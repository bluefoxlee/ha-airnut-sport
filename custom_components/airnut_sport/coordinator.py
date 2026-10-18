"""Bluetooth communication and payload decoding for AirNut Sport."""

from __future__ import annotations

import asyncio
import logging
from datetime import time as datetime_time
from datetime import timedelta

from bleak_retry_connector import BleakClientWithServiceCache, establish_connection
from homeassistant.components import bluetooth
from homeassistant.core import callback
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import (
    CMD_READ_ALL,
    DEFAULT_NIGHT_END_TIME,
    DEFAULT_NIGHT_START_TIME,
    DEFAULT_NIGHT_SUSPEND_POLLING,
    DEVICE_INFO_SERVICE_UUID,
    DOMAIN,
    FIRMWARE_REVISION_UUID,
    HARDWARE_REVISION_UUID,
    NOTIFY_UUID,
    SOFTWARE_REVISION_UUID,
    WRITE_UUID,
)

_LOGGER = logging.getLogger(__name__)


def _parse_schedule_time(value: str) -> datetime_time:
    """Parse a stored Home Assistant time selector value."""

    try:
        return datetime_time.fromisoformat(value)
    except (TypeError, ValueError):
        return datetime_time.fromisoformat(DEFAULT_NIGHT_START_TIME)


def parse_payload(data: bytes | bytearray) -> dict[str, int]:
    """Decode the AirNut Sport read-all reply."""

    if len(data) < 10:
        raise ValueError(f"回應封包長度不足: {len(data)}")
    if data[0:3] != bytes((0xAA, 0xAA, 0x6D)):
        raise ValueError(f"回應封包標頭不符: {bytes(data[:3]).hex(' ')}")

    return {
        "temperature": int.from_bytes(data[4:5], "little", signed=True),
        "humidity": int(data[5]),
        "pm25": (int(data[6]) << 8) | int(data[7]),
        "battery": int(data[9]) & 0x7F,
    }


class AirNutSportCoordinator(DataUpdateCoordinator[dict[str, int | str]]):
    """Poll one AirNut Sport device over a short-lived BLE connection."""

    def __init__(
        self,
        hass,
        address: str,
        polling_interval: int,
        disconnect_delay: int,
        night_start_time: str = DEFAULT_NIGHT_START_TIME,
        night_end_time: str = DEFAULT_NIGHT_END_TIME,
        night_suspend_polling: bool = DEFAULT_NIGHT_SUSPEND_POLLING,
    ) -> None:
        self.address = address
        self.disconnect_delay = disconnect_delay
        self._polling_interval = polling_interval
        self._night_start_time = _parse_schedule_time(night_start_time)
        self._night_end_time = _parse_schedule_time(night_end_time)
        self._night_suspend_polling = night_suspend_polling
        self._schedule_unsubscribers = []
        self._ble_device = None
        self._last_data: dict[str, int | str] | None = None
        self._firmware_checked = False
        self._firmware_version: str | None = None
        self._hardware_revision: str | None = None
        self._software_revision: str | None = None
        self._notify_event = asyncio.Event()
        self._update_lock = asyncio.Lock()

        super().__init__(
            hass,
            _LOGGER,
            name=f"空氣果 Sport {address}",
            update_interval=timedelta(seconds=polling_interval),
        )
        self._configure_schedule_listeners()
        self._update_polling_interval()

    def apply_polling_settings(
        self,
        polling_interval: int,
        disconnect_delay: int,
        night_start_time: str,
        night_end_time: str,
        night_suspend_polling: bool,
    ) -> None:
        """Apply polling options without rebuilding the coordinator."""

        self._polling_interval = polling_interval
        self.disconnect_delay = disconnect_delay
        self._night_start_time = _parse_schedule_time(night_start_time)
        self._night_end_time = _parse_schedule_time(night_end_time)
        self._night_suspend_polling = night_suspend_polling
        self._configure_schedule_listeners()
        self._update_polling_interval()

    @property
    def polling_suspended(self) -> bool:
        """Return whether the night schedule currently suspends polling."""

        return self._night_suspend_polling and self._is_night_time()

    def _configure_schedule_listeners(self) -> None:
        """Track both daily boundaries of the configured night window."""

        for unsubscribe in self._schedule_unsubscribers:
            unsubscribe()
        self._schedule_unsubscribers = []

        if self._night_start_time == self._night_end_time:
            return

        for schedule_time in (self._night_start_time, self._night_end_time):
            self._schedule_unsubscribers.append(
                async_track_time_change(
                    self.hass,
                    self._handle_schedule_boundary,
                    hour=schedule_time.hour,
                    minute=schedule_time.minute,
                    second=schedule_time.second,
                )
            )

    @callback
    def _handle_schedule_boundary(self, _now) -> None:
        """Apply the new polling state when a schedule boundary is reached."""

        self._update_polling_interval()
        if not self.polling_suspended:
            self.hass.async_create_task(
                self.async_request_refresh(),
                name=f"airnut_sport_resume_{self.address}",
            )

    async def async_shutdown(self) -> None:
        """Stop boundary listeners together with the coordinator."""

        for unsubscribe in self._schedule_unsubscribers:
            unsubscribe()
        self._schedule_unsubscribers = []
        await super().async_shutdown()

    def _is_night_time(self) -> bool:
        """Return whether the configured night window is currently active."""

        start = self._night_start_time
        end = self._night_end_time
        now = dt_util.now().time()

        # Equal endpoints intentionally disable night mode. This makes the
        # default 00:00-00:00 preserve the previous polling behaviour.
        if start == end:
            return False
        if start < end:
            return start <= now < end
        # A window such as 22:00-07:00 crosses midnight.
        return now >= start or now < end

    def _update_polling_interval(self) -> None:
        """Switch between normal polling and a suspended night schedule."""

        if self.polling_suspended:
            # A refresh may already be queued for the normal daytime interval.
            # Cancel that timer so the device can remain asleep all night.
            self._async_unsub_refresh()
            self.update_interval = None
            return

        self.update_interval = timedelta(seconds=self._polling_interval)

    def _notification_handler(self, _sender, data: bytearray) -> None:
        """Receive a read-all reply from the device."""

        try:
            self._last_data = parse_payload(data)
        except ValueError:
            _LOGGER.debug(
                "AirNut Sport %s returned an unrecognised packet: %s",
                self.address,
                bytes(data).hex(" "),
            )
            return
        self._notify_event.set()

    async def _read_device_revisions(self, client) -> dict[str, str]:
        """Read standard BLE device revision characteristics, if present."""

        if self._firmware_checked:
            return {
                key: value
                for key, value in {
                    "firmware_version": self._firmware_version,
                    "hardware_revision": self._hardware_revision,
                    "software_version": self._software_revision,
                }.items()
                if value is not None
            }

        self._firmware_checked = True
        characteristic_uuids = {
            "firmware_version": FIRMWARE_REVISION_UUID,
            "hardware_revision": HARDWARE_REVISION_UUID,
            "software_version": SOFTWARE_REVISION_UUID,
        }
        matching_characteristics = {}
        for service in client.services:
            if service.uuid.casefold() != DEVICE_INFO_SERVICE_UUID:
                continue
            for characteristic in service.characteristics:
                for key, uuid in characteristic_uuids.items():
                    if characteristic.uuid.casefold() == uuid:
                        matching_characteristics[key] = characteristic

        if not matching_characteristics:
            _LOGGER.info(
                "AirNut Sport %s does not expose standard BLE device revision characteristics",
                self.address,
            )
            return {}

        revisions = {}
        for key, characteristic in matching_characteristics.items():
            try:
                raw_revision = bytes(
                    await client.read_gatt_char(characteristic)
                ).rstrip(b"\x00")
                revision = raw_revision.decode("utf-8", errors="replace").strip()
            except Exception:
                _LOGGER.warning(
                    "AirNut Sport %s %s read failed",
                    self.address,
                    key,
                    exc_info=True,
                )
                continue

            if revision:
                revisions[key] = revision
                _LOGGER.info("AirNut Sport %s %s: %s", self.address, key, revision)

        self._firmware_version = revisions.get("firmware_version")
        self._hardware_revision = revisions.get("hardware_revision")
        self._software_revision = revisions.get("software_version")
        return revisions

    async def _async_update_data(self) -> dict[str, int | str]:
        """Connect, request one packet, decode it, and disconnect."""

        # Re-evaluate at every refresh so a schedule boundary takes effect
        # without requiring an integration reload.
        self._update_polling_interval()

        async with self._update_lock:
            current_device = bluetooth.async_ble_device_from_address(
                self.hass, self.address, connectable=True
            )
            if current_device:
                self._ble_device = current_device

            if not self._ble_device:
                raise UpdateFailed(
                    f"未掃描到空氣果 Sport ({self.address})；請先讓螢幕亮起"
                )

            client = None
            try:
                client = await establish_connection(
                    client_class=BleakClientWithServiceCache,
                    device=self._ble_device,
                    name=self.address,
                    disconnected_callback=None,
                    max_attempts=2,
                )

                self._last_data = None
                self._notify_event.clear()

                _LOGGER.debug(
                    "AirNut Sport %s services: %s",
                    self.address,
                    [
                        f"{service.uuid}: "
                        + ",".join(
                            f"{characteristic.uuid}[{','.join(characteristic.properties)}]"
                            for characteristic in service.characteristics
                        )
                        for service in client.services
                    ],
                )

                await client.start_notify(NOTIFY_UUID, self._notification_handler)
                await client.write_gatt_char(WRITE_UUID, CMD_READ_ALL, response=False)
                await asyncio.wait_for(self._notify_event.wait(), timeout=5.0)

                if not self._last_data:
                    raise ValueError("未收到完整的空氣果回應")

                data = dict(self._last_data)
                data.update(await self._read_device_revisions(client))
                return data
            except asyncio.TimeoutError as err:
                raise UpdateFailed("等待空氣果藍牙回應逾時") from err
            except UpdateFailed:
                raise
            except Exception as err:
                raise UpdateFailed(f"藍牙讀取失敗: {err}") from err
            finally:
                if client and client.is_connected:
                    try:
                        await client.stop_notify(NOTIFY_UUID)
                    except Exception:
                        _LOGGER.debug("停止 AirNut Sport notification 失敗", exc_info=True)

                    await asyncio.sleep(max(float(self.disconnect_delay), 0.5))
                    try:
                        await client.disconnect()
                    except Exception:
                        _LOGGER.debug("中斷 AirNut Sport 連線失敗", exc_info=True)

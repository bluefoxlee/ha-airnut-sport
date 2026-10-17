"""Bluetooth communication and payload decoding for AirNut Sport."""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta

from bleak_retry_connector import BleakClientWithServiceCache, establish_connection
from homeassistant.components import bluetooth
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import CMD_READ_ALL, DOMAIN, NOTIFY_UUID, WRITE_UUID

_LOGGER = logging.getLogger(__name__)


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


class AirNutSportCoordinator(DataUpdateCoordinator[dict[str, int]]):
    """Poll one AirNut Sport device over a short-lived BLE connection."""

    def __init__(
        self,
        hass,
        address: str,
        polling_interval: int,
        disconnect_delay: int,
    ) -> None:
        self.address = address
        self.disconnect_delay = disconnect_delay
        self._ble_device = None
        self._last_data: dict[str, int] | None = None
        self._notify_event = asyncio.Event()
        self._update_lock = asyncio.Lock()

        super().__init__(
            hass,
            _LOGGER,
            name=f"AirNut Sport {address}",
            update_interval=timedelta(seconds=polling_interval),
        )

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

    async def _async_update_data(self) -> dict[str, int]:
        """Connect, request one packet, decode it, and disconnect."""

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
                return self._last_data
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

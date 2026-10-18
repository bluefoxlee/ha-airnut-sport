"""Config flow for AirNut Sport."""

from __future__ import annotations

from datetime import time as datetime_time

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.components.bluetooth import (
    BluetoothServiceInfoBleak,
    async_discovered_service_info,
)
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_DISCONNECT_DELAY,
    CONF_MAC,
    CONF_NIGHT_END_TIME,
    CONF_NIGHT_START_TIME,
    CONF_NIGHT_SUSPEND_POLLING,
    CONF_POLLING_INTERVAL,
    DEFAULT_DISCONNECT_DELAY,
    DEFAULT_NIGHT_END_TIME,
    DEFAULT_NIGHT_START_TIME,
    DEFAULT_NIGHT_SUSPEND_POLLING,
    DEFAULT_POLLING_INTERVAL,
    DOMAIN,
    MAX_POLLING_INTERVAL,
    MIN_DISCONNECT_DELAY,
    MIN_POLLING_INTERVAL,
)


def _normalise_time(value, default: str) -> str:
    """Store time selector values in a stable HH:MM:SS format."""

    if isinstance(value, datetime_time):
        return value.strftime("%H:%M:%S")
    if isinstance(value, str):
        try:
            return datetime_time.fromisoformat(value).strftime("%H:%M:%S")
        except ValueError:
            pass
    return default


def _schedule_options(user_input: dict) -> dict:
    """Extract and normalise the night polling options."""

    return {
        CONF_POLLING_INTERVAL: user_input[CONF_POLLING_INTERVAL],
        CONF_DISCONNECT_DELAY: user_input[CONF_DISCONNECT_DELAY],
        CONF_NIGHT_START_TIME: _normalise_time(
            user_input.get(CONF_NIGHT_START_TIME), DEFAULT_NIGHT_START_TIME
        ),
        CONF_NIGHT_END_TIME: _normalise_time(
            user_input.get(CONF_NIGHT_END_TIME), DEFAULT_NIGHT_END_TIME
        ),
        CONF_NIGHT_SUSPEND_POLLING: user_input.get(
            CONF_NIGHT_SUSPEND_POLLING, DEFAULT_NIGHT_SUSPEND_POLLING
        ),
    }


def _night_schedule_schema(options: dict) -> dict:
    """Build the shared setup/options schema for polling schedules."""

    return {
        vol.Required(
            CONF_NIGHT_START_TIME,
            default=options.get(CONF_NIGHT_START_TIME, DEFAULT_NIGHT_START_TIME),
        ): selector.TimeSelector(),
        vol.Required(
            CONF_NIGHT_END_TIME,
            default=options.get(CONF_NIGHT_END_TIME, DEFAULT_NIGHT_END_TIME),
        ): selector.TimeSelector(),
        vol.Required(
            CONF_NIGHT_SUSPEND_POLLING,
            default=options.get(
                CONF_NIGHT_SUSPEND_POLLING, DEFAULT_NIGHT_SUSPEND_POLLING
            ),
        ): selector.BooleanSelector(),
    }


class AirNutConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle AirNut Sport setup."""

    VERSION = 1

    def __init__(self) -> None:
        self._discovery_info: BluetoothServiceInfoBleak | None = None

    async def async_step_bluetooth(self, discovery_info: BluetoothServiceInfoBleak):
        """Handle a Bluetooth discovery result."""

        await self.async_set_unique_id(discovery_info.address)
        self._abort_if_unique_id_configured()
        self._discovery_info = discovery_info
        return await self.async_step_bluetooth_confirm()

    async def async_step_bluetooth_confirm(self, user_input=None):
        """Confirm a discovered AirNut Sport."""

        if user_input is not None and self._discovery_info:
            return self.async_create_entry(
                title=self._discovery_info.name or "空氣果 Sport",
                data={CONF_MAC: self._discovery_info.address},
                options={
                    CONF_POLLING_INTERVAL: DEFAULT_POLLING_INTERVAL,
                    CONF_DISCONNECT_DELAY: DEFAULT_DISCONNECT_DELAY,
                    CONF_NIGHT_START_TIME: DEFAULT_NIGHT_START_TIME,
                    CONF_NIGHT_END_TIME: DEFAULT_NIGHT_END_TIME,
                    CONF_NIGHT_SUSPEND_POLLING: DEFAULT_NIGHT_SUSPEND_POLLING,
                },
            )

        name = (
            self._discovery_info.name
            if self._discovery_info
            else "空氣果 Sport"
        )
        return self.async_show_form(
            step_id="bluetooth_confirm",
            description_placeholders={"name": name},
        )
    async def async_step_user(self, user_input=None):
        """Add the device manually from HA's discovered Bluetooth list."""

        if user_input is not None:
            mac = user_input[CONF_MAC].strip()
            await self.async_set_unique_id(mac)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=f"空氣果 Sport {mac}",
                data={CONF_MAC: mac},
                options=_schedule_options(user_input),
            )

        discovered = async_discovered_service_info(self.hass, connectable=True)
        discovered = sorted(
            (device for device in discovered if device.connectable),
            key=lambda device: (
                0 if "airnut" in (device.name or "").casefold() else 1,
                (device.name or "Unknown").casefold(),
                device.address,
            ),
        )
        devices = {
            device.address: f"{device.name or 'Unknown'} ({device.address})"
            for device in discovered
        }
        mac_schema = vol.In(devices) if devices else str
        schema = {
            vol.Required(CONF_MAC): mac_schema,
            vol.Optional(
                CONF_POLLING_INTERVAL,
                default=DEFAULT_POLLING_INTERVAL,
            ): vol.All(
                vol.Coerce(int),
                vol.Range(
                    min=MIN_POLLING_INTERVAL,
                    max=MAX_POLLING_INTERVAL,
                ),
            ),
            vol.Optional(
                CONF_DISCONNECT_DELAY,
                default=DEFAULT_DISCONNECT_DELAY,
            ): vol.All(
                vol.Coerce(int),
                vol.Range(min=MIN_DISCONNECT_DELAY),
            ),
        }
        schema.update(_night_schedule_schema({}))
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(schema),
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Return the options flow."""

        return AirNutOptionsFlowHandler()


class AirNutOptionsFlowHandler(config_entries.OptionsFlow):
    """Allow polling settings to be changed after setup."""

    async def async_step_init(self, user_input=None):
        """Handle options."""

        options = self.config_entry.options
        if user_input is not None:
            return self.async_create_entry(
                title="", data=_schedule_options(user_input)
            )

        schema = {
            vol.Required(
                CONF_POLLING_INTERVAL,
                default=options.get(
                    CONF_POLLING_INTERVAL, DEFAULT_POLLING_INTERVAL
                ),
            ): vol.All(
                vol.Coerce(int),
                vol.Range(
                    min=MIN_POLLING_INTERVAL,
                    max=MAX_POLLING_INTERVAL,
                ),
            ),
            vol.Required(
                CONF_DISCONNECT_DELAY,
                default=options.get(
                    CONF_DISCONNECT_DELAY, DEFAULT_DISCONNECT_DELAY
                ),
            ): vol.All(
                vol.Coerce(int),
                vol.Range(min=MIN_DISCONNECT_DELAY),
            ),
        }
        schema.update(_night_schedule_schema(options))
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(schema),
        )

"""Config flow for AirNut Sport."""

from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.components.bluetooth import (
    BluetoothServiceInfoBleak,
    async_discovered_service_info,
)
from homeassistant.core import callback

from .const import (
    CONF_DISCONNECT_DELAY,
    CONF_MAC,
    CONF_POLLING_INTERVAL,
    DEFAULT_DISCONNECT_DELAY,
    DEFAULT_POLLING_INTERVAL,
    DOMAIN,
    MAX_POLLING_INTERVAL,
    MIN_DISCONNECT_DELAY,
    MIN_POLLING_INTERVAL,
)


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
                title=self._discovery_info.name or "AirNut Sport",
                data={CONF_MAC: self._discovery_info.address},
                options={
                    CONF_POLLING_INTERVAL: DEFAULT_POLLING_INTERVAL,
                    CONF_DISCONNECT_DELAY: DEFAULT_DISCONNECT_DELAY,
                },
            )

        name = self._discovery_info.name if self._discovery_info else "AirNut Sport"
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
                title=f"AirNut Sport {mac}",
                data={CONF_MAC: mac},
                options={
                    CONF_POLLING_INTERVAL: user_input[CONF_POLLING_INTERVAL],
                    CONF_DISCONNECT_DELAY: user_input[CONF_DISCONNECT_DELAY],
                },
            )

        discovered = async_discovered_service_info(self.hass, connectable=True)
        devices = {
            device.address: f"{device.name or 'Unknown'} ({device.address})"
            for device in discovered
            if device.connectable
        }
        mac_schema = vol.In(devices) if devices else str
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
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
            ),
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
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
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
            ),
        )

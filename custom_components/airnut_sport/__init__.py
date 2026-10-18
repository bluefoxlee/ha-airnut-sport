"""Home Assistant integration for the Bluetooth AirNut Sport."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

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
)
from .coordinator import AirNutSportCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ("sensor",)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the integration domain."""

    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up an AirNut Sport config entry."""

    coordinator = AirNutSportCoordinator(
        hass,
        address=entry.data[CONF_MAC],
        polling_interval=entry.options.get(
            CONF_POLLING_INTERVAL, DEFAULT_POLLING_INTERVAL
        ),
        disconnect_delay=entry.options.get(
            CONF_DISCONNECT_DELAY, DEFAULT_DISCONNECT_DELAY
        ),
        night_start_time=entry.options.get(
            CONF_NIGHT_START_TIME, DEFAULT_NIGHT_START_TIME
        ),
        night_end_time=entry.options.get(
            CONF_NIGHT_END_TIME, DEFAULT_NIGHT_END_TIME
        ),
        night_suspend_polling=entry.options.get(
            CONF_NIGHT_SUSPEND_POLLING, DEFAULT_NIGHT_SUSPEND_POLLING
        ),
    )

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Keep entity creation independent from the first Bluetooth read. This lets
    # the user wake the screen or move the proxy closer without blocking HA.
    if not coordinator.polling_suspended:
        hass.async_create_task(
            coordinator.async_refresh(),
            name=f"{DOMAIN}_initial_refresh_{entry.entry_id}",
        )

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload an AirNut Sport config entry."""

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    return unload_ok


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Apply changed polling options without restarting Home Assistant."""

    coordinator: AirNutSportCoordinator = hass.data[DOMAIN][entry.entry_id]
    coordinator.apply_polling_settings(
        polling_interval=entry.options.get(
            CONF_POLLING_INTERVAL, DEFAULT_POLLING_INTERVAL
        ),
        disconnect_delay=entry.options.get(
            CONF_DISCONNECT_DELAY, DEFAULT_DISCONNECT_DELAY
        ),
        night_start_time=entry.options.get(
            CONF_NIGHT_START_TIME, DEFAULT_NIGHT_START_TIME
        ),
        night_end_time=entry.options.get(
            CONF_NIGHT_END_TIME, DEFAULT_NIGHT_END_TIME
        ),
        night_suspend_polling=entry.options.get(
            CONF_NIGHT_SUSPEND_POLLING, DEFAULT_NIGHT_SUSPEND_POLLING
        ),
    )
    if not coordinator.polling_suspended:
        await coordinator.async_request_refresh()

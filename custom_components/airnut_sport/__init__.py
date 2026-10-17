"""Home Assistant integration for the Bluetooth AirNut Sport."""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import (
    CONF_DISCONNECT_DELAY,
    CONF_MAC,
    CONF_POLLING_INTERVAL,
    DEFAULT_DISCONNECT_DELAY,
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
    )

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Keep entity creation independent from the first Bluetooth read. This lets
    # the user wake the screen or move the proxy closer without blocking HA.
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
    coordinator.update_interval = timedelta(
        seconds=entry.options.get(CONF_POLLING_INTERVAL, DEFAULT_POLLING_INTERVAL)
    )
    coordinator.disconnect_delay = entry.options.get(
        CONF_DISCONNECT_DELAY, DEFAULT_DISCONNECT_DELAY
    )
    await coordinator.async_request_refresh()

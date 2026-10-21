"""TotalEnergies Stations (unofficial) integration for Home Assistant."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import KeyDiscoveryError, TotalEnergiesStationsApi
from .coordinator import TotalEnergiesCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BINARY_SENSOR]

TotalEnergiesConfigEntry = ConfigEntry[TotalEnergiesCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: TotalEnergiesConfigEntry) -> bool:
    """Set up from a config entry."""
    api = TotalEnergiesStationsApi(async_get_clientsession(hass))
    try:
        await api.async_discover_keys()
    except KeyDiscoveryError as err:
        raise ConfigEntryNotReady(f"Key discovery failed: {err}") from err

    coordinator = TotalEnergiesCoordinator(hass, entry, api)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def _async_update_listener(hass: HomeAssistant, entry: TotalEnergiesConfigEntry) -> None:
    """Reload the entry when options change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: TotalEnergiesConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

"""Diagnostics support. Keys and coordinates are redacted."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from . import TotalEnergiesConfigEntry
from .const import CONF_LATITUDE, CONF_LONGITUDE

TO_REDACT = {
    CONF_LATITUDE,
    CONF_LONGITUDE,
    "latitude",
    "longitude",
    "location",
    "key",
    "api_key",
    "API-Key",
    "total_key",
    "woos_key",
    "_total_key",
    "_woos_key",
    "address",
    "street_address",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: TotalEnergiesConfigEntry
) -> dict[str, Any]:
    """Return redacted diagnostics for a config entry."""
    coordinator = entry.runtime_data
    stations = {lid: asdict(data) for lid, data in (coordinator.data or {}).items()}
    payload = {
        "entry": {
            "title": entry.title,
            "data": dict(entry.data),
            "options": dict(entry.options),
        },
        "coordinator": {
            "update_interval_s": coordinator.update_interval.total_seconds()
            if coordinator.update_interval
            else None,
            "last_update_success": coordinator.last_update_success,
            "keys_discovered": coordinator.api.keys_discovered,
        },
        "stations": stations,
    }
    return async_redact_data(payload, TO_REDACT)

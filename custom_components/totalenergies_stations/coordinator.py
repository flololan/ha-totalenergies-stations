"""DataUpdateCoordinator for TotalEnergies Stations (unofficial)."""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import TotalEnergiesApiError, TotalEnergiesStationsApi
from .const import (
    BACKOFF_MULTIPLIER,
    CONF_SCAN_INTERVAL_MIN,
    CONF_STATIONS,
    DEFAULT_SCAN_INTERVAL_MIN,
    DOMAIN,
    MAX_BACKOFF_MINUTES,
    MIN_SCAN_INTERVAL_MIN,
)
from .parsing import StationData

_LOGGER = logging.getLogger(__name__)


class TotalEnergiesCoordinator(DataUpdateCoordinator[dict[str, StationData]]):
    """Polls the selected stations at a gentle interval with backoff on errors."""

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        api: TotalEnergiesStationsApi,
    ) -> None:
        minutes = int(
            entry.options.get(
                CONF_SCAN_INTERVAL_MIN,
                entry.data.get(CONF_SCAN_INTERVAL_MIN, DEFAULT_SCAN_INTERVAL_MIN),
            )
        )
        self._base_interval = timedelta(minutes=max(minutes, MIN_SCAN_INTERVAL_MIN))
        self._failures = 0
        self.api = api
        self.stations: list[dict] = list(entry.data.get(CONF_STATIONS, []))
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{DOMAIN} ({entry.title})",
            update_interval=self._base_interval,
        )

    @property
    def station_ids(self) -> list[str]:
        """Return the configured station IDs."""
        return [s["location_id"] for s in self.stations]

    def station_meta(self, location_id: str) -> dict:
        """Return the stored name/address for a station."""
        for station in self.stations:
            if station["location_id"] == location_id:
                return station
        return {"location_id": location_id}

    async def _async_update_data(self) -> dict[str, StationData]:
        try:
            data = await self.api.async_get_stations(self.station_ids)
        except TotalEnergiesApiError as err:
            self._failures += 1
            backoff = min(
                self._base_interval * (BACKOFF_MULTIPLIER**self._failures),
                timedelta(minutes=MAX_BACKOFF_MINUTES),
            )
            self.update_interval = backoff
            raise UpdateFailed(
                f"{err} (next attempt in {int(backoff.total_seconds() // 60)} min)"
            ) from err

        if self._failures:
            _LOGGER.info("Update succeeded again, resetting poll interval")
        self._failures = 0
        self.update_interval = self._base_interval
        return data

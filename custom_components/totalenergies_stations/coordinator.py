"""DataUpdateCoordinator for TotalEnergies Stations (unofficial)."""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.components import persistent_notification
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import TotalEnergiesApiError, TotalEnergiesStationsApi
from .const import (
    BACKOFF_MULTIPLIER,
    CONF_FUELS,
    CONF_NOTIFY_PERSISTENT,
    CONF_SCAN_INTERVAL_MIN,
    CONF_STATIONS,
    DEFAULT_FUELS,
    DEFAULT_NOTIFY_PERSISTENT,
    DEFAULT_SCAN_INTERVAL_MIN,
    DOMAIN,
    EVENT_FUEL_AVAILABILITY_CHANGED,
    MAX_BACKOFF_MINUTES,
    MIN_SCAN_INTERVAL_MIN,
)
from .events import detect_availability_changes
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
        self._notify_changes(data)
        return data

    # ------------------------------------------------------------ notifications
    def _option(self, key: str, default):
        entry = self.config_entry
        return entry.options.get(key, entry.data.get(key, default))

    def _notify_changes(self, data: dict[str, StationData]) -> None:
        """Fire events (and optional persistent notifications) on availability changes.

        ``self.data`` is None on the first refresh after start, so no change is
        reported then.
        """
        changes = detect_availability_changes(
            self.data,
            data,
            fuels=list(self._option(CONF_FUELS, DEFAULT_FUELS)),
            station_names={s["location_id"]: s.get("name") for s in self.stations},
        )
        if not changes:
            return
        notify = bool(self._option(CONF_NOTIFY_PERSISTENT, DEFAULT_NOTIFY_PERSISTENT))
        for change in changes:
            _LOGGER.debug("Fuel availability changed: %s", change)
            self.hass.bus.async_fire(EVENT_FUEL_AVAILABILITY_CHANGED, change)
            if notify and change["available"]:
                price = f" ({change['price']} €/L)" if change["price"] is not None else ""
                persistent_notification.async_create(
                    self.hass,
                    f"{change['product_name']} : de nouveau disponible / available again"
                    f" - {change['station_name']}{price}",
                    title="TotalEnergies Stations",
                    notification_id=(
                        f"{DOMAIN}_{change['location_id']}_{change['product_code']}"
                    ),
                )

"""Sensors: fuel price per station/fuel and opening status per station."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import (
    SensorEntity,
    SensorStateClass,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import TotalEnergiesConfigEntry
from .const import DOMAIN, FUEL_LABELS
from .coordinator import TotalEnergiesCoordinator
from .entity import TotalEnergiesStationEntity, configured_fuels, remove_stale_entities
from .parsing import FuelInfo


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TotalEnergiesConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensors for every configured station and fuel."""
    coordinator = entry.runtime_data
    fuels = configured_fuels(coordinator)
    entities: list[SensorEntity] = []
    for location_id in coordinator.station_ids:
        entities.append(OpeningStatusSensor(coordinator, location_id))
        entities.extend(FuelPriceSensor(coordinator, location_id, code) for code in fuels)
    remove_stale_entities(coordinator, "sensor", {e.unique_id for e in entities if e.unique_id})
    async_add_entities(entities)


class FuelPriceSensor(TotalEnergiesStationEntity, SensorEntity):
    """Price of one fuel at one station (EUR per litre)."""

    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "€/L"
    _attr_suggested_display_precision = 3
    _attr_icon = "mdi:gas-station"

    def __init__(
        self, coordinator: TotalEnergiesCoordinator, location_id: str, product_code: str
    ) -> None:
        super().__init__(coordinator, location_id)
        self._product_code = product_code
        self._attr_unique_id = f"{DOMAIN}_{location_id}_{product_code}_price"
        self._attr_translation_key = "fuel_price"
        self._attr_translation_placeholders = {"fuel": FUEL_LABELS.get(product_code, product_code)}

    @property
    def _fuel(self) -> FuelInfo | None:
        station = self.station
        return station.fuels.get(self._product_code) if station else None

    @property
    def native_value(self) -> float | None:
        """Return the price or None when the fuel/station has no data."""
        fuel = self._fuel
        return fuel.price if fuel else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose availability and metadata."""
        fuel = self._fuel
        return {
            "location_id": self._location_id,
            "product_code": self._product_code,
            "product_name": fuel.product_name if fuel else None,
            "availability_status": fuel.availability_status if fuel else None,
            "price_update_date_time": fuel.price_update_date_time if fuel else None,
            "currency": fuel.currency if fuel else None,
            "unit": fuel.unit if fuel else None,
            "offered": fuel is not None,
            "attribution": "Data from the TotalEnergies station map (unofficial, private use only)",
        }


class OpeningStatusSensor(TotalEnergiesStationEntity, SensorEntity):
    """Opening status (e.g. OPEN / CLOSED) of a station."""

    _attr_icon = "mdi:store-clock"
    _attr_translation_key = "opening_status"

    def __init__(self, coordinator: TotalEnergiesCoordinator, location_id: str) -> None:
        super().__init__(coordinator, location_id)
        self._attr_unique_id = f"{DOMAIN}_{location_id}_opening_status"

    @property
    def native_value(self) -> str | None:
        """Return the raw opening status code (lowercase) or None."""
        station = self.station
        if not station or not station.has_data or not station.opening_status:
            return None
        return str(station.opening_status).lower()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose station metadata."""
        station = self.station
        return {
            "location_id": self._location_id,
            "station_name": station.name if station else None,
            "address": (station.address if station else None) or self._station_address,
            "has_data": bool(station and station.has_data),
            "fuels_offered": sorted(station.fuels) if station else [],
        }

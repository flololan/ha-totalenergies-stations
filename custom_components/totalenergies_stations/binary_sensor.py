"""Binary sensors: fuel availability per station/fuel."""

from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import BinarySensorEntity
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
    """Set up availability binary sensors."""
    coordinator = entry.runtime_data
    fuels = configured_fuels(coordinator)
    entities = [
        FuelAvailableBinarySensor(coordinator, location_id, code)
        for location_id in coordinator.station_ids
        for code in fuels
    ]
    remove_stale_entities(
        coordinator, "binary_sensor", {e.unique_id for e in entities if e.unique_id}
    )
    async_add_entities(entities)


class FuelAvailableBinarySensor(TotalEnergiesStationEntity, BinarySensorEntity):
    """on = AVAILABLE, off = UNAVAILABLE, unknown = UNKNOWN/null."""

    _attr_icon = "mdi:fuel"
    _attr_translation_key = "fuel_available"

    def __init__(
        self, coordinator: TotalEnergiesCoordinator, location_id: str, product_code: str
    ) -> None:
        super().__init__(coordinator, location_id)
        self._product_code = product_code
        self._attr_unique_id = f"{DOMAIN}_{location_id}_{product_code}_available"
        self._attr_translation_placeholders = {"fuel": FUEL_LABELS.get(product_code, product_code)}

    @property
    def _fuel(self) -> FuelInfo | None:
        station = self.station
        return station.fuels.get(self._product_code) if station else None

    @property
    def is_on(self) -> bool | None:
        """Return True/False for AVAILABLE/UNAVAILABLE, None otherwise."""
        fuel = self._fuel
        return fuel.is_available if fuel else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose raw status and price metadata."""
        fuel = self._fuel
        return {
            "location_id": self._location_id,
            "product_code": self._product_code,
            "product_name": fuel.product_name if fuel else None,
            "availability_status": fuel.availability_status if fuel else None,
            "price": fuel.price if fuel else None,
            "price_update_date_time": fuel.price_update_date_time if fuel else None,
            "offered": fuel is not None,
        }

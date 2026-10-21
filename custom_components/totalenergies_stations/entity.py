"""Shared entity base for TotalEnergies Stations (unofficial)."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_FUELS, DEFAULT_FUELS, DOMAIN, MANUFACTURER, SITE_PAGE
from .coordinator import TotalEnergiesCoordinator
from .parsing import StationData


def configured_fuels(coordinator: TotalEnergiesCoordinator) -> list[str]:
    """Return the fuel codes selected by the user (options override data)."""
    entry = coordinator.config_entry
    return list(entry.options.get(CONF_FUELS, entry.data.get(CONF_FUELS, DEFAULT_FUELS)))


def remove_stale_entities(
    coordinator: TotalEnergiesCoordinator, platform: str, keep: set[str]
) -> None:
    """Remove registry entries of this config entry/platform whose unique_id is not kept.

    Used after the user de-selects a fuel in the options flow.
    """
    registry = async_get_entity_registry(coordinator.hass)
    for reg_entry in list(registry.entities.values()):
        if (
            reg_entry.config_entry_id == coordinator.config_entry.entry_id
            and reg_entry.domain == platform
            and reg_entry.unique_id not in keep
        ):
            registry.async_remove(reg_entry.entity_id)


class TotalEnergiesStationEntity(CoordinatorEntity[TotalEnergiesCoordinator]):
    """Base entity bound to one station (one HA device per station)."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: TotalEnergiesCoordinator, location_id: str) -> None:
        super().__init__(coordinator)
        self._location_id = location_id
        meta = coordinator.station_meta(location_id)
        station = (coordinator.data or {}).get(location_id)
        name = meta.get("name") or (station.name if station else None) or location_id
        self._station_address = meta.get("address") or (station.address if station else None)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, location_id)},
            name=f"TotalEnergies {name}",
            manufacturer=MANUFACTURER,
            model="Station",
            serial_number=location_id,
            configuration_url=SITE_PAGE,
        )

    @property
    def station(self) -> StationData | None:
        """Return the current data for this station."""
        return (self.coordinator.data or {}).get(self._location_id)

    @property
    def available(self) -> bool:
        """Entity is available when the coordinator has data for the station."""
        return super().available and self.station is not None

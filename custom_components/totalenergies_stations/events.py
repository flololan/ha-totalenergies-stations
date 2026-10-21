"""Pure change-detection helpers for fuel availability (no Home Assistant deps).

The coordinator compares the previous and the new poll result and fires one
event per fuel whose availability flipped between available and unavailable.
UNKNOWN / missing values never count as a change.
"""

from __future__ import annotations

from typing import Any

from .parsing import StationData


def detect_availability_changes(
    previous: dict[str, StationData] | None,
    current: dict[str, StationData],
    fuels: list[str] | None = None,
    station_names: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    """Return event payloads for every fuel whose availability changed.

    * ``previous is None`` means "first refresh after start" -> no changes.
    * Only transitions True <-> False are reported; None (UNKNOWN) is ignored
      on either side.
    * ``fuels`` restricts the comparison to the configured product codes.
    """
    if previous is None:
        return []

    changes: list[dict[str, Any]] = []
    for location_id, station in current.items():
        old_station = previous.get(location_id)
        if old_station is None:
            continue
        codes = fuels if fuels is not None else list(station.fuels)
        for code in codes:
            new_fuel = station.fuels.get(code)
            old_fuel = old_station.fuels.get(code)
            if new_fuel is None or old_fuel is None:
                continue
            new_state = new_fuel.is_available
            old_state = old_fuel.is_available
            if new_state is None or old_state is None or new_state == old_state:
                continue
            name = (station_names or {}).get(location_id) or station.name or location_id
            changes.append(
                {
                    "location_id": location_id,
                    "station_name": name,
                    "product_code": code,
                    "product_name": new_fuel.product_name or new_fuel.label,
                    "available": new_state,
                    "previous_available": old_state,
                    "availability_status": new_fuel.availability_status,
                    "price": new_fuel.price,
                }
            )
    return changes

"""Pure parsing helpers (no Home Assistant / network dependencies).

Kept framework-free so they can be unit-tested with plain pytest.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from .const import (
    AVAILABILITY_AVAILABLE,
    AVAILABILITY_UNAVAILABLE,
    AVAILABILITY_UNKNOWN,
    FUEL_LABELS,
    TOTAL_KEY_PATTERN,
    WOOS_KEY_PATTERN,
)


@dataclass(slots=True)
class StationSummary:
    """A station as returned by the Woosmap radius search."""

    location_id: str
    name: str | None = None
    address: str | None = None
    distance_m: float | None = None
    latitude: float | None = None
    longitude: float | None = None

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable representation for the config entry."""
        return {
            "location_id": self.location_id,
            "name": self.name,
            "address": self.address,
        }


@dataclass(slots=True)
class FuelInfo:
    """Price and availability of one fuel at one station."""

    product_code: str
    product_name: str | None = None
    price: float | None = None
    currency: str | None = None
    unit: str | None = None
    availability_status: str | None = None
    price_update_date_time: str | None = None

    @property
    def label(self) -> str:
        """Return a human readable label for the product code."""
        return FUEL_LABELS.get(self.product_code, self.product_code)

    @property
    def is_available(self) -> bool | None:
        """True/False for AVAILABLE/UNAVAILABLE, None for UNKNOWN/null."""
        if self.availability_status == AVAILABILITY_AVAILABLE:
            return True
        if self.availability_status == AVAILABILITY_UNAVAILABLE:
            return False
        return None


@dataclass(slots=True)
class StationData:
    """Hot data for one station."""

    location_id: str
    name: str | None = None
    address: str | None = None
    opening_status: str | None = None
    fuels: dict[str, FuelInfo] = field(default_factory=dict)
    has_data: bool = True  # False when the API returned 404 (no data)


def extract_woos_key(text: str) -> str | None:
    """Extract the public Woosmap key from loader.js source."""
    match = re.search(WOOS_KEY_PATTERN, text or "")
    return match.group(0) if match else None


def extract_total_key(text: str) -> str | None:
    """Extract the hot-data API key from front.js source."""
    match = re.search(TOTAL_KEY_PATTERN, text or "")
    return match.group(1) if match else None


def _format_address(address: dict[str, Any] | None) -> str | None:
    if not address:
        return None
    lines = [line for line in (address.get("lines") or []) if line]
    tail = " ".join(part for part in (address.get("zipcode"), address.get("city")) if part)
    parts = [", ".join(lines)] if lines else []
    if tail:
        parts.append(tail)
    return ", ".join(parts) or None


def parse_woosmap_search(geojson: dict[str, Any]) -> list[StationSummary]:
    """Parse a Woosmap `stores/search` response and de-duplicate by location_id.

    Woosmap returns one feature per POI type (FUELING, WASH, ...) so the same
    station may appear several times.
    """
    result: list[StationSummary] = []
    seen: set[str] = set()
    for feature in (geojson or {}).get("features", []) or []:
        props = feature.get("properties") or {}
        user_props = props.get("user_properties") or {}
        location_id = user_props.get("location_id") or props.get("store_id")
        if not location_id or location_id in seen:
            continue
        seen.add(location_id)
        coords = (feature.get("geometry") or {}).get("coordinates") or [None, None]
        result.append(
            StationSummary(
                location_id=str(location_id),
                name=props.get("name"),
                address=_format_address(props.get("address")),
                distance_m=props.get("distance"),
                longitude=coords[0] if len(coords) > 0 else None,
                latitude=coords[1] if len(coords) > 1 else None,
            )
        )
    result.sort(key=lambda s: (s.distance_m is None, s.distance_m or 0))
    return result


def normalize_availability(value: Any) -> str | None:
    """Map the raw availability_status to AVAILABLE/UNAVAILABLE/UNKNOWN/None."""
    if value is None:
        return None
    text = str(value).strip().upper()
    if text in (AVAILABILITY_AVAILABLE, AVAILABILITY_UNAVAILABLE):
        return text
    if text == "":
        return None
    return AVAILABILITY_UNKNOWN


def _to_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_hot_data(location_id: str, payload: dict[str, Any] | None) -> StationData:
    """Parse the hot-data response for one station.

    `payload=None` means the API answered 404 (no data for that station).
    Only products with category_code == "ENERGIES" are considered.
    """
    if payload is None:
        return StationData(location_id=location_id, has_data=False)

    address_parts = [
        payload.get("street_address"),
        " ".join(p for p in (payload.get("zip_code"), payload.get("city")) if p),
    ]
    address = ", ".join(p.strip() for p in address_parts if p and p.strip()) or None

    fuels: dict[str, FuelInfo] = {}
    for product in payload.get("products_and_services") or []:
        if product.get("category_code") != "ENERGIES":
            continue
        code = product.get("product_code")
        if not code:
            continue
        code = str(code).upper()
        name = product.get("product_name")
        fuels[code] = FuelInfo(
            product_code=code,
            product_name=name.strip() if isinstance(name, str) else name,
            price=_to_float(product.get("price")),
            currency=product.get("currency_code"),
            unit=product.get("unit_of_measure_code"),
            availability_status=normalize_availability(product.get("availability_status")),
            price_update_date_time=product.get("price_update_date_time"),
        )

    return StationData(
        location_id=str(payload.get("location_id") or location_id),
        name=payload.get("business_name"),
        address=address,
        opening_status=payload.get("current_business_opening_status_code"),
        fuels=fuels,
        has_data=True,
    )


def parse_station_ids(text: str) -> list[str]:
    """Parse a comma/space/newline separated list of station IDs (NF...)."""
    ids: list[str] = []
    for token in re.split(r"[\s,;]+", text or ""):
        token = token.strip().upper()
        if token and token not in ids:
            ids.append(token)
    return ids

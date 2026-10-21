"""Manual live smoke test (needs network). Not run in CI.

Usage: python scripts/smoke_test.py [lat] [lng]
Discovers the public keys, searches stations and fetches hot data for a few of
them. Keys are never printed. Please run sparingly - it hits the live endpoints.
"""

import asyncio
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _register_package_stub() -> None:
    """Allow importing api.py without Home Assistant installed."""
    for name, path in (
        ("custom_components", ROOT / "custom_components"),
        (
            "custom_components.totalenergies_stations",
            ROOT / "custom_components/totalenergies_stations",
        ),
    ):
        if name not in sys.modules:
            module = types.ModuleType(name)
            module.__path__ = [str(path)]  # type: ignore[attr-defined]
            sys.modules[name] = module


async def main() -> None:
    _register_package_stub()
    import aiohttp

    from custom_components.totalenergies_stations.api import TotalEnergiesStationsApi

    lat = float(sys.argv[1]) if len(sys.argv) > 1 else 48.08
    lng = float(sys.argv[2]) if len(sys.argv) > 2 else 7.36
    async with aiohttp.ClientSession() as session:
        api = TotalEnergiesStationsApi(session)
        await api.async_discover_keys()
        print("keys discovered:", api.keys_discovered)
        stations = await api.async_search_stations(lat, lng, 10000)
        print("stations found:", len(stations))
        for s in stations[:6]:
            print("  ", s.location_id, s.name, s.address, f"{(s.distance_m or 0) / 1000:.1f} km")
        ids = [s.location_id for s in stations[:3]]
        data = await api.async_get_stations(ids)
        for lid, d in data.items():
            print(lid, "has_data=", d.has_data, "open=", d.opening_status, "name=", d.name)
            for code in ("E10", "SP8", "GO"):
                f = d.fuels.get(code)
                if not f:
                    print("    ", code, "-> not offered")
                    continue
                print(
                    f"     {code} -> {f.label}: {f.price} {f.currency}/{f.unit}"
                    f" {f.availability_status} ({f.price_update_date_time})"
                )


if __name__ == "__main__":
    asyncio.run(main())

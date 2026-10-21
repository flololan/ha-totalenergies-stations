"""Constants for the TotalEnergies Stations (unofficial) integration."""

from __future__ import annotations

from datetime import timedelta

DOMAIN = "totalenergies_stations"
INTEGRATION_NAME = "TotalEnergies Stations (unofficial)"
VERSION = "0.1.0"
PROJECT_URL = "https://github.com/flololan/ha-totalenergies-stations"

# Honest, non-spoofed user agent. No browser impersonation.
USER_AGENT = f"ha-totalenergies-stations/{VERSION} (+{PROJECT_URL})"

# Public web endpoints used by the official station map
# (https://services.totalenergies.fr/stations). Undocumented, may change.
SITE_ORIGIN = "https://services.totalenergies.fr"
SITE_PAGE = f"{SITE_ORIGIN}/stations"
# Script chain of the map: /stations -> mapstore.js -> customdevs loader.js
# -> main.js -> front.js. loader.js and front.js both embed the public keys.
LOADER_URL = "https://customdevs.woosmap.com/total/loader.js"
FRONT_URL = "https://customdevs.woosmap.com/total/front.js"
WOOSMAP_SEARCH_URL = "https://api.woosmap.com/stores/search"
HOT_DATA_URL = (
    "https://apis.poifinder.alzp.tgscloud.net/"
    "poi-finder-store-locator-back/api/v1/point-of-interest"
)

# Regular expressions used to discover the public keys embedded in the
# map's JavaScript at runtime. No key is ever stored in this repository.
WOOS_KEY_PATTERN = r"woos-[0-9a-f\-]{36}"
TOTAL_KEY_PATTERN = r'totalKey:"([^"]+)"'

# Config entry keys
CONF_LATITUDE = "latitude"
CONF_LONGITUDE = "longitude"
CONF_RADIUS_KM = "radius_km"
CONF_FUELS = "fuels"
CONF_STATIONS = "stations"  # list of dicts: {location_id, name, address}
CONF_STATION_IDS = "station_ids"  # manual entry (comma separated)
CONF_SCAN_INTERVAL_MIN = "scan_interval_minutes"

DEFAULT_RADIUS_KM = 10
MAX_RADIUS_KM = 30
MAX_STATIONS = 10
DEFAULT_SCAN_INTERVAL_MIN = 30
MIN_SCAN_INTERVAL_MIN = 15
DEFAULT_SCAN_INTERVAL = timedelta(minutes=DEFAULT_SCAN_INTERVAL_MIN)

# Gentle network behaviour
REQUEST_TIMEOUT_S = 20
MAX_CONCURRENT_REQUESTS = 2
BACKOFF_MULTIPLIER = 2
MAX_BACKOFF_MINUTES = 180

# Product codes as returned by the hot-data API -> human readable labels.
FUEL_LABELS: dict[str, str] = {
    "E10": "SP95-E10",
    "SP8": "SP98",
    "SP95": "SP95",
    "GO": "Gazole",
    "GOEX": "Excellium Gazole",
    "E85": "E85",
    "GPLC": "GPLc",
    "ADBLUE": "AdBlue",
}
DEFAULT_FUELS = ["E10", "SP8"]

AVAILABILITY_AVAILABLE = "AVAILABLE"
AVAILABILITY_UNAVAILABLE = "UNAVAILABLE"
AVAILABILITY_UNKNOWN = "UNKNOWN"

MANUFACTURER = "TotalEnergies (unofficial data)"

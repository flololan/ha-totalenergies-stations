"""Async client for the public web endpoints of the TotalEnergies station map.

The keys used by the map are discovered at runtime from the publicly served
JavaScript of the map (loader.js / front.js) and cached in memory only.
Nothing is hardcoded and nothing is persisted.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp

from .const import (
    FRONT_URL,
    HOT_DATA_URL,
    LOADER_URL,
    MAX_CONCURRENT_REQUESTS,
    REQUEST_TIMEOUT_S,
    SITE_ORIGIN,
    SITE_PAGE,
    USER_AGENT,
    WOOSMAP_SEARCH_URL,
)
from .parsing import (
    StationData,
    StationSummary,
    extract_total_key,
    extract_woos_key,
    parse_hot_data,
    parse_woosmap_search,
)

_LOGGER = logging.getLogger(__name__)

# Status codes that indicate our discovered key is no longer accepted.
AUTH_ERROR_STATUSES = frozenset({401, 403, 404})


class TotalEnergiesApiError(Exception):
    """Generic API error."""


class KeyDiscoveryError(TotalEnergiesApiError):
    """Raised when the public keys cannot be discovered."""


class ApiAuthError(TotalEnergiesApiError):
    """Raised when the API rejects the discovered key (401/403)."""

    def __init__(self, status: int, message: str = "") -> None:
        super().__init__(message or f"HTTP {status}")
        self.status = status


class TotalEnergiesStationsApi:
    """Thin async wrapper around the station map endpoints."""

    def __init__(self, session: aiohttp.ClientSession) -> None:
        self._session = session
        self._woos_key: str | None = None
        self._total_key: str | None = None
        self._discovery_lock = asyncio.Lock()
        self._semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)
        self._timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT_S)

    # ------------------------------------------------------------------ keys
    @property
    def keys_discovered(self) -> bool:
        """Return True if both keys are cached."""
        return bool(self._woos_key and self._total_key)

    async def _fetch_text(self, url: str, headers: dict[str, str]) -> str:
        async with self._semaphore:
            async with self._session.get(
                url, headers={"User-Agent": USER_AGENT, **headers}, timeout=self._timeout
            ) as resp:
                resp.raise_for_status()
                return await resp.text(errors="replace")

    async def async_discover_keys(self, force: bool = False) -> None:
        """Discover the public keys from the map's JavaScript (cached)."""
        async with self._discovery_lock:
            if self.keys_discovered and not force:
                return
            _LOGGER.debug("Discovering public keys from the station map scripts")
            try:
                loader_js = await self._fetch_text(LOADER_URL, {"Referer": SITE_PAGE})
                front_js = await self._fetch_text(FRONT_URL, {"Referer": SITE_PAGE})
            except (TimeoutError, aiohttp.ClientError) as err:
                raise KeyDiscoveryError(f"Could not fetch map scripts: {err}") from err

            # loader.js carries the Woosmap key; front.js carries both keys and
            # serves as fallback should the loader change.
            woos_key = extract_woos_key(loader_js) or extract_woos_key(front_js)
            total_key = extract_total_key(front_js)
            if not woos_key or not total_key:
                raise KeyDiscoveryError(
                    "Public keys not found in map scripts (site may have changed)"
                )
            self._woos_key = woos_key
            self._total_key = total_key
            _LOGGER.debug("Public keys discovered (values are never logged)")

    async def async_ensure_keys(self) -> None:
        """Discover keys if not cached yet."""
        if not self.keys_discovered:
            await self.async_discover_keys()

    # ---------------------------------------------------------------- search
    async def async_search_stations(
        self, latitude: float, longitude: float, radius_m: int
    ) -> list[StationSummary]:
        """Search stations around a point (radius in metres)."""
        await self.async_ensure_keys()
        params = {
            "key": self._woos_key,
            "lat": f"{latitude:.6f}",
            "lng": f"{longitude:.6f}",
            "radius": str(int(radius_m)),
        }
        # The public Woosmap key is domain-bound; the endpoint only answers
        # when Origin/Referer point to the station map. No browser spoofing.
        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
            "Origin": SITE_ORIGIN,
            "Referer": SITE_PAGE,
        }
        try:
            async with self._semaphore:
                async with self._session.get(
                    WOOSMAP_SEARCH_URL,
                    params=params,
                    headers=headers,
                    timeout=self._timeout,
                ) as resp:
                    if resp.status in (401, 403):
                        raise ApiAuthError(resp.status, "Woosmap rejected the key")
                    resp.raise_for_status()
                    payload: dict[str, Any] = await resp.json(content_type=None)
        except (TimeoutError, aiohttp.ClientError) as err:
            raise TotalEnergiesApiError(f"Station search failed: {err}") from err
        return parse_woosmap_search(payload)

    # -------------------------------------------------------------- hot data
    async def async_get_station(self, location_id: str) -> StationData:
        """Fetch price/availability for one station.

        Returns StationData(has_data=False) when the API answers 404.
        Raises ApiAuthError for 401/403.
        """
        await self.async_ensure_keys()
        params = {"location_id": location_id, "type": "FUELING"}
        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
            "API-Key": self._total_key or "",
        }
        try:
            async with self._semaphore:
                async with self._session.get(
                    HOT_DATA_URL, params=params, headers=headers, timeout=self._timeout
                ) as resp:
                    if resp.status == 404:
                        _LOGGER.debug("No hot data for station %s (404)", location_id)
                        return parse_hot_data(location_id, None)
                    if resp.status in (401, 403):
                        raise ApiAuthError(resp.status, "Hot-data API rejected the key")
                    resp.raise_for_status()
                    payload = await resp.json(content_type=None)
        except (TimeoutError, aiohttp.ClientError) as err:
            raise TotalEnergiesApiError(
                f"Hot data request failed for {location_id}: {err}"
            ) from err
        if not isinstance(payload, dict):
            return parse_hot_data(location_id, None)
        return parse_hot_data(location_id, payload)

    async def async_get_stations(self, location_ids: list[str]) -> dict[str, StationData]:
        """Fetch several stations with limited concurrency.

        If *all* stations fail with 401/403/404, the keys are re-discovered
        once and the batch is retried.
        """
        results = await self._fetch_batch(location_ids)
        if location_ids and all(
            isinstance(r, ApiAuthError) or (isinstance(r, StationData) and not r.has_data)
            for r in results.values()
        ):
            _LOGGER.info("All stations returned 401/403/404 - re-discovering keys once")
            await self.async_discover_keys(force=True)
            results = await self._fetch_batch(location_ids)

        out: dict[str, StationData] = {}
        errors: list[str] = []
        for lid, res in results.items():
            if isinstance(res, StationData):
                out[lid] = res
            else:
                errors.append(f"{lid}: {res}")
        if errors and not out:
            raise TotalEnergiesApiError("; ".join(errors))
        if errors:
            _LOGGER.warning("Some stations could not be updated: %s", "; ".join(errors))
        return out

    async def _fetch_batch(self, location_ids: list[str]) -> dict[str, StationData | Exception]:
        async def _one(lid: str) -> StationData | Exception:
            try:
                return await self.async_get_station(lid)
            except TotalEnergiesApiError as err:
                return err

        coros = [_one(lid) for lid in location_ids]
        gathered = await asyncio.gather(*coros)
        return dict(zip(location_ids, gathered, strict=True))

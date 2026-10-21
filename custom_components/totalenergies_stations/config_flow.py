"""Config flow for TotalEnergies Stations (unofficial)."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import KeyDiscoveryError, TotalEnergiesApiError, TotalEnergiesStationsApi
from .const import (
    CONF_FUELS,
    CONF_NOTIFY_PERSISTENT,
    CONF_RADIUS_KM,
    CONF_SCAN_INTERVAL_MIN,
    CONF_STATION_IDS,
    CONF_STATIONS,
    DEFAULT_FUELS,
    DEFAULT_NOTIFY_PERSISTENT,
    DEFAULT_RADIUS_KM,
    DEFAULT_SCAN_INTERVAL_MIN,
    DOMAIN,
    FUEL_LABELS,
    MAX_RADIUS_KM,
    MAX_STATIONS,
    MIN_SCAN_INTERVAL_MIN,
)
from .parsing import StationSummary, parse_station_ids

_LOGGER = logging.getLogger(__name__)

CONF_LOCATION = "location"


def _fuel_selector() -> selector.SelectSelector:
    return selector.SelectSelector(
        selector.SelectSelectorConfig(
            options=[
                selector.SelectOptionDict(value=code, label=label)
                for code, label in FUEL_LABELS.items()
            ],
            multiple=True,
            mode=selector.SelectSelectorMode.LIST,
        )
    )


def _unique_id_for(station_ids: list[str]) -> str:
    return "|".join(sorted(station_ids))


class TotalEnergiesConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the config flow."""

    VERSION = 1

    def __init__(self) -> None:
        self._fuels: list[str] = list(DEFAULT_FUELS)
        self._found: list[StationSummary] = []

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> TotalEnergiesOptionsFlow:
        """Return the options flow."""
        return TotalEnergiesOptionsFlow()

    # ---------------------------------------------------------------- menu
    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Entry point: choose between radius search and manual station IDs."""
        return self.async_show_menu(step_id="user", menu_options=["search", "manual"])

    # -------------------------------------------------------------- search
    async def async_step_search(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Ask for location, radius and fuels, then search stations."""
        errors: dict[str, str] = {}
        if user_input is not None:
            location = user_input[CONF_LOCATION]
            lat = float(location["latitude"])
            lng = float(location["longitude"])
            radius_km = float(user_input[CONF_RADIUS_KM])
            self._fuels = list(user_input.get(CONF_FUELS) or DEFAULT_FUELS)

            api = TotalEnergiesStationsApi(async_get_clientsession(self.hass))
            try:
                self._found = await api.async_search_stations(lat, lng, int(radius_km * 1000))
            except KeyDiscoveryError:
                errors["base"] = "key_discovery_failed"
            except TotalEnergiesApiError:
                errors["base"] = "cannot_connect"
            else:
                if not self._found:
                    errors["base"] = "no_stations"
                else:
                    return await self.async_step_select()

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_LOCATION,
                    default={
                        "latitude": self.hass.config.latitude,
                        "longitude": self.hass.config.longitude,
                    },
                ): selector.LocationSelector(selector.LocationSelectorConfig(radius=False)),
                vol.Required(CONF_RADIUS_KM, default=DEFAULT_RADIUS_KM): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1,
                        max=MAX_RADIUS_KM,
                        step=1,
                        unit_of_measurement="km",
                        mode=selector.NumberSelectorMode.SLIDER,
                    )
                ),
                vol.Required(CONF_FUELS, default=list(self._fuels)): _fuel_selector(),
            }
        )
        return self.async_show_form(step_id="search", data_schema=schema, errors=errors)

    async def async_step_select(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Let the user pick up to MAX_STATIONS of the found stations."""
        errors: dict[str, str] = {}
        if user_input is not None:
            chosen_ids = list(user_input.get(CONF_STATIONS) or [])
            if not chosen_ids:
                errors["base"] = "no_selection"
            elif len(chosen_ids) > MAX_STATIONS:
                errors["base"] = "too_many_stations"
            else:
                stations = [s.as_dict() for s in self._found if s.location_id in chosen_ids]
                return await self._async_create(stations)

        options = []
        for station in self._found:
            dist = (
                f" ({station.distance_m / 1000:.1f} km)" if station.distance_m is not None else ""
            )
            label = (
                f"{station.name or station.location_id}{dist}"
                f" - {station.address or ''} [{station.location_id}]"
            )
            options.append(
                selector.SelectOptionDict(value=station.location_id, label=label.strip())
            )
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_STATIONS, default=[s.location_id for s in self._found[:MAX_STATIONS]]
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=options, multiple=True, mode=selector.SelectSelectorMode.LIST
                    )
                )
            }
        )
        return self.async_show_form(
            step_id="select",
            data_schema=schema,
            errors=errors,
            description_placeholders={"count": str(len(self._found)), "max": str(MAX_STATIONS)},
        )

    # -------------------------------------------------------------- manual
    async def async_step_manual(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Enter station IDs (NF...) manually."""
        errors: dict[str, str] = {}
        if user_input is not None:
            ids = parse_station_ids(user_input.get(CONF_STATION_IDS, ""))
            self._fuels = list(user_input.get(CONF_FUELS) or DEFAULT_FUELS)
            if not ids:
                errors["base"] = "no_selection"
            elif len(ids) > MAX_STATIONS:
                errors["base"] = "too_many_stations"
            else:
                stations = [{"location_id": lid, "name": lid, "address": None} for lid in ids]
                return await self._async_create(stations)

        schema = vol.Schema(
            {
                vol.Required(CONF_STATION_IDS): selector.TextSelector(
                    selector.TextSelectorConfig(multiline=True)
                ),
                vol.Required(CONF_FUELS, default=list(self._fuels)): _fuel_selector(),
            }
        )
        return self.async_show_form(
            step_id="manual",
            data_schema=schema,
            errors=errors,
            description_placeholders={"max": str(MAX_STATIONS)},
        )

    # -------------------------------------------------------------- create
    async def _async_create(self, stations: list[dict[str, Any]]) -> ConfigFlowResult:
        ids = [s["location_id"] for s in stations]
        await self.async_set_unique_id(_unique_id_for(ids))
        self._abort_if_unique_id_configured()

        # Enrich name/address from hot data (best effort, also validates IDs).
        api = TotalEnergiesStationsApi(async_get_clientsession(self.hass))
        try:
            data = await api.async_get_stations(ids)
        except TotalEnergiesApiError as err:
            _LOGGER.debug("Could not fetch hot data during setup: %s", err)
            data = {}
        for station in stations:
            info = data.get(station["location_id"])
            if info and info.has_data:
                station["name"] = station.get("name") or info.name or station["location_id"]
                if info.name and station["name"] == station["location_id"]:
                    station["name"] = info.name
                station["address"] = station.get("address") or info.address

        title = stations[0]["name"] if len(stations) == 1 else f"{len(stations)} stations"
        return self.async_create_entry(
            title=f"TotalEnergies: {title}",
            data={
                CONF_STATIONS: stations,
                CONF_FUELS: self._fuels,
                CONF_SCAN_INTERVAL_MIN: DEFAULT_SCAN_INTERVAL_MIN,
            },
            options={CONF_FUELS: self._fuels, CONF_SCAN_INTERVAL_MIN: DEFAULT_SCAN_INTERVAL_MIN},
        )


class TotalEnergiesOptionsFlow(OptionsFlow):
    """Options: poll interval, fuels and persistent notifications."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Show/handle the options form."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current_fuels = self.config_entry.options.get(
            CONF_FUELS, self.config_entry.data.get(CONF_FUELS, DEFAULT_FUELS)
        )
        current_interval = self.config_entry.options.get(
            CONF_SCAN_INTERVAL_MIN,
            self.config_entry.data.get(CONF_SCAN_INTERVAL_MIN, DEFAULT_SCAN_INTERVAL_MIN),
        )
        current_notify = self.config_entry.options.get(
            CONF_NOTIFY_PERSISTENT, DEFAULT_NOTIFY_PERSISTENT
        )
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_SCAN_INTERVAL_MIN, default=current_interval
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=MIN_SCAN_INTERVAL_MIN,
                        max=720,
                        step=5,
                        unit_of_measurement="min",
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
                vol.Required(CONF_FUELS, default=list(current_fuels)): _fuel_selector(),
                vol.Required(
                    CONF_NOTIFY_PERSISTENT, default=bool(current_notify)
                ): selector.BooleanSelector(),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)

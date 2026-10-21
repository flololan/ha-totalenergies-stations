"""Unit tests for the framework-free parsing helpers (synthetic fixtures only)."""

import json
from pathlib import Path

import pytest

from custom_components.totalenergies_stations import parsing
from custom_components.totalenergies_stations.const import FUEL_LABELS

FIXTURES = Path(__file__).parent / "fixtures"


def load(name: str):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


# ------------------------------------------------------------------ key discovery
def test_extract_woos_key_from_synthetic_loader():
    fake_key = "woos-00000000-1111-2222-3333-444444444444"  # synthetic UUID-like
    assert len(fake_key) == len("woos-") + 36
    js = f'var x = {{apiKey:"{fake_key}", other: 1}};'
    assert parsing.extract_woos_key(js) == fake_key


def test_extract_woos_key_missing():
    assert parsing.extract_woos_key("nothing here") is None
    assert parsing.extract_woos_key("") is None


def test_extract_total_key_from_synthetic_front():
    js = 'const cfg={hotDataUrl:"https://example.invalid/?",totalKey:"FAKE~not-a-real-key",x:1};'
    assert parsing.extract_total_key(js) == "FAKE~not-a-real-key"
    assert parsing.extract_total_key("totalKey:''") is None


# ------------------------------------------------------------------ woosmap search
def test_parse_woosmap_search_dedupes_and_sorts():
    stations = parsing.parse_woosmap_search(load("woosmap_search.json"))
    ids = [s.location_id for s in stations]
    # NF000001 appears twice (FUELING + WASH) -> once; store_id fallback kept
    assert ids == ["NF000002", "NF000001", "fallback_store_id_only"]
    first = stations[0]
    assert first.name == "RELAIS EXAMPLE SUD"
    assert first.address == "2 AVENUE FICTIVE, 99000 TESTVILLE"
    assert first.latitude == pytest.approx(48.2)
    assert first.longitude == pytest.approx(7.2)
    assert stations[2].distance_m is None
    assert stations[2].address == "99000 TESTVILLE"


def test_parse_woosmap_search_empty_and_malformed():
    assert parsing.parse_woosmap_search({}) == []
    assert parsing.parse_woosmap_search({"features": None}) == []
    assert parsing.parse_woosmap_search({"features": [{"properties": {}}]}) == []


def test_station_summary_as_dict_has_no_coordinates():
    s = parsing.StationSummary("NF1", "n", "a", 1.0, 48.0, 7.0)
    assert s.as_dict() == {"location_id": "NF1", "name": "n", "address": "a"}


# ------------------------------------------------------------------ hot data
def test_parse_hot_data_full():
    data = parsing.parse_hot_data("NF000001", load("hot_data_station.json"))
    assert data.has_data is True
    assert data.name == "RELAIS EXAMPLE NORD"
    assert data.address == "1 RUE DU TEST, 99000 TESTVILLE"
    assert data.opening_status == "OPEN"
    # only ENERGIES with a product_code
    assert set(data.fuels) == {"E10", "SP8", "GO", "GPLC", "E85"}

    e10 = data.fuels["E10"]
    assert e10.price == 1.99
    assert e10.availability_status == "UNAVAILABLE"
    assert e10.is_available is False
    assert e10.label == "SP95-E10"

    sp98 = data.fuels["SP8"]
    assert sp98.is_available is True
    assert sp98.label == "SP98"
    assert sp98.product_name == "Excellium SP98"

    go = data.fuels["GO"]
    assert go.price == 2.25  # string price converted
    assert go.product_name == "Diesel Premier"  # stripped
    assert go.availability_status == "UNKNOWN"
    assert go.is_available is None

    gplc = data.fuels["GPLC"]
    assert gplc.price is None
    assert gplc.availability_status is None
    assert gplc.is_available is None

    # unknown status strings are mapped to UNKNOWN, never to True/False
    assert data.fuels["E85"].availability_status == "UNKNOWN"
    assert data.fuels["E85"].is_available is None


def test_parse_hot_data_404_means_no_data():
    data = parsing.parse_hot_data("NF999999", None)
    assert data.has_data is False
    assert data.fuels == {}
    assert data.location_id == "NF999999"
    assert data.opening_status is None


def test_parse_hot_data_minimal_payload():
    data = parsing.parse_hot_data("NF1", {"products_and_services": None})
    assert data.has_data is True
    assert data.fuels == {}
    assert data.address is None


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("AVAILABLE", "AVAILABLE"),
        ("available", "AVAILABLE"),
        (" unavailable ", "UNAVAILABLE"),
        ("UNKNOWN", "UNKNOWN"),
        ("weird", "UNKNOWN"),
        ("", None),
        (None, None),
    ],
)
def test_normalize_availability(raw, expected):
    assert parsing.normalize_availability(raw) == expected


# ------------------------------------------------------------------ product codes
def test_product_code_mapping():
    assert FUEL_LABELS["SP8"] == "SP98"
    assert FUEL_LABELS["E10"] == "SP95-E10"
    assert FUEL_LABELS["GO"] == "Gazole"
    assert FUEL_LABELS["GOEX"] == "Excellium Gazole"
    assert parsing.FuelInfo("XYZ").label == "XYZ"


# ------------------------------------------------------------------ manual IDs
def test_parse_station_ids():
    assert parsing.parse_station_ids("nf000001, NF000002\nNF000001; nf000003") == [
        "NF000001",
        "NF000002",
        "NF000003",
    ]
    assert parsing.parse_station_ids("") == []
    assert parsing.parse_station_ids(None) == []

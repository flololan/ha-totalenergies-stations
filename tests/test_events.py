"""Tests for the availability change detection used for events/notifications."""

from custom_components.totalenergies_stations.events import detect_availability_changes
from custom_components.totalenergies_stations.parsing import FuelInfo, StationData


def _station(location_id: str, **fuels: str | None) -> StationData:
    return StationData(
        location_id=location_id,
        name=f"Station {location_id}",
        fuels={
            code: FuelInfo(product_code=code, product_name=code, price=1.99, availability_status=st)
            for code, st in fuels.items()
        },
    )


def test_first_refresh_never_fires():
    current = {"NF1": _station("NF1", E10="AVAILABLE")}
    assert detect_availability_changes(None, current) == []


def test_unavailable_to_available_fires_event():
    previous = {"NF1": _station("NF1", E10="UNAVAILABLE", SP8="UNAVAILABLE")}
    current = {"NF1": _station("NF1", E10="AVAILABLE", SP8="UNAVAILABLE")}
    changes = detect_availability_changes(previous, current, station_names={"NF1": "My station"})
    assert len(changes) == 1
    change = changes[0]
    assert change["location_id"] == "NF1"
    assert change["station_name"] == "My station"
    assert change["product_code"] == "E10"
    assert change["available"] is True
    assert change["previous_available"] is False
    assert change["availability_status"] == "AVAILABLE"
    assert change["price"] == 1.99


def test_available_to_unavailable_fires_event():
    previous = {"NF1": _station("NF1", E10="AVAILABLE")}
    current = {"NF1": _station("NF1", E10="UNAVAILABLE")}
    changes = detect_availability_changes(previous, current)
    assert [(c["available"], c["previous_available"]) for c in changes] == [(False, True)]
    assert changes[0]["station_name"] == "Station NF1"


def test_no_change_and_unknown_are_ignored():
    previous = {"NF1": _station("NF1", E10="AVAILABLE", SP8="UNKNOWN", GO=None)}
    current = {"NF1": _station("NF1", E10="AVAILABLE", SP8="AVAILABLE", GO="AVAILABLE")}
    assert detect_availability_changes(previous, current) == []
    # available -> unknown is not a change either
    assert detect_availability_changes(current, previous) == []


def test_fuel_filter_and_new_station():
    previous = {"NF1": _station("NF1", E10="UNAVAILABLE", SP8="UNAVAILABLE")}
    current = {
        "NF1": _station("NF1", E10="AVAILABLE", SP8="AVAILABLE"),
        "NF2": _station("NF2", E10="AVAILABLE"),  # new station -> no history -> ignored
    }
    changes = detect_availability_changes(previous, current, fuels=["SP8"])
    assert [c["product_code"] for c in changes] == ["SP8"]
    changes = detect_availability_changes(previous, current, fuels=["E10", "SP8", "GO"])
    assert sorted(c["product_code"] for c in changes) == ["E10", "SP8"]

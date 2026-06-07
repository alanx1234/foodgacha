from __future__ import annotations

from foodgacha import main


def test_coordinates_are_cached(monkeypatch) -> None:
    calls = 0

    def fake_geocode(location: str):
        nonlocal calls
        calls += 1
        return 32.7157, -117.1611, "San Diego, California, USA"

    monkeypatch.setattr(main, "geocode_location", fake_geocode)
    monkeypatch.setattr(main, "save_data", lambda data: None)
    data = {"geocache": {}}

    first = main._coordinates_for(data, "San Diego, CA")
    second = main._coordinates_for(data, "san diego, ca")

    assert first == second
    assert calls == 1


def test_restaurant_results_are_cached(monkeypatch) -> None:
    calls = 0

    def fake_search(latitude: float, longitude: float):
        nonlocal calls
        calls += 1
        return [{"id": "osm-node-1", "name": "Cafe"}]

    monkeypatch.setattr(main, "search_restaurants", fake_search)
    monkeypatch.setattr(main, "save_data", lambda data: None)
    data = {"restaurant_cache": {}}

    first = main._restaurants_for(data, 32.7157, -117.1611)
    second = main._restaurants_for(data, 32.7157, -117.1611)

    assert first == second
    assert calls == 1

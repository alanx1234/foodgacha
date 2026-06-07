from __future__ import annotations

import httpx

from foodgacha.openstreetmap import (
    USER_AGENT,
    geocode_location,
    search_restaurants,
)


def test_geocode_location_uses_identifying_user_agent(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_get(url, *, headers, params, timeout):
        captured.update(
            {"url": url, "headers": headers, "params": params, "timeout": timeout}
        )
        return httpx.Response(
            200,
            json=[
                {
                    "lat": "32.7157",
                    "lon": "-117.1611",
                    "display_name": "San Diego, California, USA",
                }
            ],
            request=httpx.Request("GET", url),
        )

    monkeypatch.setattr(httpx, "get", fake_get)

    result = geocode_location("San Diego, CA")

    assert result == (32.7157, -117.1611, "San Diego, California, USA")
    assert captured["headers"] == {"User-Agent": USER_AGENT}
    assert captured["params"] == {
        "q": "San Diego, CA",
        "format": "jsonv2",
        "limit": 1,
    }


def test_restaurant_search_normalizes_and_sorts_results(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_post(url, *, headers, data, timeout):
        captured.update(
            {"url": url, "headers": headers, "data": data, "timeout": timeout}
        )
        return httpx.Response(
            200,
            json={
                "elements": [
                    {
                        "type": "node",
                        "id": 2,
                        "lat": 32.73,
                        "lon": -117.17,
                        "tags": {
                            "name": "Far Cafe",
                            "amenity": "cafe",
                            "cuisine": "coffee_shop",
                        },
                    },
                    {
                        "type": "way",
                        "id": 1,
                        "center": {"lat": 32.716, "lon": -117.161},
                        "tags": {
                            "name": "Near Ramen",
                            "amenity": "restaurant",
                            "cuisine": "ramen;japanese",
                            "opening_hours": "Mo-Su 11:00-22:00",
                            "website": "https://example.com",
                        },
                    },
                ]
            },
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr(httpx, "post", fake_post)

    results = search_restaurants(32.7157, -117.1611)

    assert [result["name"] for result in results] == ["Near Ramen", "Far Cafe"]
    assert results[0]["id"] == "osm-way-1"
    assert results[0]["cuisines"] == ["ramen", "japanese"]
    assert results[0]["url"] == "https://www.openstreetmap.org/way/1"
    assert captured["headers"] == {"User-Agent": USER_AGENT}
    assert '"amenity"~"^(restaurant|fast_food|cafe|food_court)$"' in str(
        captured["data"]
    )


def test_restaurant_search_falls_back_after_transient_error(monkeypatch) -> None:
    calls: list[str] = []

    def fake_post(url, *, headers, data, timeout):
        calls.append(url)
        request = httpx.Request("POST", url)
        if len(calls) == 1:
            return httpx.Response(504, request=request)
        return httpx.Response(200, json={"elements": []}, request=request)

    monkeypatch.setattr(httpx, "post", fake_post)

    assert search_restaurants(32.7157, -117.1611) == []
    assert len(calls) == 2

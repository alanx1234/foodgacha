from __future__ import annotations

import math
from typing import Any

import httpx

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
OVERPASS_URLS = (
    "https://overpass-api.de/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
)
USER_AGENT = "foodgacha/0.2 (+https://github.com/alanx1234/foodgacha)"
DEFAULT_RADIUS_METERS = 3000


class OpenStreetMapError(RuntimeError):
    """A user-facing OpenStreetMap service failure."""


def geocode_location(location: str) -> tuple[float, float, str]:
    try:
        response = httpx.get(
            NOMINATIM_URL,
            headers={"User-Agent": USER_AGENT},
            params={
                "q": location,
                "format": "jsonv2",
                "limit": 1,
            },
            timeout=15,
        )
        response.raise_for_status()
        payload = response.json()
    except httpx.HTTPStatusError as exc:
        raise OpenStreetMapError(
            f"Location lookup failed ({exc.response.status_code})."
        ) from exc
    except (httpx.HTTPError, ValueError) as exc:
        raise OpenStreetMapError(f"Could not look up that location: {exc}") from exc

    if not isinstance(payload, list) or not payload:
        raise OpenStreetMapError(f"Could not find a location matching {location!r}.")

    result = payload[0]
    try:
        return (
            float(result["lat"]),
            float(result["lon"]),
            str(result.get("display_name") or location),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise OpenStreetMapError(
            "OpenStreetMap returned an unexpected location response."
        ) from exc


def search_restaurants(
    latitude: float,
    longitude: float,
    radius_meters: int = DEFAULT_RADIUS_METERS,
    limit: int = 60,
) -> list[dict[str, Any]]:
    query = _restaurant_query(latitude, longitude, radius_meters)
    payload = _query_overpass(query)

    elements = payload.get("elements", [])
    if not isinstance(elements, list):
        raise OpenStreetMapError(
            "OpenStreetMap returned an unexpected restaurant response."
        )

    restaurants = [
        restaurant
        for element in elements
        if isinstance(element, dict)
        if (restaurant := _normalize_element(element, latitude, longitude)) is not None
    ]
    restaurants.sort(key=lambda item: float(item["distance"]))
    return restaurants[:limit]


def _query_overpass(query: str) -> dict[str, Any]:
    last_error: Exception | None = None
    for url in OVERPASS_URLS:
        try:
            response = httpx.post(
                url,
                headers={"User-Agent": USER_AGENT},
                data={"data": query},
                timeout=12,
            )
            response.raise_for_status()
            payload = response.json()
            if isinstance(payload, dict):
                return payload
            raise ValueError("response was not a JSON object")
        except httpx.HTTPStatusError as exc:
            last_error = exc
            if exc.response.status_code not in {429, 502, 503, 504}:
                break
        except (httpx.HTTPError, ValueError) as exc:
            last_error = exc

    if isinstance(last_error, httpx.HTTPStatusError):
        raise OpenStreetMapError(
            f"Restaurant search failed ({last_error.response.status_code}). "
            "Try again shortly."
        ) from last_error
    raise OpenStreetMapError(
        f"Could not search OpenStreetMap: {last_error or 'unknown error'}"
    ) from last_error


def _restaurant_query(latitude: float, longitude: float, radius_meters: int) -> str:
    return f"""
[out:json][timeout:12];
(
  nwr["amenity"~"^(restaurant|fast_food|cafe|food_court)$"]
    (around:{radius_meters},{latitude},{longitude});
);
out center 100;
""".strip()


def _normalize_element(
    element: dict[str, Any],
    origin_latitude: float,
    origin_longitude: float,
) -> dict[str, Any] | None:
    tags = element.get("tags")
    if not isinstance(tags, dict):
        return None
    name = str(tags.get("name") or tags.get("brand") or "").strip()
    if not name:
        return None

    center = element.get("center") if isinstance(element.get("center"), dict) else {}
    latitude = element.get("lat", center.get("lat"))
    longitude = element.get("lon", center.get("lon"))
    try:
        latitude = float(latitude)
        longitude = float(longitude)
    except (TypeError, ValueError):
        return None

    element_type = str(element.get("type", "node"))
    element_id = str(element.get("id", ""))
    cuisines = _split_values(tags.get("cuisine"))
    amenity = str(tags.get("amenity", "restaurant"))
    return {
        "id": f"osm-{element_type}-{element_id}",
        "name": name,
        "cuisines": cuisines,
        "cuisine": _display_cuisine(cuisines, amenity),
        "amenity": amenity,
        "tags": {str(key): str(value) for key, value in tags.items()},
        "distance": _distance_meters(
            origin_latitude,
            origin_longitude,
            latitude,
            longitude,
        ),
        "coordinates": {"latitude": latitude, "longitude": longitude},
        "url": f"https://www.openstreetmap.org/{element_type}/{element_id}",
        "price_level": _price_level(tags),
    }


def _split_values(value: Any) -> list[str]:
    if not value:
        return []
    normalized = str(value).lower().replace(",", ";")
    return [
        item.strip().replace(" ", "_")
        for item in normalized.split(";")
        if item.strip()
    ]


def _display_cuisine(cuisines: list[str], amenity: str) -> str:
    if cuisines:
        return cuisines[0].replace("_", " ").title()
    return {
        "fast_food": "Fast Food",
        "food_court": "Food Court",
    }.get(amenity, amenity.replace("_", " ").title())


def _price_level(tags: dict[str, Any]) -> int | None:
    value = str(tags.get("price") or tags.get("price_range") or "").strip()
    if value and set(value) == {"$"}:
        return min(len(value), 4)
    return None


def _distance_meters(
    latitude_1: float,
    longitude_1: float,
    latitude_2: float,
    longitude_2: float,
) -> float:
    earth_radius = 6_371_000
    lat_1 = math.radians(latitude_1)
    lat_2 = math.radians(latitude_2)
    delta_lat = math.radians(latitude_2 - latitude_1)
    delta_lon = math.radians(longitude_2 - longitude_1)
    a = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat_1) * math.cos(lat_2) * math.sin(delta_lon / 2) ** 2
    )
    return earth_radius * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

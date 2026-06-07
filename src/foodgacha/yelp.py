from __future__ import annotations

import os
from typing import Any

import httpx

SEARCH_URL = "https://api.yelp.com/v3/businesses/search"

CUISINE_MAP = {
    "japanese": "ramen,sushi,japanese",
    "korean": "korean",
    "mexican": "mexican",
    "italian": "italian",
    "american": "burgers,newamerican,tradamerican",
    "thai": "thai",
    "chinese": "chinese",
    "indian": "indpak",
    "vietnamese": "vietnamese",
    "mediterranean": "mediterranean",
}


class YelpError(RuntimeError):
    """A user-facing Yelp API failure."""


def search_businesses(
    location: str,
    cuisines: list[str] | None = None,
    prices: list[int] | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    api_key = os.environ.get("YELP_API_KEY")
    if not api_key:
        raise YelpError(
            "YELP_API_KEY is not set. Create a Yelp API key and export it first."
        )

    params: dict[str, str | int] = {
        "location": location,
        "limit": limit,
        "sort_by": "best_match",
    }
    categories = _category_aliases(cuisines or [])
    if categories:
        params["categories"] = ",".join(categories)
    if prices:
        params["price"] = ",".join(str(price) for price in sorted(set(prices)))

    try:
        response = httpx.get(
            SEARCH_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            params=params,
            timeout=10,
        )
        response.raise_for_status()
        payload = response.json()
    except httpx.HTTPStatusError as exc:
        detail = _error_description(exc.response)
        raise YelpError(f"Yelp search failed ({exc.response.status_code}): {detail}") from exc
    except (httpx.HTTPError, ValueError) as exc:
        raise YelpError(f"Could not reach Yelp: {exc}") from exc

    businesses = payload.get("businesses", [])
    if not isinstance(businesses, list):
        raise YelpError("Yelp returned an unexpected response.")
    return [business for business in businesses if isinstance(business, dict)]


def _category_aliases(cuisines: list[str]) -> list[str]:
    aliases: list[str] = []
    for cuisine in cuisines:
        aliases.extend(CUISINE_MAP.get(cuisine.lower(), cuisine.lower()).split(","))
    return list(dict.fromkeys(alias for alias in aliases if alias))


def _error_description(response: httpx.Response) -> str:
    try:
        error = response.json().get("error", {})
        return str(error.get("description") or error.get("code") or response.reason_phrase)
    except ValueError:
        return response.reason_phrase


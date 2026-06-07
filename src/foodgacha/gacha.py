from __future__ import annotations

import random
from collections.abc import Iterable
from datetime import date, datetime, timedelta, timezone
from typing import Any

RARITY_WEIGHTS = {"SSR": 5, "SR": 35, "R": 60}
RARITY_ORDER = ("SSR", "SR", "R")
PITY_LIMIT = 10


def rarity_for(business: dict[str, Any]) -> str:
    rating = float(business.get("rating") or 0)
    reviews = int(business.get("review_count") or 0)
    if rating >= 4.5 and reviews >= 200:
        return "SSR"
    if rating >= 4.0 or reviews >= 100:
        return "SR"
    return "R"


def choose_restaurant(
    businesses: Iterable[dict[str, Any]],
    pity_counter: int,
    history: list[dict[str, Any]],
    vibes: list[str] | None = None,
    rng: random.Random | None = None,
) -> tuple[dict[str, Any] | None, str | None, int]:
    randomizer = rng or random.Random()
    candidates = filter_candidates(list(businesses), history, vibes or [])
    buckets = {rarity: [] for rarity in RARITY_ORDER}
    for business in candidates:
        buckets[rarity_for(business)].append(business)

    pity_triggered = pity_counter >= PITY_LIMIT - 1
    if pity_triggered and buckets["SSR"]:
        selected_tier = "SSR"
    else:
        rolled_tier = randomizer.choices(
            list(RARITY_WEIGHTS),
            weights=list(RARITY_WEIGHTS.values()),
            k=1,
        )[0]
        selected_tier = _available_tier(rolled_tier, buckets)

    if selected_tier is None:
        return None, None, pity_counter

    tier_candidates = buckets[selected_tier]
    selected = randomizer.choices(
        tier_candidates,
        weights=[_vibe_weight(item, vibes or []) for item in tier_candidates],
        k=1,
    )[0]
    new_pity = 0 if selected_tier == "SSR" else pity_counter + 1
    return selected, selected_tier, new_pity


def filter_candidates(
    businesses: list[dict[str, Any]],
    history: list[dict[str, Any]],
    vibes: list[str],
) -> list[dict[str, Any]]:
    normalized_vibes = {vibe.lower() for vibe in vibes}
    recent_ids = _recently_visited_ids(history)
    known_ids = {str(item.get("id")) for item in history}
    favorite_ids = {
        str(item.get("id")) for item in history if item.get("visited") is True
    }

    candidates = [
        business
        for business in businesses
        if str(business.get("id")) not in recent_ids
    ]
    if "something-new" in normalized_vibes:
        candidates = [
            business
            for business in candidates
            if str(business.get("id")) not in known_ids
        ]
    if "old-favorite" in normalized_vibes:
        candidates = [
            business
            for business in candidates
            if str(business.get("id")) in favorite_ids
        ]
    return candidates


def history_entry(
    business: dict[str, Any],
    rarity: str,
    pulled_at: datetime | None = None,
) -> dict[str, Any]:
    categories = business.get("categories") or []
    first_category = categories[0] if categories else {}
    coordinates = business.get("coordinates") or {}
    return {
        "id": business.get("id", ""),
        "name": business.get("name", "Unknown restaurant"),
        "cuisine": first_category.get("title", "Restaurant"),
        "rarity": rarity,
        "visited": False,
        "rating_given": None,
        "date": (pulled_at or datetime.now(timezone.utc)).date().isoformat(),
        "notes": "",
        "yelp_rating": business.get("rating"),
        "review_count": business.get("review_count", 0),
        "price": business.get("price", ""),
        "distance_miles": round(float(business.get("distance") or 0) / 1609.344, 1),
        "url": business.get("url", ""),
        "coordinates": {
            "latitude": coordinates.get("latitude"),
            "longitude": coordinates.get("longitude"),
        },
    }


def _available_tier(
    rolled_tier: str,
    buckets: dict[str, list[dict[str, Any]]],
) -> str | None:
    start = RARITY_ORDER.index(rolled_tier)
    fallback_order = RARITY_ORDER[start:] + RARITY_ORDER[:start]
    return next((tier for tier in fallback_order if buckets[tier]), None)


def _recently_visited_ids(history: list[dict[str, Any]]) -> set[str]:
    cutoff = date.today() - timedelta(days=7)
    recent: set[str] = set()
    for item in history:
        if not item.get("visited"):
            continue
        try:
            visited_date = date.fromisoformat(str(item.get("date")))
        except ValueError:
            continue
        if visited_date >= cutoff:
            recent.add(str(item.get("id")))
    return recent


def _vibe_weight(business: dict[str, Any], vibes: list[str]) -> float:
    aliases = {
        str(category.get("alias", "")).lower()
        for category in business.get("categories") or []
        if isinstance(category, dict)
    }
    distance_miles = float(business.get("distance") or 0) / 1609.344
    weight = 1.0
    for vibe in vibes:
        if vibe == "quick" and distance_miles <= 2:
            weight += 1.5
        elif vibe == "sit-down" and aliases & {
            "newamerican",
            "tradamerican",
            "italian",
            "mediterranean",
        }:
            weight += 1.0
        elif vibe == "spicy" and aliases & {
            "hotpot",
            "indpak",
            "korean",
            "mexican",
            "szechuan",
            "thai",
        }:
            weight += 1.5
        elif vibe == "light" and aliases & {
            "juicebars",
            "mediterranean",
            "salad",
            "sushi",
            "vegetarian",
            "vietnamese",
        }:
            weight += 1.25
        elif vibe == "filling" and aliases & {
            "bbq",
            "burgers",
            "hotpot",
            "pizza",
            "ramen",
            "steak",
        }:
            weight += 1.25
    return weight

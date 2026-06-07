from __future__ import annotations

import random
from collections.abc import Iterable
from datetime import date, datetime, timedelta, timezone
from typing import Any

RARITY_WEIGHTS = {"SSR": 5, "SR": 15, "R": 25, "U": 30, "C": 25}
RARITY_ORDER = ("SSR", "SR", "R", "U", "C")
RARITY_LABELS = {
    "SSR": "SSR",
    "SR": "SR",
    "R": "Rare",
    "U": "Uncommon",
    "C": "Common",
}
PITY_LIMIT = 10
HISTORY_VIBES = {"something-new", "old-favorite"}

CUISINE_ALIASES = {
    "american": {"american", "burger", "burgers", "steak", "wings"},
    "chinese": {"chinese", "dim_sum", "hotpot", "noodle", "szechuan"},
    "indian": {"indian", "indian_sweet", "nepalese", "pakistani"},
    "italian": {"italian", "pasta", "pizza"},
    "japanese": {"japanese", "ramen", "sushi", "udon"},
    "korean": {"korean", "korean_barbecue"},
    "mediterranean": {"greek", "mediterranean", "middle_eastern"},
    "mexican": {"burrito", "mexican", "taco"},
    "thai": {"thai"},
    "vietnamese": {"pho", "vietnamese"},
}

SPICY_CUISINES = {
    "hotpot",
    "indian",
    "korean",
    "mexican",
    "szechuan",
    "thai",
}
LIGHT_CUISINES = {
    "greek",
    "japanese",
    "mediterranean",
    "salad",
    "sushi",
    "vegetarian",
    "vietnamese",
}
FILLING_CUISINES = {
    "american",
    "barbecue",
    "burger",
    "burgers",
    "hotpot",
    "pasta",
    "pizza",
    "ramen",
    "steak",
}
METADATA_GROUPS = (
    ("opening_hours",),
    ("website", "contact:website"),
    ("phone", "contact:phone"),
    ("takeaway",),
    ("delivery",),
    ("outdoor_seating",),
    ("wheelchair",),
    ("reservation",),
)


def rarity_for(score: int) -> str:
    if score >= 85:
        return "SSR"
    if score >= 70:
        return "SR"
    if score >= 50:
        return "R"
    if score >= 30:
        return "U"
    return "C"


def choose_restaurant(
    businesses: Iterable[dict[str, Any]],
    pity_counter: int,
    history: list[dict[str, Any]],
    cuisines: list[str] | None = None,
    prices: list[int] | None = None,
    vibes: list[str] | None = None,
    rng: random.Random | None = None,
) -> tuple[dict[str, Any] | None, str | None, int]:
    randomizer = rng or random.Random()
    candidates = filter_candidates(list(businesses), history, vibes or [])
    buckets = {rarity: [] for rarity in RARITY_ORDER}
    for business in candidates:
        score, reasons = match_score(
            business,
            cuisines or [],
            prices or [],
            vibes or [],
            history,
        )
        scored_business = {**business, "match_score": score, "match_reasons": reasons}
        buckets[rarity_for(score)].append(scored_business)

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
    selected = randomizer.choice(tier_candidates)
    new_pity = 0 if selected_tier == "SSR" else pity_counter + 1
    return selected, selected_tier, new_pity


def match_score(
    business: dict[str, Any],
    cuisines: list[str],
    prices: list[int],
    vibes: list[str],
    history: list[dict[str, Any]],
) -> tuple[int, list[str]]:
    score = 0
    reasons: list[str] = []
    business_cuisines = {
        str(cuisine).lower().replace(" ", "_")
        for cuisine in business.get("cuisines") or []
    }
    tags = {
        str(key): str(value).lower()
        for key, value in (business.get("tags") or {}).items()
    }
    normalized_vibes = normalize_vibes(vibes)
    history_ids = {str(entry.get("id")) for entry in history}
    visited_ids = {
        str(entry.get("id")) for entry in history if entry.get("visited") is True
    }
    business_id = str(business.get("id"))

    requested_cuisines = {cuisine.lower() for cuisine in cuisines}
    if any(
        business_cuisines & CUISINE_ALIASES.get(cuisine, {cuisine})
        for cuisine in requested_cuisines
    ):
        score += 40
        reasons.append("cuisine match")

    matched_vibes = [
        vibe
        for vibe in normalized_vibes
        if _matches_vibe(
            vibe,
            business,
            business_cuisines,
            tags,
            business_id in history_ids,
            business_id in visited_ids,
        )
    ]
    if matched_vibes:
        score += 15 * len(matched_vibes)
        reasons.extend(f"{vibe.replace('-', ' ')} vibe" for vibe in matched_vibes)

    price_level = business.get("price_level")
    if price_level is not None and int(price_level) in prices:
        score += 10
        reasons.append("price match")

    distance_miles = float(business.get("distance") or 0) / 1609.344
    if distance_miles <= 2:
        score += 15
        reasons.append("within two miles")

    metadata_points = min(
        sum(any(tags.get(key) for key in group) for group in METADATA_GROUPS) * 2,
        10,
    )
    if metadata_points:
        score += metadata_points
        reasons.append("helpful place details")

    if business_id in visited_ids and "old-favorite" not in normalized_vibes:
        score -= 20
        reasons.append("visited before")

    return max(0, min(score, 100)), reasons


def filter_candidates(
    businesses: list[dict[str, Any]],
    history: list[dict[str, Any]],
    vibes: list[str],
) -> list[dict[str, Any]]:
    normalized_vibes = normalize_vibes(vibes)
    recent_ids = (
        set()
        if "old-favorite" in normalized_vibes
        else _recently_visited_ids(history)
    )
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


def normalize_vibes(vibes: list[str]) -> set[str]:
    normalized = {vibe.lower() for vibe in vibes}
    if HISTORY_VIBES <= normalized:
        normalized -= HISTORY_VIBES
    return normalized


def history_entry(
    business: dict[str, Any],
    rarity: str,
    pulled_at: datetime | None = None,
) -> dict[str, Any]:
    coordinates = business.get("coordinates") or {}
    price_level = business.get("price_level")
    return {
        "id": business.get("id", ""),
        "name": business.get("name", "Unknown restaurant"),
        "cuisine": business.get("cuisine", "Restaurant"),
        "rarity": rarity,
        "match_score": business.get("match_score", 0),
        "match_reasons": business.get("match_reasons", []),
        "visited": False,
        "rating_given": None,
        "date": (pulled_at or datetime.now(timezone.utc)).date().isoformat(),
        "notes": "",
        "price": "$" * int(price_level) if price_level else "",
        "distance_miles": round(float(business.get("distance") or 0) / 1609.344, 1),
        "url": business.get("url", ""),
        "source": "OpenStreetMap",
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


def _matches_vibe(
    vibe: str,
    business: dict[str, Any],
    cuisines: set[str],
    tags: dict[str, str],
    known: bool,
    visited: bool,
) -> bool:
    distance_miles = float(business.get("distance") or 0) / 1609.344
    if vibe == "quick":
        return (
            business.get("amenity") == "fast_food"
            or tags.get("takeaway") == "yes"
            or distance_miles <= 1
        )
    if vibe == "sit-down":
        return business.get("amenity") == "restaurant"
    if vibe == "something-new":
        return not known
    if vibe == "old-favorite":
        return visited
    if vibe == "spicy":
        return bool(cuisines & SPICY_CUISINES)
    if vibe == "light":
        return bool(cuisines & LIGHT_CUISINES)
    if vibe == "filling":
        return bool(cuisines & FILLING_CUISINES)
    return False

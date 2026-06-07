from __future__ import annotations

import random
import re
from collections.abc import Iterable
from datetime import datetime, timezone
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
REMOVED_VIBES = {"something-new", "old-favorite"}

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

DISH_ALIASES = {
    "banh_mi": {"banh mi", "bánh mì"},
    "barbecue": {"barbecue", "bbq"},
    "bibimbap": {"bibimbap"},
    "biryani": {"biryani"},
    "boat_noodles": {"boat noodle", "boat noodles"},
    "burger": {"burger", "burgers"},
    "burrito": {"burrito", "burritos"},
    "chinese_noodles": {"chinese noodle", "chinese noodles", "noodle", "noodles"},
    "dim_sum": {"dim sum", "dimsum"},
    "dosa": {"dosa"},
    "falafel": {"falafel"},
    "gelato": {"gelato"},
    "gyro": {"gyro", "gyros"},
    "hotpot": {"hot pot", "hotpot"},
    "hummus": {"hummus"},
    "indian_curry": {"curry", "indian curry"},
    "katsu": {"katsu", "tonkatsu"},
    "kebab": {"kebab", "kebap"},
    "korean_barbecue": {"korean barbecue", "korean bbq", "korean_barbecue"},
    "korean_fried_chicken": {"korean fried chicken"},
    "pad_thai": {"pad thai", "pad_thai"},
    "panini": {"panini", "panino"},
    "pasta": {"pasta"},
    "pho": {"pho", "phở"},
    "pizza": {"pizza"},
    "quesadilla": {"quesadilla", "quesadillas"},
    "ramen": {"ramen"},
    "spring_rolls": {"spring roll", "spring rolls"},
    "steak": {"steak", "steakhouse"},
    "sushi": {"sushi"},
    "szechuan": {"sichuan", "szechuan"},
    "taco": {"taco", "tacos"},
    "tamale": {"tamale", "tamales"},
    "tandoori": {"tandoori"},
    "thai_curry": {"thai curry"},
    "tom_yum": {"tom yum", "tom_yum"},
    "tteokbokki": {"tteokbokki", "topokki"},
    "udon": {"udon"},
    "vermicelli": {"vermicelli"},
    "wings": {"chicken wings", "wings"},
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
    dishes: list[str] | None = None,
    prices: list[int] | None = None,
    vibes: list[str] | None = None,
    rng: random.Random | None = None,
) -> tuple[dict[str, Any] | None, str | None, int]:
    randomizer = rng or random.Random()
    candidates = filter_candidates(list(businesses), history, vibes or [])
    fallback_note = ""
    dish_candidates = [
        business
        for business in candidates
        if matches_requested_dish(business, dishes or [])
    ]
    if dish_candidates:
        candidates = dish_candidates
    else:
        cuisine_candidates = [
            business
            for business in candidates
            if matches_requested_cuisine(business, cuisines or [])
        ]
        if cuisine_candidates:
            candidates = cuisine_candidates
            if dishes:
                fallback_note = (
                    "No exact dish tags were found nearby, so cuisine matches were used."
                )
        elif dishes or cuisines:
            fallback_note = (
                "No requested dish or cuisine tags were found nearby, so other "
                "preferences were used."
            )
    buckets = {rarity: [] for rarity in RARITY_ORDER}
    for business in candidates:
        score, reasons = match_score(
            business,
            cuisines or [],
            dishes or [],
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
    if fallback_note:
        selected = {**selected, "fallback_note": fallback_note}
    new_pity = 0 if selected_tier == "SSR" else pity_counter + 1
    return selected, selected_tier, new_pity


def match_score(
    business: dict[str, Any],
    cuisines: list[str],
    dishes: list[str],
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

    requested_cuisines = {cuisine.lower() for cuisine in cuisines}
    if any(
        business_cuisines & CUISINE_ALIASES.get(cuisine, {cuisine})
        for cuisine in requested_cuisines
    ):
        score += 30
        reasons.append("cuisine match")

    searchable_text = _normalize_search_text(" ".join(
        [
            str(business.get("name", "")),
            *business_cuisines,
            *tags.values(),
        ]
    ))
    matched_dishes = [
        dish
        for dish in {dish.lower() for dish in dishes}
        if any(
            _normalize_search_text(alias) in searchable_text
            for alias in DISH_ALIASES.get(dish, {dish})
        )
    ]
    if matched_dishes:
        score += 25
        labels = ", ".join(dish.replace("_", " ") for dish in sorted(matched_dishes))
        reasons.append(f"specific dish match: {labels}")

    matched_vibes = [
        vibe
        for vibe in normalized_vibes
        if _matches_vibe(
            vibe,
            business,
            business_cuisines,
            tags,
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

    return max(0, min(score, 100)), reasons


def filter_candidates(
    businesses: list[dict[str, Any]],
    history: list[dict[str, Any]],
    vibes: list[str],
) -> list[dict[str, Any]]:
    pulled_ids = {str(item.get("id")) for item in history}

    return [
        business
        for business in businesses
        if str(business.get("id")) not in pulled_ids
    ]


def normalize_vibes(vibes: list[str]) -> set[str]:
    return {vibe.lower() for vibe in vibes} - REMOVED_VIBES


def matches_requested_cuisine(
    business: dict[str, Any],
    cuisines: list[str],
) -> bool:
    if not cuisines:
        return False
    business_cuisines = {
        str(cuisine).lower().replace(" ", "_")
        for cuisine in business.get("cuisines") or []
    }
    return any(
        business_cuisines & CUISINE_ALIASES.get(cuisine.lower(), {cuisine.lower()})
        for cuisine in cuisines
    )


def matches_requested_dish(
    business: dict[str, Any],
    dishes: list[str],
) -> bool:
    if not dishes:
        return False
    tags = {
        str(key): str(value).lower()
        for key, value in (business.get("tags") or {}).items()
    }
    searchable_text = _normalize_search_text(
        " ".join(
            [
                str(business.get("name", "")),
                *(str(cuisine) for cuisine in business.get("cuisines") or []),
                *tags.values(),
            ]
        )
    )
    return any(
        _normalize_search_text(alias) in searchable_text
        for dish in {dish.lower() for dish in dishes}
        for alias in DISH_ALIASES.get(dish, {dish})
    )


def _normalize_search_text(value: str) -> str:
    words = re.sub(r"[^\w]+", " ", value.lower().replace("_", " ")).strip()
    return f" {words} "


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


def _matches_vibe(
    vibe: str,
    business: dict[str, Any],
    cuisines: set[str],
    tags: dict[str, str],
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
    if vibe == "spicy":
        return bool(cuisines & SPICY_CUISINES)
    if vibe == "light":
        return bool(cuisines & LIGHT_CUISINES)
    if vibe == "filling":
        return bool(cuisines & FILLING_CUISINES)
    return False

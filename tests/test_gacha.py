from __future__ import annotations

import random

from foodgacha.gacha import (
    choose_restaurant,
    filter_candidates,
    match_score,
    rarity_for,
)


def business(
    identifier: str,
    cuisine: str = "",
    distance: float = 5000,
    amenity: str = "restaurant",
    tags: dict[str, str] | None = None,
) -> dict[str, object]:
    return {
        "id": identifier,
        "name": identifier,
        "cuisines": [cuisine] if cuisine else [],
        "cuisine": cuisine.title() if cuisine else "Restaurant",
        "amenity": amenity,
        "tags": tags or {},
        "distance": distance,
        "price_level": None,
    }


def test_rarity_rules() -> None:
    assert rarity_for(85) == "SSR"
    assert rarity_for(70) == "SR"
    assert rarity_for(50) == "R"
    assert rarity_for(30) == "U"
    assert rarity_for(29) == "C"


def test_match_score_rewards_preferences_distance_and_metadata() -> None:
    restaurant = business(
        "great-match",
        cuisine="ramen",
        distance=1000,
        tags={
            "opening_hours": "Mo-Su 11:00-22:00",
            "website": "https://example.com",
            "phone": "555-0100",
            "takeaway": "yes",
            "delivery": "yes",
        },
    )

    score, reasons = match_score(
        restaurant,
        cuisines=["japanese"],
        dishes=[],
        prices=[],
        vibes=["sit-down", "filling"],
        history=[],
    )

    assert score == 85
    assert "cuisine match" in reasons
    assert "within two miles" in reasons


def test_match_score_rewards_specific_dish_from_restaurant_name() -> None:
    restaurant = business("Katsu Cafe", cuisine="japanese", distance=5000)

    score, reasons = match_score(
        restaurant,
        cuisines=["japanese"],
        dishes=["katsu"],
        prices=[],
        vibes=[],
        history=[],
    )

    assert score == 55
    assert "specific dish match: katsu" in reasons


def test_pity_forces_ssr_when_available() -> None:
    selected, rarity, pity = choose_restaurant(
        [
            business(
                "ssr",
                cuisine="ramen",
                distance=1000,
                tags={
                    "opening_hours": "yes",
                    "website": "yes",
                    "phone": "yes",
                    "takeaway": "yes",
                    "delivery": "yes",
                },
            ),
            business("common"),
        ],
        pity_counter=9,
        history=[],
        cuisines=["japanese"],
        vibes=["sit-down", "filling"],
        rng=random.Random(1),
    )
    assert selected is not None
    assert selected["id"] == "ssr"
    assert rarity == "SSR"
    assert pity == 0


def test_pity_remains_active_without_ssr_candidate() -> None:
    selected, rarity, pity = choose_restaurant(
        [business("common")],
        pity_counter=9,
        history=[],
        rng=random.Random(1),
    )
    assert selected is not None
    assert rarity == "C"
    assert pity == 10


def test_requested_dishes_narrow_candidates_when_matches_exist() -> None:
    selected, _, _ = choose_restaurant(
        [
            business("Sushi Place", cuisine="sushi"),
            business("Taco Place", cuisine="taco"),
        ],
        pity_counter=0,
        history=[],
        cuisines=["japanese", "mexican"],
        dishes=["sushi"],
        rng=random.Random(1),
    )

    assert selected is not None
    assert selected["id"] == "Sushi Place"


def test_requested_dishes_fall_back_when_osm_has_no_match() -> None:
    selected, _, _ = choose_restaurant(
        [business("Japanese Place", cuisine="japanese")],
        pity_counter=0,
        history=[],
        cuisines=["japanese"],
        dishes=["katsu"],
        rng=random.Random(1),
    )

    assert selected is not None
    assert selected["id"] == "Japanese Place"
    assert "cuisine matches were used" in str(selected["fallback_note"])


def test_requested_cuisines_narrow_candidates_when_matches_exist() -> None:
    selected, _, _ = choose_restaurant(
        [
            business("Ramen Place", cuisine="ramen"),
            business("Pizza Place", cuisine="pizza"),
        ],
        pity_counter=0,
        history=[],
        cuisines=["japanese"],
        rng=random.Random(1),
    )

    assert selected is not None
    assert selected["id"] == "Ramen Place"


def test_all_previously_pulled_restaurants_are_excluded() -> None:
    restaurants = [business("visited"), business("unvisited-pull"), business("new")]
    history = [
        {
            "id": "visited",
            "visited": True,
            "date": "2020-01-01",
        },
        {
            "id": "unvisited-pull",
            "visited": False,
            "date": "2020-01-01",
        },
    ]

    candidates = filter_candidates(restaurants, history, [])

    assert [item["id"] for item in candidates] == ["new"]


def test_removed_history_vibes_are_ignored_for_legacy_profiles() -> None:
    restaurants = [business("visited"), business("new")]
    history = [{"id": "visited", "visited": True, "date": "2020-01-01"}]

    candidates = filter_candidates(
        restaurants,
        history,
        ["something-new", "old-favorite"],
    )

    assert [item["id"] for item in candidates] == ["new"]

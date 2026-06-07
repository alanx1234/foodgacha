from __future__ import annotations

import random
from datetime import date

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
        prices=[],
        vibes=["sit-down", "filling"],
        history=[],
    )

    assert score == 95
    assert "cuisine match" in reasons
    assert "within two miles" in reasons


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


def test_history_vibes_filter_candidates() -> None:
    restaurants = [business("known"), business("new")]
    history = [{"id": "known", "visited": True, "date": "2020-01-01"}]
    assert [
        item["id"]
        for item in filter_candidates(restaurants, history, ["something-new"])
    ] == ["new"]
    assert [
        item["id"]
        for item in filter_candidates(restaurants, history, ["old-favorite"])
    ] == ["known"]


def test_conflicting_history_vibes_cancel_each_other() -> None:
    restaurants = [business("known"), business("new")]
    history = [{"id": "known", "visited": True, "date": "2020-01-01"}]

    candidates = filter_candidates(
        restaurants,
        history,
        ["something-new", "old-favorite"],
    )

    assert [item["id"] for item in candidates] == ["known", "new"]


def test_old_favorite_can_include_recently_visited_places() -> None:
    restaurants = [business("favorite")]
    history = [
        {
            "id": "favorite",
            "visited": True,
            "date": date.today().isoformat(),
        }
    ]

    assert filter_candidates(restaurants, history, ["old-favorite"]) == restaurants


def test_recently_visited_restaurant_is_excluded() -> None:
    restaurants = [business("recent")]
    history = [
        {
            "id": "recent",
            "visited": True,
            "date": date.today().isoformat(),
        }
    ]
    assert filter_candidates(restaurants, history, []) == []

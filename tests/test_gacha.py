from __future__ import annotations

import random
from datetime import date

from foodgacha.gacha import choose_restaurant, filter_candidates, rarity_for


def business(
    identifier: str,
    rating: float,
    reviews: int,
    alias: str = "restaurants",
) -> dict[str, object]:
    return {
        "id": identifier,
        "name": identifier,
        "rating": rating,
        "review_count": reviews,
        "categories": [{"alias": alias, "title": alias.title()}],
        "distance": 1000,
    }


def test_rarity_rules() -> None:
    assert rarity_for(business("excellent", 4.5, 200)) == "SSR"
    assert rarity_for(business("strong", 4.2, 150)) == "SR"
    assert rarity_for(business("popular", 3.4, 100)) == "R"
    assert rarity_for(business("high-rated", 4.0, 5)) == "R"
    assert rarity_for(business("uncommon", 3.5, 25)) == "U"
    assert rarity_for(business("common", 3.4, 24)) == "C"


def test_pity_forces_ssr_when_available() -> None:
    selected, rarity, pity = choose_restaurant(
        [
            business("ssr", 4.8, 500),
            business("common", 3.0, 10),
        ],
        pity_counter=9,
        history=[],
        rng=random.Random(1),
    )
    assert selected is not None
    assert selected["id"] == "ssr"
    assert rarity == "SSR"
    assert pity == 0


def test_pity_remains_active_without_ssr_candidate() -> None:
    selected, rarity, pity = choose_restaurant(
        [business("common", 3.0, 10)],
        pity_counter=9,
        history=[],
        rng=random.Random(1),
    )
    assert selected is not None
    assert rarity == "C"
    assert pity == 10


def test_history_vibes_filter_candidates() -> None:
    restaurants = [
        business("known", 4.0, 10),
        business("new", 4.0, 10),
    ]
    history = [
        {
            "id": "known",
            "visited": True,
            "date": "2020-01-01",
        }
    ]
    assert [item["id"] for item in filter_candidates(
        restaurants, history, ["something-new"]
    )] == ["new"]
    assert [item["id"] for item in filter_candidates(
        restaurants, history, ["old-favorite"]
    )] == ["known"]


def test_recently_visited_restaurant_is_excluded() -> None:
    restaurants = [business("recent", 4.0, 10)]
    history = [
        {
            "id": "recent",
            "visited": True,
            "date": date.today().isoformat(),
        }
    ]
    assert filter_candidates(restaurants, history, []) == []

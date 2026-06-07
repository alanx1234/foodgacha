from __future__ import annotations

from foodgacha.swipe import dish_cards_for


def test_dish_cards_only_use_selected_cuisines() -> None:
    cards = dish_cards_for(["japanese", "mexican"])
    values = [card.value for card in cards]

    assert values == [
        "sushi",
        "ramen",
        "katsu",
        "udon",
        "burrito",
        "taco",
        "quesadilla",
        "tamale",
    ]


def test_no_cuisines_produces_no_dish_cards() -> None:
    assert dish_cards_for([]) == []

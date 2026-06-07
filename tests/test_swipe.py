from __future__ import annotations

import readchar

from foodgacha import swipe
from foodgacha.swipe import Card, RoundResult, _run_round, dish_cards_for


class FakeConsole:
    def clear(self) -> None:
        pass

    def print(self, *args, **kwargs) -> None:
        pass


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


def test_enter_finishes_round_and_keeps_prior_selections(monkeypatch) -> None:
    keys = iter(["y", readchar.key.ENTER])
    monkeypatch.setattr(readchar, "readkey", lambda: next(keys))

    result = _run_round(
        FakeConsole(),
        "Test round",
        [Card("First", "first"), Card("Second", "second")],
    )

    assert result.selected == ["first"]
    assert result.finished is True


def test_collect_preferences_stops_after_enter(monkeypatch) -> None:
    calls = 0

    def fake_round(console, title, cards):
        nonlocal calls
        calls += 1
        return RoundResult(selected=["japanese"], finished=True)

    monkeypatch.setattr(swipe, "_run_round", fake_round)

    preferences = swipe.collect_preferences(FakeConsole())

    assert calls == 1
    assert preferences == {
        "cuisines": ["japanese"],
        "price": [],
        "vibes": [],
        "dishes": [],
    }

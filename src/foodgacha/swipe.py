from __future__ import annotations

from dataclasses import dataclass

import readchar
from rich.align import Align
from rich.console import Console
from rich.panel import Panel


@dataclass(frozen=True)
class Card:
    label: str
    value: str | int
    detail: str = ""


CUISINE_CARDS = [
    Card("Japanese", "japanese"),
    Card("Korean", "korean"),
    Card("Mexican", "mexican"),
    Card("Italian", "italian"),
    Card("American", "american"),
    Card("Thai", "thai"),
    Card("Chinese", "chinese"),
    Card("Indian", "indian"),
    Card("Vietnamese", "vietnamese"),
    Card("Mediterranean", "mediterranean"),
]

PRICE_CARDS = [
    Card("Cheap", 1, "$"),
    Card("Mid", 2, "$$"),
    Card("Fancy", 3, "$$$"),
    Card("Splurge", 4, "$$$$"),
]

VIBE_CARDS = [
    Card("Quick Bite", "quick", "nearby options get a boost"),
    Card("Sit-down", "sit-down", "restaurant categories get a boost"),
    Card("Spicy", "spicy", "spicy cuisines get a boost"),
    Card("Light", "light", "lighter cuisines get a boost"),
    Card("Filling", "filling", "hearty cuisines get a boost"),
]


def collect_preferences(console: Console) -> dict[str, list[str] | list[int]]:
    console.print(
        "[bold]Swipe with left/right arrows. You can also press n/y.[/bold]\n"
    )
    cuisines = _run_round(console, "Round 1: cuisines", CUISINE_CARDS)
    prices = _run_round(console, "Round 2: prices", PRICE_CARDS)
    vibes = _run_round(console, "Round 3: vibes", VIBE_CARDS)
    return {
        "cuisines": [str(value) for value in cuisines],
        "price": [int(value) for value in prices],
        "vibes": [str(value) for value in vibes],
    }


def _run_round(
    console: Console,
    title: str,
    cards: list[Card],
) -> list[str | int]:
    selected: list[str | int] = []
    for index, card in enumerate(cards, start=1):
        while True:
            console.clear()
            content = f"[bold]{card.label}[/bold]"
            if card.detail:
                content += f"\n[dim]{card.detail}[/dim]"
            content += "\n\n[dim]left/n: skip    right/y: keep[/dim]"
            console.print(
                Panel(
                    Align.center(content, vertical="middle"),
                    title=title,
                    subtitle=f"{index} / {len(cards)}",
                    height=9,
                    width=48,
                    border_style="magenta",
                )
            )
            key = readchar.readkey()
            if key in {readchar.key.RIGHT, "y", "Y"}:
                selected.append(card.value)
                break
            if key in {readchar.key.LEFT, "n", "N"}:
                break
            if key in {readchar.key.CTRL_C, "q", "Q"}:
                raise KeyboardInterrupt
    return selected

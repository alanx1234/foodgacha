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


@dataclass(frozen=True)
class RoundResult:
    selected: list[str | int]
    finished: bool = False


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

DISH_CARDS_BY_CUISINE = {
    "japanese": [
        Card("Sushi", "sushi"),
        Card("Ramen", "ramen"),
        Card("Katsu", "katsu"),
        Card("Udon", "udon"),
    ],
    "korean": [
        Card("Korean BBQ", "korean_barbecue"),
        Card("Bibimbap", "bibimbap"),
        Card("Korean Fried Chicken", "korean_fried_chicken"),
        Card("Tteokbokki", "tteokbokki"),
    ],
    "mexican": [
        Card("Burritos", "burrito"),
        Card("Tacos", "taco"),
        Card("Quesadillas", "quesadilla"),
        Card("Tamales", "tamale"),
    ],
    "italian": [
        Card("Pizza", "pizza"),
        Card("Pasta", "pasta"),
        Card("Panini", "panini"),
        Card("Gelato", "gelato"),
    ],
    "american": [
        Card("Burgers", "burger"),
        Card("Barbecue", "barbecue"),
        Card("Steak", "steak"),
        Card("Wings", "wings"),
    ],
    "thai": [
        Card("Pad Thai", "pad_thai"),
        Card("Thai Curry", "thai_curry"),
        Card("Boat Noodles", "boat_noodles"),
        Card("Tom Yum", "tom_yum"),
    ],
    "chinese": [
        Card("Dim Sum", "dim_sum"),
        Card("Hot Pot", "hotpot"),
        Card("Szechuan", "szechuan"),
        Card("Noodles", "chinese_noodles"),
    ],
    "indian": [
        Card("Curry", "indian_curry"),
        Card("Biryani", "biryani"),
        Card("Tandoori", "tandoori"),
        Card("Dosa", "dosa"),
    ],
    "vietnamese": [
        Card("Pho", "pho"),
        Card("Banh Mi", "banh_mi"),
        Card("Vermicelli", "vermicelli"),
        Card("Spring Rolls", "spring_rolls"),
    ],
    "mediterranean": [
        Card("Kebab", "kebab"),
        Card("Gyro", "gyro"),
        Card("Falafel", "falafel"),
        Card("Hummus", "hummus"),
    ],
}


def collect_preferences(console: Console) -> dict[str, list[str] | list[int]]:
    console.print(
        "[bold]Swipe with left/right arrows or n/y.[/bold]\n"
        "[dim]Press Enter anytime to save your choices and finish early.[/dim]\n"
    )
    preferences: dict[str, list[str] | list[int]] = {
        "cuisines": [],
        "price": [],
        "vibes": [],
        "dishes": [],
    }

    cuisines = _run_round(console, "Round 1: cuisines", CUISINE_CARDS)
    preferences["cuisines"] = [str(value) for value in cuisines.selected]
    if cuisines.finished:
        return preferences

    prices = _run_round(console, "Round 2: prices", PRICE_CARDS)
    preferences["price"] = [int(value) for value in prices.selected]
    if prices.finished:
        return preferences

    vibes = _run_round(console, "Round 3: vibes", VIBE_CARDS)
    preferences["vibes"] = [str(value) for value in vibes.selected]
    if vibes.finished:
        return preferences

    dish_cards = dish_cards_for([str(value) for value in cuisines.selected])
    dishes = _run_round(console, "Round 4: specific dishes", dish_cards)
    preferences["dishes"] = [str(value) for value in dishes.selected]
    return preferences


def dish_cards_for(cuisines: list[str]) -> list[Card]:
    cards: list[Card] = []
    seen: set[str | int] = set()
    for cuisine in cuisines:
        for card in DISH_CARDS_BY_CUISINE.get(cuisine, []):
            if card.value not in seen:
                cards.append(card)
                seen.add(card.value)
    return cards


def _run_round(
    console: Console,
    title: str,
    cards: list[Card],
) -> RoundResult:
    selected: list[str | int] = []
    for index, card in enumerate(cards, start=1):
        while True:
            console.clear()
            content = f"[bold]{card.label}[/bold]"
            if card.detail:
                content += f"\n[dim]{card.detail}[/dim]"
            content += (
                "\n\n[dim]left/n: skip    right/y: keep[/dim]"
                "\n[bold cyan]Enter: save and finish[/bold cyan]"
            )
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
            if key in {readchar.key.ENTER, "\n", "\r"}:
                return RoundResult(selected=selected, finished=True)
            if key in {readchar.key.CTRL_C, "q", "Q"}:
                raise KeyboardInterrupt
    return RoundResult(selected=selected)

from __future__ import annotations

from rich.console import Console

from foodgacha.main import _pull_result_panel


def test_pull_panel_contains_key_result_details() -> None:
    console = Console(record=True, width=100)
    panel = _pull_result_panel(
        {
            "name": "Ramen House",
            "cuisine": "Ramen",
            "price": "$$",
            "distance_miles": 0.8,
            "match_score": 85,
            "match_reasons": ["cuisine match", "specific dish match: ramen"],
            "url": "https://www.openstreetmap.org/node/1",
        },
        rarity="SSR",
        display_location="San Diego, California",
        pity=0,
    )

    console.print(panel)
    output = console.export_text()

    assert "SSR PULL" in output
    assert "Ramen House" in output
    assert "85/100" in output
    assert "#################" in output
    assert "specific dish match: ramen" in output
    assert "OpenStreetMap contributors" in output

from __future__ import annotations

import time
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from typing import Annotated, Any

import typer
from rich.console import Console
from rich.table import Table

from foodgacha import __version__
from foodgacha.gacha import (
    PITY_LIMIT,
    RARITY_LABELS,
    choose_restaurant,
    history_entry,
)
from foodgacha.openstreetmap import (
    OpenStreetMapError,
    geocode_location,
    search_restaurants,
)
from foodgacha.storage import load_data, save_data
from foodgacha.swipe import collect_preferences

app = typer.Typer(
    help="Choose where to eat with preferences, rarity tiers, and a pity counter.",
    no_args_is_help=True,
)
console = Console()


def version_callback(value: bool) -> None:
    if value:
        console.print(f"foodgacha {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool | None,
        typer.Option("--version", callback=version_callback, is_eager=True),
    ] = None,
) -> None:
    """A restaurant recommendation gacha game."""


@app.command()
def swipe() -> None:
    """Set saved cuisine, price, and vibe preferences."""
    data = load_data()
    _ensure_location(data)
    try:
        preferences = collect_preferences(console)
    except (KeyboardInterrupt, EOFError):
        console.print("\n[yellow]Swipe cancelled; existing preferences were kept.[/yellow]")
        raise typer.Exit(1)

    data["preferences"] = preferences
    save_data(data)
    console.print("\n[bold magenta]Your vibe[/bold magenta]")
    console.print(f"cuisines: {_format_list(preferences['cuisines'])}")
    console.print(f"price: {_format_prices(preferences['price'])}")
    console.print(f"vibes: {_format_list(preferences['vibes'])}")
    console.print("\n[green]Preferences saved.[/green] Run [bold]foodgacha pull[/bold].")


@app.command()
def pull(
    location: Annotated[
        str | None, typer.Option(help="Use a different location for this pull.")
    ] = None,
    cuisine: Annotated[
        list[str] | None,
        typer.Option(help="Override saved cuisines. Repeat for more than one."),
    ] = None,
    price: Annotated[
        list[int] | None,
        typer.Option(min=1, max=4, help="Override saved prices. Repeat for more than one."),
    ] = None,
) -> None:
    """Pull a nearby restaurant recommendation from OpenStreetMap."""
    data = load_data()
    if not location:
        _ensure_location(data)
    preferences = data.get("preferences", {})
    cuisines = cuisine if cuisine else list(preferences.get("cuisines", []))
    prices = price if price else list(preferences.get("price", []))
    vibes = list(preferences.get("vibes", []))
    search_location = location or str(data["location"])

    console.print("[dim]Searching OpenStreetMap and rolling...[/dim]")
    try:
        latitude, longitude, display_location = _coordinates_for(
            data,
            search_location,
        )
        businesses = _restaurants_for(data, latitude, longitude)
    except OpenStreetMapError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1)

    selected, rarity, pity = choose_restaurant(
        businesses,
        int(data.get("pity_counter", 0)),
        list(data.get("history", [])),
        cuisines=cuisines,
        prices=prices,
        vibes=vibes,
    )
    if selected is None or rarity is None:
        console.print(
            "[yellow]No restaurants matched your vibe.[/yellow]\n"
            "Try [bold]foodgacha swipe[/bold] to loosen your preferences."
        )
        raise typer.Exit(1)

    stars = {"SSR": "*****", "SR": "****", "R": "***", "U": "**", "C": "*"}[
        rarity
    ]
    rarity_label = RARITY_LABELS[rarity]
    console.print(
        f"\n[bold magenta]{stars}  {rarity_label}  {stars}[/bold magenta]"
    )
    time.sleep(0.8)
    entry = history_entry(selected, rarity)
    console.print(f"\n[bold]{entry['name']}[/bold]")
    console.print(
        f"{entry['cuisine']}  |  {entry['price'] or 'price unknown'}  |  "
        f"{entry['distance_miles']:.1f} mi"
    )
    console.print(f"match score: {entry['match_score']} / 100")
    if entry["match_reasons"]:
        console.print(f"[dim]{', '.join(entry['match_reasons'])}[/dim]")
    if entry["url"]:
        console.print(f"[link={entry['url']}]{entry['url']}[/link]")
    console.print(f"[dim]Near {display_location} | © OpenStreetMap contributors[/dim]")
    console.print(f"\nPity counter: {pity} / {PITY_LIMIT}")

    data["pity_counter"] = pity
    data.setdefault("history", []).append(entry)
    save_data(data)


@app.command()
def visit(
    name_or_id: Annotated[
        str,
        typer.Argument(help="Restaurant name fragment or OpenStreetMap ID."),
    ],
    rating: Annotated[int, typer.Option(min=1, max=10)],
    notes: Annotated[str, typer.Option()] = "",
) -> None:
    """Mark a pulled restaurant as visited and give it a personal rating."""
    data = load_data()
    history = list(data.get("history", []))
    matches = _history_matches(history, name_or_id)
    if not matches:
        console.print(f"[red]No history entry matched {name_or_id!r}.[/red]")
        raise typer.Exit(1)

    entry = _choose_match(matches)
    entry["visited"] = True
    entry["rating_given"] = rating
    entry["notes"] = notes
    entry["date"] = date.today().isoformat()
    save_data(data)
    console.print(f"[green]Logged.[/green] {entry['name']} - {rating}/10")
    if notes:
        console.print(f'"{notes}"')


@app.command(name="history")
def show_history(
    limit: Annotated[int, typer.Option(min=1, help="Number of pulls to show.")] = 10,
) -> None:
    """Show recent restaurant pulls."""
    history = list(reversed(load_data().get("history", [])))[:limit]
    if not history:
        console.print("No pulls yet. Run [bold]foodgacha pull[/bold] first.")
        return

    table = Table(title="Recent pulls")
    for heading in ("Name", "Rarity", "Visited", "Rating", "Date"):
        table.add_column(heading)
    for entry in history:
        visited = bool(entry.get("visited"))
        style = None if visited else "dim"
        personal_rating = entry.get("rating_given")
        table.add_row(
            str(entry.get("name", "Unknown")),
            RARITY_LABELS.get(
                str(entry.get("rarity", "C")),
                str(entry.get("rarity", "Common")),
            ),
            "yes" if visited else "no",
            f"{personal_rating}/10" if personal_rating else "-",
            str(entry.get("date", "")),
            style=style,
        )
    console.print(table)


@app.command()
def stats() -> None:
    """Show pull, rarity, cuisine, rating, and visit statistics."""
    data = load_data()
    history = list(data.get("history", []))
    total = len(history)
    ssr_count = sum(entry.get("rarity") == "SSR" for entry in history)
    visited = [entry for entry in history if entry.get("visited")]
    ratings = [
        float(entry["rating_given"])
        for entry in visited
        if entry.get("rating_given") is not None
    ]
    cuisines = Counter(str(entry.get("cuisine", "unknown")) for entry in history)
    most_pulled = cuisines.most_common(1)[0] if cuisines else ("-", 0)
    pity = int(data.get("pity_counter", 0))

    console.print("[bold magenta]Your foodgacha stats[/bold magenta]\n")
    console.print(f"total pulls: {total}")
    console.print(
        f"SSR hits: {ssr_count} ({_percent(ssr_count, total)}, expected 5%)"
    )
    console.print(f"most pulled: {most_pulled[0]} ({most_pulled[1]} pulls)")
    console.print(
        f"avg personal rating: {sum(ratings) / len(ratings):.1f} / 10"
        if ratings
        else "avg personal rating: -"
    )
    console.print(f"visited rate: {_percent(len(visited), total)}")
    console.print(
        f"\npity counter: {pity} / {PITY_LIMIT} "
        f"(SSR guaranteed in {max(PITY_LIMIT - pity, 1)} eligible pulls)"
    )


@app.command()
def config(
    location: Annotated[str, typer.Option(prompt=True, help="Default search location.")],
) -> None:
    """Update the saved default location."""
    data = load_data()
    data["location"] = location.strip()
    save_data(data)
    console.print(f"[green]Default location saved:[/green] {data['location']}")


def _ensure_location(data: dict[str, Any]) -> None:
    if str(data.get("location", "")).strip():
        return
    console.print("[bold magenta]Welcome to foodgacha.[/bold magenta]")
    location = typer.prompt("What is your default location? (e.g. San Diego, CA)")
    if not location.strip():
        console.print("[red]A location is required.[/red]")
        raise typer.Exit(1)
    data["location"] = location.strip()
    save_data(data)


def _coordinates_for(
    data: dict[str, Any],
    location: str,
) -> tuple[float, float, str]:
    cache = data.setdefault("geocache", {})
    cache_key = location.strip().casefold()
    cached = cache.get(cache_key)
    if isinstance(cached, dict):
        try:
            return (
                float(cached["latitude"]),
                float(cached["longitude"]),
                str(cached["display_name"]),
            )
        except (KeyError, TypeError, ValueError):
            pass

    latitude, longitude, display_name = geocode_location(location)
    cache[cache_key] = {
        "latitude": latitude,
        "longitude": longitude,
        "display_name": display_name,
    }
    save_data(data)
    return latitude, longitude, display_name


def _restaurants_for(
    data: dict[str, Any],
    latitude: float,
    longitude: float,
) -> list[dict[str, Any]]:
    cache = data.setdefault("restaurant_cache", {})
    cache_key = f"{latitude:.4f},{longitude:.4f}"
    cached = cache.get(cache_key)
    if isinstance(cached, dict) and isinstance(cached.get("restaurants"), list):
        try:
            fetched_at = datetime.fromisoformat(str(cached["fetched_at"]))
            if datetime.now(timezone.utc) - fetched_at <= timedelta(hours=6):
                return list(cached["restaurants"])
        except (KeyError, TypeError, ValueError):
            pass

    restaurants = search_restaurants(latitude, longitude)
    cache[cache_key] = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "restaurants": restaurants,
    }
    save_data(data)
    return restaurants


def _history_matches(
    history: list[dict[str, Any]],
    query: str,
) -> list[dict[str, Any]]:
    normalized = query.casefold()
    exact_ids = [item for item in history if str(item.get("id", "")).casefold() == normalized]
    if exact_ids:
        return exact_ids
    return [
        item
        for item in reversed(history)
        if normalized in str(item.get("name", "")).casefold()
    ]


def _choose_match(matches: list[dict[str, Any]]) -> dict[str, Any]:
    if len(matches) == 1:
        return matches[0]
    console.print("Multiple restaurants matched:")
    for index, entry in enumerate(matches, start=1):
        console.print(f"{index}. {entry.get('name')} ({entry.get('date')})")
    choice = typer.prompt("Choose a number", type=int)
    if choice < 1 or choice > len(matches):
        console.print("[red]Invalid selection.[/red]")
        raise typer.Exit(1)
    return matches[choice - 1]


def _format_list(values: list[str] | list[int]) -> str:
    return ", ".join(str(value).replace("-", " ") for value in values) or "any"


def _format_prices(values: list[int]) -> str:
    return ", ".join("$" * value for value in values) or "any"


def _percent(part: int, whole: int) -> str:
    return f"{part / whole * 100:.1f}%" if whole else "0.0%"


if __name__ == "__main__":
    app()

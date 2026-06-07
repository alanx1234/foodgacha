from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

REMOVED_VIBES = {"something-new", "old-favorite"}


def data_path() -> Path:
    override = os.environ.get("FOODGACHA_DATA_FILE")
    if override:
        return Path(override).expanduser()
    return Path.home() / ".foodgacha" / "data.json"


def default_data() -> dict[str, Any]:
    return {
        "location": "",
        "geocache": {},
        "restaurant_cache": {},
        "pity_counter": 0,
        "preferences": {"cuisines": [], "dishes": [], "price": [], "vibes": []},
        "history": [],
    }


def load_data() -> dict[str, Any]:
    path = data_path()
    if not path.exists():
        return default_data()

    try:
        stored = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Could not read {path}: {exc}") from exc

    data = default_data()
    if isinstance(stored, dict):
        data.update(stored)
    if not isinstance(data.get("preferences"), dict):
        data["preferences"] = default_data()["preferences"]
    preferences = data["preferences"]
    if not isinstance(preferences.get("dishes"), list):
        preferences["dishes"] = []
    vibes = preferences.get("vibes", [])
    if isinstance(vibes, list):
        preferences["vibes"] = [
            vibe for vibe in vibes if str(vibe).lower() not in REMOVED_VIBES
        ]
    if not isinstance(data.get("history"), list):
        data["history"] = []
    if not isinstance(data.get("geocache"), dict):
        data["geocache"] = {}
    if not isinstance(data.get("restaurant_cache"), dict):
        data["restaurant_cache"] = {}
    return data


def save_data(data: dict[str, Any]) -> None:
    path = data_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)

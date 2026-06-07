from __future__ import annotations

from foodgacha.storage import load_data, save_data


def test_data_round_trip(tmp_path, monkeypatch) -> None:
    path = tmp_path / "profile" / "data.json"
    monkeypatch.setenv("FOODGACHA_DATA_FILE", str(path))
    data = load_data()
    data["location"] = "San Diego, CA"
    data["pity_counter"] = 4

    save_data(data)

    assert path.exists()
    assert load_data()["location"] == "San Diego, CA"
    assert load_data()["pity_counter"] == 4


def test_removed_vibes_are_migrated_out(tmp_path, monkeypatch) -> None:
    path = tmp_path / "data.json"
    monkeypatch.setenv("FOODGACHA_DATA_FILE", str(path))
    data = load_data()
    data["preferences"]["vibes"] = [
        "quick",
        "something-new",
        "old-favorite",
        "spicy",
    ]
    save_data(data)

    assert load_data()["preferences"]["vibes"] == ["quick", "spicy"]

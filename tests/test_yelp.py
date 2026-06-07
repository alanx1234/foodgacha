from __future__ import annotations

import httpx
import pytest

from foodgacha.yelp import YelpError, search_businesses


def test_missing_api_key_has_actionable_error(monkeypatch) -> None:
    monkeypatch.delenv("YELP_API_KEY", raising=False)
    with pytest.raises(YelpError, match="YELP_API_KEY"):
        search_businesses("San Diego, CA")


def test_search_builds_yelp_filters(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_get(url, *, headers, params, timeout):
        captured.update(
            {"url": url, "headers": headers, "params": params, "timeout": timeout}
        )
        return httpx.Response(
            200,
            json={"businesses": [{"id": "one"}]},
            request=httpx.Request("GET", url),
        )

    monkeypatch.setenv("YELP_API_KEY", "secret")
    monkeypatch.setattr(httpx, "get", fake_get)

    results = search_businesses(
        "San Diego, CA",
        cuisines=["japanese"],
        prices=[2, 1, 2],
    )

    assert results == [{"id": "one"}]
    assert captured["headers"] == {"Authorization": "Bearer secret"}
    assert captured["params"] == {
        "location": "San Diego, CA",
        "limit": 20,
        "sort_by": "best_match",
        "categories": "ramen,sushi,japanese",
        "price": "1,2",
    }

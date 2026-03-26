"""Tests for data-source connectors."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from property_damage_alerts.sources.base import BaseSource, Incident
from property_damage_alerts.sources.factory import build_sources
from property_damage_alerts.sources.fire import FireSource
from property_damage_alerts.sources.news import NewsSource
from property_damage_alerts.sources.police import PoliceSource
from property_damage_alerts.sources.rss import RSSSource

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_feed_entry(title="House Fire on Elm St", summary="A house caught fire.", link="http://x.com/1"):
    entry = MagicMock()
    entry.get = lambda key, default=None: {
        "title": title,
        "summary": summary,
        "link": link,
        "published": "Mon, 01 Jan 2024 12:00:00 +0000",
        "published_parsed": (2024, 1, 1, 12, 0, 0, 0, 1, 0),
    }.get(key, default)
    return entry


def _make_feedparser_result(entries=None):
    result = MagicMock()
    result.get = lambda key, default=None: {
        "entries": entries or [],
        "bozo": False,
    }.get(key, default)
    return result


# ---------------------------------------------------------------------------
# BaseSource
# ---------------------------------------------------------------------------

class ConcreteSource(BaseSource):
    """Minimal concrete implementation for testing the abstract base."""

    def fetch(self) -> list[Incident]:
        return []


class FailingSource(BaseSource):
    """Source that raises an exception on fetch."""

    def fetch(self) -> list[Incident]:
        raise RuntimeError("network error")


def test_base_source_safe_fetch_returns_empty_on_error():
    src = FailingSource(name="bad", config={})
    result = src.safe_fetch()
    assert result == []


def test_incident_as_dict():
    inc = Incident(
        source_name="Test",
        title="Flood at 123 Main St",
        summary="Heavy flooding reported.",
        url="http://example.com",
        published_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )
    d = inc.as_dict()
    assert d["source_name"] == "Test"
    assert d["title"] == "Flood at 123 Main St"
    assert "published_at" in d


# ---------------------------------------------------------------------------
# RSSSource
# ---------------------------------------------------------------------------

def test_rss_source_fetch_parses_entries():
    entry = _make_feed_entry()
    feed_result = _make_feedparser_result(entries=[entry])

    with patch("feedparser.parse", return_value=feed_result):
        src = RSSSource(name="Test RSS", config={"urls": ["http://example.com/feed"]})
        incidents = src.fetch()

    assert len(incidents) == 1
    assert incidents[0].title == "House Fire on Elm St"
    assert incidents[0].source_name == "Test RSS"


def test_rss_source_fetch_multiple_urls():
    entry = _make_feed_entry()
    feed_result = _make_feedparser_result(entries=[entry])

    with patch("feedparser.parse", return_value=feed_result):
        src = RSSSource(
            name="Multi",
            config={"urls": ["http://a.com/feed", "http://b.com/feed"]},
        )
        incidents = src.fetch()

    assert len(incidents) == 2


def test_rss_source_empty_feed_returns_no_incidents():
    feed_result = _make_feedparser_result(entries=[])
    with patch("feedparser.parse", return_value=feed_result):
        src = RSSSource(name="Empty", config={"urls": ["http://example.com/feed"]})
        incidents = src.fetch()
    assert incidents == []


# ---------------------------------------------------------------------------
# Source subclasses
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("source_cls", [PoliceSource, FireSource, NewsSource])
def test_source_subclasses_are_rss_sources(source_cls):
    src = source_cls(name="test", config={"urls": []})
    assert isinstance(src, RSSSource)


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def test_build_sources_returns_correct_types():
    cfg = [
        {"name": "Police", "type": "police", "enabled": True, "urls": []},
        {"name": "Fire", "type": "fire", "enabled": True, "urls": []},
        {"name": "News", "type": "news", "enabled": True, "urls": []},
    ]
    sources = build_sources(cfg)
    assert len(sources) == 3
    assert isinstance(sources[0], PoliceSource)
    assert isinstance(sources[1], FireSource)
    assert isinstance(sources[2], NewsSource)


def test_build_sources_skips_disabled():
    cfg = [
        {"name": "Off", "type": "rss", "enabled": False, "urls": []},
        {"name": "On", "type": "rss", "enabled": True, "urls": []},
    ]
    sources = build_sources(cfg)
    assert len(sources) == 1
    assert sources[0].name == "On"


def test_build_sources_skips_unknown_type():
    cfg = [{"name": "X", "type": "ftp_scraper", "enabled": True, "urls": []}]
    sources = build_sources(cfg)
    assert sources == []

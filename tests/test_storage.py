"""Tests for the SQLite storage layer."""

from __future__ import annotations

from datetime import datetime

import pytest

from property_damage_alerts.sources.base import Incident
from property_damage_alerts.storage.database import IncidentStore

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def store(tmp_path):
    """Provide a fresh in-memory-ish IncidentStore for each test."""
    db_file = tmp_path / "test_incidents.db"
    s = IncidentStore(db_file)
    yield s
    s.close()


def _incident(
    title: str = "Flood at 123 River Rd",
    url: str = "http://example.com/1",
    published_at: datetime = datetime(2024, 3, 10, 9, 0),
) -> Incident:
    return Incident(
        source_name="Test",
        title=title,
        summary="Flooding reported near the river.",
        url=url,
        published_at=published_at,
    )


# ---------------------------------------------------------------------------
# save / is_known
# ---------------------------------------------------------------------------

def test_save_and_is_known_by_url(store):
    inc = _incident()
    assert not store.is_known(inc)
    store.save(inc)
    assert store.is_known(inc)


def test_is_known_returns_false_for_new_url(store):
    inc1 = _incident(url="http://example.com/1")
    inc2 = _incident(url="http://example.com/2")
    store.save(inc1)
    assert not store.is_known(inc2)


def test_save_returns_integer_rowid(store):
    rowid = store.save(_incident())
    assert isinstance(rowid, int)
    assert rowid > 0


def test_is_known_without_url_uses_fallback(store):
    inc = _incident(url="")
    assert not store.is_known(inc)
    store.save(inc)
    assert store.is_known(inc)


def test_save_duplicate_url_raises(store):
    import sqlite3
    inc = _incident()
    store.save(inc)
    with pytest.raises(sqlite3.IntegrityError):
        store.save(inc)


# ---------------------------------------------------------------------------
# list_recent
# ---------------------------------------------------------------------------

def test_list_recent_returns_saved_incidents(store):
    store.save(_incident(title="Incident A", url="http://x.com/a"))
    store.save(_incident(title="Incident B", url="http://x.com/b"))
    rows = store.list_recent()
    assert len(rows) == 2


def test_list_recent_respects_limit(store):
    for i in range(10):
        store.save(_incident(title=f"Inc {i}", url=f"http://x.com/{i}"))
    rows = store.list_recent(limit=3)
    assert len(rows) == 3


def test_list_recent_newest_first(store):
    store.save(_incident(title="First", url="http://x.com/1"))
    store.save(_incident(title="Second", url="http://x.com/2"))
    rows = store.list_recent()
    # The second-saved item should appear first (newest).
    assert rows[0]["title"] == "Second"

"""SQLite storage layer for tracking processed incidents."""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path
from typing import Any

from ..sources.base import Incident

logger = logging.getLogger(__name__)

_CREATE_INCIDENTS_TABLE = """
CREATE TABLE IF NOT EXISTS incidents (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    source_name TEXT    NOT NULL,
    title       TEXT    NOT NULL,
    summary     TEXT    NOT NULL,
    url         TEXT    NOT NULL DEFAULT '',
    published_at TEXT   NOT NULL,
    created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""

_CREATE_URL_INDEX = """
CREATE UNIQUE INDEX IF NOT EXISTS idx_incidents_url ON incidents(url)
    WHERE url != '';
"""


class IncidentStore:
    """Persist incidents to a local SQLite database.

    Args:
        db_path: Path to the SQLite file.  Parent directories are created
                 automatically if they do not already exist.
    """

    def __init__(self, db_path: str | Path) -> None:
        self._path = Path(db_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._migrate()
        logger.info("IncidentStore initialised at %s", self._path)

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def is_known(self, incident: Incident) -> bool:
        """Return ``True`` if *incident* is already stored (deduplication).

        Deduplication is based on the incident URL when available; otherwise
        on the combination of source name, title, and publication timestamp.

        Args:
            incident: Incident to check.

        Returns:
            ``True`` when the incident already exists in the database.
        """
        if incident.url:
            cur = self._conn.execute(
                "SELECT 1 FROM incidents WHERE url = ?", (incident.url,)
            )
            return cur.fetchone() is not None

        cur = self._conn.execute(
            "SELECT 1 FROM incidents WHERE source_name = ? AND title = ? AND published_at = ?",
            (incident.source_name, incident.title, incident.published_at.isoformat()),
        )
        return cur.fetchone() is not None

    def save(self, incident: Incident) -> int:
        """Persist a new incident to the database.

        Args:
            incident: Incident to store.

        Returns:
            The ``rowid`` of the newly inserted row.

        Raises:
            sqlite3.IntegrityError: If the incident already exists
                                    (unique URL constraint violation).
        """
        cur = self._conn.execute(
            """
            INSERT INTO incidents (source_name, title, summary, url, published_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                incident.source_name,
                incident.title,
                incident.summary,
                incident.url,
                incident.published_at.isoformat(),
            ),
        )
        self._conn.commit()
        logger.debug("Saved incident id=%d: %s", cur.lastrowid, incident.title)
        return cur.lastrowid

    def list_recent(self, limit: int = 50) -> list[dict[str, Any]]:
        """Return the most recent *limit* incidents as plain dicts.

        Args:
            limit: Maximum number of rows to return.

        Returns:
            List of incident dicts ordered newest-first.
        """
        cur = self._conn.execute(
            "SELECT * FROM incidents ORDER BY created_at DESC, id DESC LIMIT ?", (limit,)
        )
        return [dict(row) for row in cur.fetchall()]

    def close(self) -> None:
        """Close the underlying database connection."""
        self._conn.close()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _migrate(self) -> None:
        self._conn.execute(_CREATE_INCIDENTS_TABLE)
        self._conn.execute(_CREATE_URL_INDEX)
        self._conn.commit()

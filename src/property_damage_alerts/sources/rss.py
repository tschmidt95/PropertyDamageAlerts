"""RSS feed source – shared implementation used by police, fire, and news connectors."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any

import feedparser

from .base import BaseSource, Incident

logger = logging.getLogger(__name__)


def _parse_date(entry: Any) -> datetime:
    """Best-effort extraction of a UTC datetime from a feedparser entry."""
    # feedparser provides a ``published_parsed`` time-tuple when available.
    if entry.get("published_parsed"):
        try:
            return datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
        except Exception:
            pass

    # Fall back to parsing the raw ``published`` string.
    if entry.get("published"):
        try:
            return (
                parsedate_to_datetime(entry.published)
                .astimezone(timezone.utc)
                .replace(tzinfo=None)
            )
        except Exception:
            pass

    return datetime.now(timezone.utc).replace(tzinfo=None)


class RSSSource(BaseSource):
    """A data source that polls one or more RSS / Atom feed URLs.

    Args:
        name:   Human-readable source name.
        config: Source config dict.  Expected keys:
                  - ``urls`` (list[str]): Feed URLs to poll.
    """

    def __init__(self, name: str, config: dict[str, Any]) -> None:
        super().__init__(name, config)
        self._urls: list[str] = config.get("urls", [])

    # ------------------------------------------------------------------
    # BaseSource interface
    # ------------------------------------------------------------------

    def fetch(self) -> list[Incident]:
        """Parse all configured RSS feeds and return their entries."""
        incidents: list[Incident] = []
        for url in self._urls:
            incidents.extend(self._fetch_url(url))
        return incidents

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _fetch_url(self, url: str) -> list[Incident]:
        self._logger.debug("Fetching RSS feed: %s", url)
        feed = feedparser.parse(url)

        if feed.get("bozo") and feed.get("bozo_exception"):
            self._logger.warning(
                "Malformed feed at %s: %s", url, feed["bozo_exception"]
            )

        incidents: list[Incident] = []
        for entry in feed.get("entries", []):
            summary = entry.get("summary", "") or entry.get("description", "")
            incidents.append(
                Incident(
                    source_name=self.name,
                    title=entry.get("title", "(no title)"),
                    summary=summary,
                    url=entry.get("link", ""),
                    published_at=_parse_date(entry),
                    raw=dict(entry),
                )
            )
        return incidents

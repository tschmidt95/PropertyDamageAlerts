"""Abstract base class for all data sources."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class Incident:
    """A single property-damage incident returned by a data source.

    Attributes:
        source_name:  Human-readable name of the originating source.
        title:        Short title / headline.
        summary:      Full body text or description of the incident.
        url:          Link to the original report (empty string if unavailable).
        published_at: Publication timestamp (UTC).  Defaults to *now*.
        raw:          Original raw data from the source, kept for debugging.
    """

    source_name: str
    title: str
    summary: str
    url: str = ""
    published_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )
    raw: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable representation of this incident."""
        return {
            "source_name": self.source_name,
            "title": self.title,
            "summary": self.summary,
            "url": self.url,
            "published_at": self.published_at.isoformat(),
        }


class BaseSource(ABC):
    """Abstract base class that all data-source connectors must implement.

    Subclasses should override :meth:`fetch` to retrieve raw incidents from
    their specific data source and return them as a list of :class:`Incident`
    objects.

    Args:
        name:   Human-readable source name (used in logs and alert messages).
        config: Source-level configuration dictionary from ``config.yaml``.
    """

    def __init__(self, name: str, config: dict[str, Any]) -> None:
        self.name = name
        self.config = config
        self._logger = logging.getLogger(f"{__name__}.{name}")

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    @abstractmethod
    def fetch(self) -> list[Incident]:
        """Fetch new incidents from the data source.

        Returns:
            A list of :class:`Incident` objects.  May return an empty list
            when there are no new items or the source is unreachable.
        """

    def safe_fetch(self) -> list[Incident]:
        """Call :meth:`fetch`, catching and logging any exceptions.

        Returns:
            Incidents returned by :meth:`fetch`, or an empty list on error.
        """
        try:
            incidents = self.fetch()
            self._logger.debug("Fetched %d incident(s) from '%s'.", len(incidents), self.name)
            return incidents
        except Exception:
            self._logger.exception("Error fetching from source '%s'.", self.name)
            return []

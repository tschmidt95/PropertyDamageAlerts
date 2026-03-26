"""Incident filter – decide which parsed incidents are property-damage events."""

from __future__ import annotations

import logging
from typing import Any

from .parser import ParsedIncident

logger = logging.getLogger(__name__)


class DamageFilter:
    """Filters :class:`~property_damage_alerts.processing.parser.ParsedIncident`
    objects using configurable keyword and location lists.

    Args:
        filter_config: The ``filter`` section of the application config.
                       Expected keys:
                         - ``damage_keywords`` (list[str]): Incident must contain
                           at least one of these words/phrases.
                         - ``locations`` (list[str]): Optional whitelist of
                           geographic terms.  When non-empty, the incident must
                           also match at least one location term.
    """

    def __init__(self, filter_config: dict[str, Any]) -> None:
        raw_keywords: list[str] = filter_config.get("damage_keywords", [])
        self._keywords: list[str] = [kw.lower() for kw in raw_keywords]

        raw_locations: list[str] = filter_config.get("locations", [])
        self._locations: list[str] = [loc.lower() for loc in raw_locations]

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def is_match(self, parsed: ParsedIncident) -> bool:
        """Return ``True`` when *parsed* represents a property-damage event.

        Args:
            parsed: A :class:`~property_damage_alerts.processing.parser.ParsedIncident`.

        Returns:
            ``True`` if the incident passes all active filter criteria.
        """
        if not self._keyword_match(parsed.text):
            return False

        if self._locations and not self._location_match(parsed.text):
            return False

        return True

    def apply(self, incidents: list[ParsedIncident]) -> list[ParsedIncident]:
        """Filter a list of incidents, returning only those that match.

        Args:
            incidents: Parsed incidents to evaluate.

        Returns:
            Subset of *incidents* that pass the filter.
        """
        matched = [p for p in incidents if self.is_match(p)]
        logger.debug(
            "Filter: %d/%d incidents matched.", len(matched), len(incidents)
        )
        return matched

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _keyword_match(self, text: str) -> bool:
        return any(kw in text for kw in self._keywords)

    def _location_match(self, text: str) -> bool:
        return any(loc in text for loc in self._locations)

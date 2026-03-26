"""Incident parser – normalise raw source data into structured fields."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from ..sources.base import Incident

# Simple address pattern: e.g. "123 Main St", "4500 N Broadway Ave"
_ADDRESS_RE = re.compile(
    r"\b\d{1,5}\s+(?:[NSEW]\s+)?[A-Za-z0-9]+(?:\s+[A-Za-z0-9]+){0,4}"
    r"\s+(?:St(?:reet)?|Ave(?:nue)?|Rd|Road|Blvd|Boulevard|Dr(?:ive)?|"
    r"Ln|Lane|Ct|Court|Pl(?:ace)?|Way|Hwy|Highway|Pkwy|Parkway)\b",
    re.IGNORECASE,
)

# Zip-code pattern (US 5-digit or ZIP+4)
_ZIP_RE = re.compile(r"\b\d{5}(?:-\d{4})?\b")


@dataclass
class ParsedIncident:
    """Enriched version of an :class:`~property_damage_alerts.sources.base.Incident`.

    Attributes:
        incident:       The original incident object.
        addresses:      Candidate street addresses extracted from the text.
        zip_codes:      Candidate ZIP codes extracted from the text.
        text:           Combined searchable text (title + summary).
    """

    incident: Incident
    addresses: list[str] = field(default_factory=list)
    zip_codes: list[str] = field(default_factory=list)
    text: str = ""


def parse_incident(incident: Incident) -> ParsedIncident:
    """Extract structured fields from a raw :class:`Incident`.

    Args:
        incident: The raw incident to parse.

    Returns:
        A :class:`ParsedIncident` with extracted addresses and ZIP codes.
    """
    combined = f"{incident.title} {incident.summary}"
    addresses = _ADDRESS_RE.findall(combined)
    zip_codes = _ZIP_RE.findall(combined)

    return ParsedIncident(
        incident=incident,
        addresses=addresses,
        zip_codes=zip_codes,
        text=combined.lower(),
    )

"""Fire department RSS source connector."""

from __future__ import annotations

from typing import Any

from .rss import RSSSource


class FireSource(RSSSource):
    """Polls fire department RSS feeds for property-damage incidents.

    Configuration example (``config.yaml``)::

        sources:
          - name: "City Fire Department"
            type: fire
            enabled: true
            urls:
              - "https://fire.example.gov/rss/incidents.xml"
            poll_interval: 300

    Args:
        name:   Human-readable source name.
        config: Source-level configuration dictionary.
    """

    def __init__(self, name: str, config: dict[str, Any]) -> None:
        super().__init__(name, config)

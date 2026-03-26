"""Police RSS / blotter source connector."""

from __future__ import annotations

from typing import Any

from .rss import RSSSource


class PoliceSource(RSSSource):
    """Polls police department RSS blotters for property-damage incidents.

    Configuration example (``config.yaml``)::

        sources:
          - name: "City Police Department"
            type: police
            enabled: true
            urls:
              - "https://police.example.gov/rss/incidents.xml"
            poll_interval: 300

    Args:
        name:   Human-readable source name.
        config: Source-level configuration dictionary.
    """

    def __init__(self, name: str, config: dict[str, Any]) -> None:
        super().__init__(name, config)

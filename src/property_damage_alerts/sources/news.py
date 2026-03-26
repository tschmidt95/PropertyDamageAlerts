"""News RSS source connector."""

from __future__ import annotations

from typing import Any

from .rss import RSSSource


class NewsSource(RSSSource):
    """Polls local/regional news RSS feeds for property-damage incidents.

    Configuration example (``config.yaml``)::

        sources:
          - name: "Local News"
            type: news
            enabled: true
            urls:
              - "https://news.example.com/feed.rss"
            poll_interval: 600

    Args:
        name:   Human-readable source name.
        config: Source-level configuration dictionary.
    """

    def __init__(self, name: str, config: dict[str, Any]) -> None:
        super().__init__(name, config)

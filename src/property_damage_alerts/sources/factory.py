"""Source factory – build source objects from configuration."""

from __future__ import annotations

import logging
from typing import Any

from .base import BaseSource
from .fire import FireSource
from .news import NewsSource
from .police import PoliceSource

logger = logging.getLogger(__name__)

# Registry mapping the ``type`` string in config to a source class.
_SOURCE_REGISTRY: dict[str, type[BaseSource]] = {
    "rss": __import__(
        "property_damage_alerts.sources.rss", fromlist=["RSSSource"]
    ).RSSSource,
    "police": PoliceSource,
    "fire": FireSource,
    "news": NewsSource,
}


def build_sources(sources_config: list[dict[str, Any]]) -> list[BaseSource]:
    """Instantiate source connectors from the ``sources`` section of config.

    Args:
        sources_config: List of source configuration dicts.

    Returns:
        List of enabled :class:`~property_damage_alerts.sources.base.BaseSource`
        instances.
    """
    sources: list[BaseSource] = []
    for cfg in sources_config:
        if not cfg.get("enabled", True):
            logger.info("Source '%s' is disabled; skipping.", cfg.get("name", "?"))
            continue

        source_type = cfg.get("type", "rss").lower()
        source_cls = _SOURCE_REGISTRY.get(source_type)
        if source_cls is None:
            logger.warning(
                "Unknown source type '%s' for source '%s'; skipping.",
                source_type,
                cfg.get("name", "?"),
            )
            continue

        name = cfg.get("name", source_type)
        sources.append(source_cls(name=name, config=cfg))
        logger.debug("Registered source '%s' (type=%s).", name, source_type)

    logger.info("Loaded %d source(s).", len(sources))
    return sources

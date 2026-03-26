"""Main entry point for PropertyDamageAlerts."""

from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

from .alerts.notifier import Notifier
from .config import load_config, resolve_env_secrets
from .processing.filter import DamageFilter
from .processing.parser import parse_incident
from .sources.factory import build_sources
from .storage.database import IncidentStore


def _setup_logging(level: str, log_file: str | None) -> None:
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_path, encoding="utf-8"))

    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s – %(message)s",
        handlers=handlers,
    )


def run_once(config: dict) -> int:
    """Fetch all sources, filter incidents, store and notify.

    Args:
        config: Loaded application configuration dictionary.

    Returns:
        Number of new property-damage incidents detected.
    """
    logger = logging.getLogger(__name__)

    sources = build_sources(config.get("sources", []))
    damage_filter = DamageFilter(config.get("filter", {}))
    store = IncidentStore(config["storage"]["db_path"])
    notifier = Notifier(config.get("alerts", {}))

    new_count = 0
    for source in sources:
        raw_incidents = source.safe_fetch()
        parsed_incidents = [parse_incident(inc) for inc in raw_incidents]
        matched = damage_filter.apply(parsed_incidents)

        for parsed in matched:
            if store.is_known(parsed.incident):
                logger.debug("Skipping already-known incident: %s", parsed.incident.title)
                continue
            store.save(parsed.incident)
            notifier.notify(parsed)
            logger.info(
                "NEW incident [%s] – %s", parsed.incident.source_name, parsed.incident.title
            )
            new_count += 1

    store.close()
    return new_count


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="PropertyDamageAlerts – monitor police, fire, and news for property damage.",
    )
    parser.add_argument(
        "--config",
        metavar="PATH",
        help="Path to config YAML file (default: config/config.yaml)",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run a single fetch cycle then exit.",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=300,
        metavar="SECONDS",
        help="Polling interval in seconds when running continuously (default: 300).",
    )
    args = parser.parse_args()

    config = load_config(args.config)
    resolve_env_secrets(config)

    log_cfg = config.get("logging", {})
    _setup_logging(log_cfg.get("level", "INFO"), log_cfg.get("log_file"))

    logger = logging.getLogger(__name__)
    logger.info("PropertyDamageAlerts starting.")

    if args.once:
        count = run_once(config)
        logger.info("Done. %d new incident(s) found.", count)
        return

    logger.info("Running continuously every %d seconds (Ctrl-C to stop).", args.interval)
    while True:
        try:
            count = run_once(config)
            logger.info("%d new incident(s) found this cycle.", count)
        except KeyboardInterrupt:
            logger.info("Interrupted by user. Exiting.")
            break
        except Exception:
            logger.exception("Unexpected error in run cycle.")
        time.sleep(args.interval)


if __name__ == "__main__":
    main()

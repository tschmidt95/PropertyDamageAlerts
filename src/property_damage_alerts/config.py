"""Configuration loader for PropertyDamageAlerts."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

_DEFAULT_CONFIG_PATH = Path(__file__).parent.parent.parent / "config" / "config.yaml"


def load_config(path: str | Path | None = None) -> dict[str, Any]:
    """Load YAML configuration from *path*.

    Falls back to ``config/config.yaml`` relative to the project root, or
    returns a minimal default configuration when no file is found.

    Args:
        path: Explicit path to a YAML config file.  ``None`` uses the default.

    Returns:
        Parsed configuration dictionary.
    """
    config_path = Path(path) if path else _DEFAULT_CONFIG_PATH

    if not config_path.exists():
        logger.warning("Config file not found at %s; using defaults.", config_path)
        return _default_config()

    with config_path.open("r", encoding="utf-8") as fh:
        data: dict[str, Any] = yaml.safe_load(fh) or {}

    logger.info("Loaded configuration from %s", config_path)
    return data


def _default_config() -> dict[str, Any]:
    return {
        "sources": [],
        "filter": {
            "damage_keywords": [
                "fire",
                "flood",
                "storm damage",
                "structural damage",
                "explosion",
                "collapse",
                "burst pipe",
                "water damage",
                "vandalism",
                "arson",
                "tornado",
                "hurricane",
                "hail",
                "wind damage",
                "smoke damage",
            ],
            "locations": [],
        },
        "alerts": {
            "email": {"enabled": False},
            "webhook": {"enabled": False},
        },
        "storage": {"db_path": "data/incidents.db"},
        "logging": {"level": "INFO", "log_file": "logs/pda.log"},
    }


def resolve_env_secrets(config: dict[str, Any]) -> dict[str, Any]:
    """Expand ``*_env`` keys in the alerts section into their actual values.

    For example, ``password_env: PDA_EMAIL_PASSWORD`` is replaced by the
    content of the ``PDA_EMAIL_PASSWORD`` environment variable.

    Args:
        config: Configuration dictionary (mutated in-place).

    Returns:
        The same dictionary with secrets resolved.
    """
    email_cfg = config.get("alerts", {}).get("email", {})
    env_key = email_cfg.get("password_env")
    if env_key:
        email_cfg["password"] = os.environ.get(env_key, "")
        email_cfg.pop("password_env", None)
    return config

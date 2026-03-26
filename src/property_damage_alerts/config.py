"""
Configuration – loads settings from environment variables / .env file.
"""

from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()


def _get(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


# ── Email / SMTP ──────────────────────────────────────────────────────────────
SMTP_HOST: str = _get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT: int = int(_get("SMTP_PORT", "587"))
SMTP_USERNAME: str = _get("SMTP_USERNAME")
SMTP_PASSWORD: str = _get("SMTP_PASSWORD")
FROM_EMAIL: str = _get("FROM_EMAIL")
FROM_NAME: str = _get("FROM_NAME", "Your Public Adjusting Firm")

# ── Firm details (used in outreach templates) ─────────────────────────────────
FIRM_NAME: str = _get("FIRM_NAME", "Your Public Adjusting Firm")
ADJUSTER_NAME: str = _get("ADJUSTER_NAME", "Your Name")
ADJUSTER_LICENSE: str = _get("ADJUSTER_LICENSE", "W123456")
ADJUSTER_PHONE: str = _get("ADJUSTER_PHONE", "(555) 555-5555")
ADJUSTER_EMAIL: str = _get("ADJUSTER_EMAIL", "adjuster@yourfirm.com")
FIRM_WEBSITE: str = _get("FIRM_WEBSITE", "https://yourfirm.com")

# ── FEMA Open Data ────────────────────────────────────────────────────────────
FEMA_API_BASE: str = _get("FEMA_API_BASE", "https://www.fema.gov/api/open/v2")

# ── NewsAPI ───────────────────────────────────────────────────────────────────
NEWS_API_KEY: str = _get("NEWS_API_KEY")
NEWS_API_BASE: str = _get("NEWS_API_BASE", "https://newsapi.org/v2")

# ── HOA marketing ─────────────────────────────────────────────────────────────
HOA_OUTREACH_DELAY_DAYS: int = int(_get("HOA_OUTREACH_DELAY_DAYS", "30"))

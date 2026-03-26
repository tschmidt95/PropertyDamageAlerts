"""
Fetches Florida property-damage news articles via NewsAPI.

Searches for articles about fires, wind damage, and structural damage
at Florida properties. Each article is returned as a ``PropertyIncident``.

Requires a NewsAPI key (https://newsapi.org – free tier available).
"""

from __future__ import annotations

import hashlib
import logging
import re
from datetime import date, timedelta
from typing import Any

import requests
from tenacity import retry, stop_after_attempt, wait_exponential

from property_damage_alerts import config
from property_damage_alerts.models import DamageType, IncidentSource, PropertyIncident

logger = logging.getLogger(__name__)

# Search queries that target Florida property damage stories
_QUERIES: list[tuple[str, list[DamageType]]] = [
    (
        "Florida house fire OR structure fire OR building fire",
        [DamageType.FIRE],
    ),
    (
        "Florida wind damage OR hurricane damage OR tornado damage property",
        [DamageType.WIND],
    ),
    (
        "Florida roof damage OR structural damage OR building collapse property",
        [DamageType.STRUCTURAL],
    ),
]

# Major Florida cities used for extracting location from article text.
# Sorted alphabetically for easy maintenance.
_FLORIDA_CITIES: list[str] = [
    "Boca Raton",
    "Bonita Springs",
    "Bradenton",
    "Cape Coral",
    "Clearwater",
    "Coral Springs",
    "Davie",
    "Daytona Beach",
    "Deltona",
    "Fort Lauderdale",
    "Fort Myers",
    "Gainesville",
    "Hialeah",
    "Hollywood",
    "Jacksonville",
    "Kissimmee",
    "Lakeland",
    "Melbourne",
    "Miami",
    "Miami Gardens",
    "Miramar",
    "Naples",
    "North Port",
    "Ocala",
    "Orlando",
    "Palm Bay",
    "Pembroke Pines",
    "Pensacola",
    "Pompano Beach",
    "Port St. Lucie",
    "Sarasota",
    "Sanford",
    "St. Petersburg",
    "Tallahassee",
    "Tampa",
    "West Palm Beach",
]

_FLORIDA_CITY_RE = re.compile(
    r"\b(" + "|".join(re.escape(c) for c in _FLORIDA_CITIES) + r")\b",
    re.IGNORECASE,
)


def _stable_id(url: str) -> str:
    """Generate a short stable identifier from an article URL."""
    return "news-" + hashlib.sha1(url.encode()).hexdigest()[:12]


def _extract_location(text: str) -> tuple[str, str]:
    """Return (city, county) from article text; defaults to ('Florida', 'Unknown')."""
    match = _FLORIDA_CITY_RE.search(text or "")
    city = match.group(0).title() if match else "Florida"
    return city, "Unknown"


def _parse_article(article: dict[str, Any], damage_types: list[DamageType]) -> PropertyIncident:
    title = article.get("title") or ""
    description = article.get("description") or ""
    published = article.get("publishedAt", "")[:10]
    url = article.get("url", "")

    try:
        incident_date = date.fromisoformat(published)
    except ValueError:
        incident_date = date.today()

    combined_text = f"{title} {description}"
    city, county = _extract_location(combined_text)

    return PropertyIncident(
        incident_id=_stable_id(url),
        source=IncidentSource.NEWS,
        incident_date=incident_date,
        damage_types=damage_types,
        address=f"See article: {url}",
        city=city,
        county=county,
        state="FL",
        description=f"{title}: {description}",
        raw_data=article,
    )


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def _search(query: str, from_date: str) -> list[dict]:
    """Perform a single NewsAPI everything search."""
    if not config.NEWS_API_KEY:
        logger.warning("NEWS_API_KEY not set – skipping news search.")
        return []

    params = {
        "q": query,
        "from": from_date,
        "language": "en",
        "sortBy": "publishedAt",
        "pageSize": 100,
        "apiKey": config.NEWS_API_KEY,
    }
    response = requests.get(f"{config.NEWS_API_BASE}/everything", params=params, timeout=30)
    response.raise_for_status()
    return response.json().get("articles", [])


def fetch_florida_news_incidents(days_back: int = 30) -> list[PropertyIncident]:
    """
    Query NewsAPI for Florida property-damage articles.

    Parameters
    ----------
    days_back:
        How many days back to search (NewsAPI free tier: 1 month).

    Returns
    -------
    list[PropertyIncident]
        De-duplicated list of news-sourced incidents.
    """
    from_date = (date.today() - timedelta(days=days_back)).isoformat()
    seen: set[str] = set()
    incidents: list[PropertyIncident] = []

    for query, damage_types in _QUERIES:
        try:
            articles = _search(query, from_date)
        except requests.RequestException as exc:
            logger.error("NewsAPI request failed for query '%s': %s", query, exc)
            continue

        for article in articles:
            incident = _parse_article(article, damage_types)
            if incident.incident_id not in seen:
                seen.add(incident.incident_id)
                incidents.append(incident)

    logger.info("Fetched %d Florida incidents from news", len(incidents))
    return incidents

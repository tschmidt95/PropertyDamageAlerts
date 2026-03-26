"""
Fetches Florida disaster / incident data from FEMA's Open Data API.

FEMA Open Data endpoint used:
  https://www.fema.gov/api/open/v2/disasterDeclarationsSummaries

Docs: https://www.fema.gov/about/openfema/data-sets
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any

import requests
from tenacity import retry, stop_after_attempt, wait_exponential

from property_damage_alerts import config
from property_damage_alerts.models import DamageType, IncidentSource, PropertyIncident

logger = logging.getLogger(__name__)

# FEMA incident type keywords that map to our damage categories
_FIRE_KEYWORDS = {"fire", "wildfire", "conflagration"}
_WIND_KEYWORDS = {"hurricane", "typhoon", "tornado", "wind", "cyclone", "tropical storm"}
_STRUCTURAL_KEYWORDS = {"flood", "structural", "collapse", "landslide", "earthquake", "tsunami"}

# FEMA incident types that map to each category
_FEMA_FIRE_TYPES = {"Fire", "Wildfire"}
_FEMA_WIND_TYPES = {"Hurricane", "Typhoon", "Tornado", "Severe Storm(s)", "Coastal Storm"}
_FEMA_STRUCTURAL_TYPES = {
    "Flood",
    "Severe Ice Storm",
    "Earthquake",
    "Mud/Landslide",
    "Tsunami",
    "Dam/Levee Break",
}


def _classify_damage(incident_type: str, title: str) -> list[DamageType]:
    """Return damage type(s) for a FEMA incident."""
    types: list[DamageType] = []
    combined = f"{incident_type} {title}".lower()

    if incident_type in _FEMA_FIRE_TYPES or any(k in combined for k in _FIRE_KEYWORDS):
        types.append(DamageType.FIRE)
    if incident_type in _FEMA_WIND_TYPES or any(k in combined for k in _WIND_KEYWORDS):
        types.append(DamageType.WIND)
    if incident_type in _FEMA_STRUCTURAL_TYPES or any(
        k in combined for k in _STRUCTURAL_KEYWORDS
    ):
        types.append(DamageType.STRUCTURAL)

    if not types:
        types.append(DamageType.OTHER)
    return types


def _parse_incident(raw: dict[str, Any]) -> PropertyIncident:
    """Convert a raw FEMA disaster record to a ``PropertyIncident``."""
    incident_date_str: str = raw.get("incidentBeginDate", raw.get("declarationDate", ""))
    try:
        incident_date = date.fromisoformat(incident_date_str[:10])
    except (ValueError, TypeError):
        incident_date = date.today()

    incident_type = raw.get("incidentType", "")
    title = raw.get("declarationTitle", "")
    county = raw.get("designatedArea", raw.get("county", "Unknown"))

    damage_types = _classify_damage(incident_type, title)

    return PropertyIncident(
        incident_id=f"fema-{raw.get('disasterNumber', 'unknown')}",
        source=IncidentSource.FEMA,
        incident_date=incident_date,
        damage_types=damage_types,
        address=f"See FEMA disaster {raw.get('disasterNumber')}",
        city=county,
        county=county,
        state="FL",
        description=f"{title} – {incident_type}",
        raw_data=raw,
    )


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def _fetch_page(params: dict) -> dict:
    """Fetch one page from the FEMA disasters API."""
    url = f"{config.FEMA_API_BASE}/disasterDeclarationsSummaries"
    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()
    return response.json()


def fetch_florida_incidents(
    days_back: int = 365,
    damage_filter: set[DamageType] | None = None,
) -> list[PropertyIncident]:
    """
    Fetch FEMA disaster declarations for Florida within the past ``days_back`` days.

    Parameters
    ----------
    days_back:
        How many days back from today to query.
    damage_filter:
        If provided, only return incidents matching these damage types.
        Defaults to fire, wind, and structural.

    Returns
    -------
    list[PropertyIncident]
        All matching Florida property incidents.
    """
    if damage_filter is None:
        damage_filter = {DamageType.FIRE, DamageType.WIND, DamageType.STRUCTURAL}

    since = (date.today() - timedelta(days=days_back)).isoformat()
    incidents: list[PropertyIncident] = []
    skip = 0
    page_size = 100

    while True:
        params = {
            "state": "FL",
            "$filter": f"incidentBeginDate ge '{since}'",
            "$orderby": "incidentBeginDate desc",
            "$top": page_size,
            "$skip": skip,
            "$format": "json",
            "$select": (
                "disasterNumber,state,declarationTitle,incidentType,"
                "incidentBeginDate,declarationDate,designatedArea,county"
            ),
        }
        try:
            data = _fetch_page(params)
        except requests.RequestException as exc:
            logger.error("FEMA API request failed: %s", exc)
            break

        records = data.get("DisasterDeclarationsSummaries", [])
        if not records:
            break

        for raw in records:
            incident = _parse_incident(raw)
            if not damage_filter or (set(incident.damage_types) & damage_filter):
                incidents.append(incident)

        if len(records) < page_size:
            break
        skip += page_size

    logger.info("Fetched %d Florida incidents from FEMA", len(incidents))
    return incidents

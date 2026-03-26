"""
Main pipeline – orchestrates disaster fetching, owner lookup, and outreach.
"""

from __future__ import annotations

import logging
from typing import Optional

from property_damage_alerts.fema_fetcher import fetch_florida_incidents
from property_damage_alerts.hoa_registry import HOARegistry, get_default_registry
from property_damage_alerts.models import DamageType, HOA, OutreachRecord, PropertyIncident
from property_damage_alerts.news_fetcher import fetch_florida_news_incidents
from property_damage_alerts.outreach import send_hoa_outreach, send_owner_outreach
from property_damage_alerts.property_lookup import lookup_owner

logger = logging.getLogger(__name__)


def run_disaster_outreach(
    days_back: int = 365,
    damage_filter: Optional[set[DamageType]] = None,
    use_fema: bool = True,
    use_news: bool = True,
    dry_run: bool = False,
) -> list[OutreachRecord]:
    """
    Full pipeline: fetch Florida disasters → look up owners → send outreach.

    Parameters
    ----------
    days_back:
        How many days back to search for incidents.
    damage_filter:
        Damage types to include. Defaults to fire, wind, and structural.
    use_fema:
        Include FEMA disaster declarations.
    use_news:
        Include news-sourced incidents.
    dry_run:
        Render messages and log them without actually sending emails.

    Returns
    -------
    list[OutreachRecord]
        One record per outreach attempt (successful or not).
    """
    if damage_filter is None:
        damage_filter = {DamageType.FIRE, DamageType.WIND, DamageType.STRUCTURAL}

    incidents: list[PropertyIncident] = []

    if use_fema:
        incidents.extend(fetch_florida_incidents(days_back=days_back, damage_filter=damage_filter))

    if use_news:
        news_days = min(days_back, 30)  # NewsAPI free tier: 1 month
        news_incidents = fetch_florida_news_incidents(days_back=news_days)
        # Filter news incidents to requested damage types
        incidents.extend(
            i for i in news_incidents if set(i.damage_types) & damage_filter
        )

    logger.info("Processing %d total incidents", len(incidents))
    records: list[OutreachRecord] = []

    for incident in incidents:
        owner = lookup_owner(incident)
        if owner is None:
            logger.debug(
                "No owner found for incident %s at %s – skipping outreach",
                incident.incident_id,
                incident.address,
            )
            continue

        record = send_owner_outreach(incident, owner, dry_run=dry_run)
        records.append(record)

    logger.info(
        "Completed disaster outreach: %d sent, %d failed",
        sum(1 for r in records if r.success),
        sum(1 for r in records if not r.success),
    )
    return records


def run_hoa_marketing(
    registry: Optional[HOARegistry] = None,
    dry_run: bool = False,
) -> list[OutreachRecord]:
    """
    Send marketing outreach to all HOAs in the registry.

    Parameters
    ----------
    registry:
        HOA registry to use. Defaults to the registry at the default path.
    dry_run:
        Render messages and log them without actually sending emails.

    Returns
    -------
    list[OutreachRecord]
        One record per HOA outreach attempt.
    """
    if registry is None:
        registry = get_default_registry()

    hoas = list(registry.all())
    logger.info("Sending HOA marketing outreach to %d HOAs", len(hoas))
    records: list[OutreachRecord] = []

    for hoa in hoas:
        record = send_hoa_outreach(hoa, dry_run=dry_run)
        records.append(record)

    logger.info(
        "HOA marketing complete: %d sent, %d failed",
        sum(1 for r in records if r.success),
        sum(1 for r in records if not r.success),
    )
    return records

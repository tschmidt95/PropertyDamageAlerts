"""
Property owner lookup via Florida county property appraiser portals.

Florida's 67 counties each maintain a public property appraiser website.
Many expose SOAP/REST APIs or allow CSV download of ownership data.

This module provides:
  • A base interface ``PropertyAppraiserClient``
  • A generic REST implementation that works with common Florida county APIs
  • A ``lookup_owner`` convenience function

When a county-specific API key or endpoint is not configured, the lookup
returns ``None`` gracefully so the rest of the pipeline can proceed.
"""

from __future__ import annotations

import logging
import os
from abc import ABC, abstractmethod
from typing import Optional

import requests
from tenacity import retry, stop_after_attempt, wait_exponential

from property_damage_alerts.models import PropertyIncident, PropertyOwner

logger = logging.getLogger(__name__)


class PropertyAppraiserClient(ABC):
    """Abstract base for county property appraiser lookups."""

    @abstractmethod
    def lookup_by_address(self, address: str, city: str, zip_code: str = "") -> Optional[PropertyOwner]:
        """Return the owner of the given property, or ``None`` if not found."""


class GenericRestAppraiserClient(PropertyAppraiserClient):
    """
    Generic REST client for county appraisers that support address-based search.

    Many Florida counties expose an endpoint similar to::

        GET /api/search?address=<addr>&city=<city>

    Configure the base URL via the ``PROPERTY_APPRAISER_BASE_URL`` environment
    variable per county.  This client handles the most common response shape;
    subclass and override ``_parse_response`` for counties with a different schema.
    """

    def __init__(self, base_url: str, api_key: str = "") -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(min=1, max=5))
    def _get(self, path: str, params: dict) -> dict:
        if self._api_key:
            params["apiKey"] = self._api_key
        response = requests.get(f"{self._base_url}{path}", params=params, timeout=15)
        response.raise_for_status()
        return response.json()

    def _parse_response(self, data: dict) -> Optional[PropertyOwner]:
        """
        Parse a generic county API response into a ``PropertyOwner``.

        Override this method for counties with a unique response schema.
        """
        # Try common top-level keys
        record = None
        for key in ("results", "parcels", "data", "properties"):
            if key in data and data[key]:
                record = data[key][0]
                break

        if record is None:
            return None

        name = record.get("ownerName") or record.get("owner_name") or record.get("owner") or ""
        if not name:
            return None

        return PropertyOwner(
            name=name,
            mailing_address=record.get("mailingAddress") or record.get("mailing_address") or "",
            mailing_city=record.get("mailingCity") or record.get("mailing_city") or "",
            mailing_state=record.get("mailingState") or record.get("mailing_state") or "FL",
            mailing_zip=record.get("mailingZip") or record.get("mailing_zip") or "",
            email=record.get("email"),
            phone=record.get("phone"),
            parcel_id=record.get("parcelId") or record.get("parcel_id"),
        )

    def lookup_by_address(self, address: str, city: str, zip_code: str = "") -> Optional[PropertyOwner]:
        try:
            data = self._get("/api/search", {"address": address, "city": city, "zip": zip_code})
            return self._parse_response(data)
        except requests.RequestException as exc:
            logger.warning("Property appraiser lookup failed for %s, %s: %s", address, city, exc)
            return None


def lookup_owner(incident: PropertyIncident) -> Optional[PropertyOwner]:
    """
    Attempt to look up the owner for the given incident's property.

    Returns ``None`` when no lookup client is configured or when the address
    is not a specific street address (e.g. FEMA county-level records).
    """
    api_key = os.environ.get("PROPERTY_APPRAISER_API_KEY", "")
    base_url = os.environ.get("PROPERTY_APPRAISER_BASE_URL", "")

    if not base_url:
        logger.debug(
            "PROPERTY_APPRAISER_BASE_URL not set – skipping owner lookup for incident %s",
            incident.incident_id,
        )
        return None

    client = GenericRestAppraiserClient(base_url=base_url, api_key=api_key)
    return client.lookup_by_address(
        address=incident.address,
        city=incident.city,
        zip_code=incident.zip_code or "",
    )

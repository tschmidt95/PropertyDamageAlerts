"""
Shared data models for the Property Damage Alerts system.
"""

from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class DamageType(str, Enum):
    FIRE = "fire"
    WIND = "wind"
    STRUCTURAL = "structural"
    OTHER = "other"


class IncidentSource(str, Enum):
    FEMA = "fema"
    NEWS = "news"
    MANUAL = "manual"


class PropertyIncident(BaseModel):
    """A property damage incident in Florida."""

    incident_id: str
    source: IncidentSource
    incident_date: date
    damage_types: list[DamageType]
    address: str
    city: str
    county: str
    state: str = "FL"
    zip_code: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    description: str = ""
    raw_data: dict = Field(default_factory=dict)


class PropertyOwner(BaseModel):
    """A property owner associated with an incident address."""

    name: str
    mailing_address: str
    mailing_city: str
    mailing_state: str
    mailing_zip: str
    email: Optional[str] = None
    phone: Optional[str] = None
    parcel_id: Optional[str] = None


class HOA(BaseModel):
    """A Homeowners Association to be marketed to."""

    name: str
    county: str
    city: str
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    mailing_address: Optional[str] = None
    num_units: Optional[int] = None
    notes: str = ""


class OutreachRecord(BaseModel):
    """Tracks outreach sent to a property owner or HOA."""

    recipient_type: str  # "owner" or "hoa"
    recipient_id: str
    incident_id: Optional[str] = None
    sent_date: date
    channel: str  # "email" | "letter"
    subject: str
    body_preview: str = ""
    success: bool = True
    error: Optional[str] = None

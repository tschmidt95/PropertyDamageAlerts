"""Shared test fixtures."""
import pytest

from property_damage_alerts.models import (
    DamageType,
    HOA,
    IncidentSource,
    PropertyIncident,
    PropertyOwner,
)
from datetime import date


@pytest.fixture
def sample_incident():
    return PropertyIncident(
        incident_id="test-001",
        source=IncidentSource.FEMA,
        incident_date=date(2024, 9, 15),
        damage_types=[DamageType.FIRE, DamageType.WIND],
        address="123 Main St",
        city="Tampa",
        county="Hillsborough",
        state="FL",
        zip_code="33601",
        description="Structure fire with wind damage",
    )


@pytest.fixture
def sample_owner():
    return PropertyOwner(
        name="Jane Smith",
        mailing_address="123 Main St",
        mailing_city="Tampa",
        mailing_state="FL",
        mailing_zip="33601",
        email="jane.smith@example.com",
    )


@pytest.fixture
def sample_hoa():
    return HOA(
        name="Palmetto Pointe HOA",
        county="Hillsborough",
        city="Tampa",
        contact_name="Board President",
        contact_email="board@palmettopointe.example.com",
        num_units=150,
    )

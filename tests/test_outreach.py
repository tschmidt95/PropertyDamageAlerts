"""Tests for the outreach module."""
import pytest

from property_damage_alerts.outreach import (
    _damage_description,
    _render_template,
    send_hoa_outreach,
    send_owner_outreach,
)
from property_damage_alerts.models import DamageType


class TestDamageDescription:
    def test_single(self):
        assert _damage_description([DamageType.FIRE]) == "fire damage"

    def test_two(self):
        desc = _damage_description([DamageType.FIRE, DamageType.WIND])
        assert "fire damage" in desc
        assert "wind damage" in desc
        assert "and" in desc

    def test_three(self):
        desc = _damage_description([DamageType.FIRE, DamageType.WIND, DamageType.STRUCTURAL])
        assert "structural damage" in desc

    def test_empty(self):
        assert _damage_description([]) == "property damage"


class TestRenderTemplate:
    def test_owner_template_has_subject(self, monkeypatch):
        import property_damage_alerts.config as cfg
        monkeypatch.setattr(cfg, "FIRM_NAME", "Test Firm")
        monkeypatch.setattr(cfg, "ADJUSTER_NAME", "Test Adjuster")
        monkeypatch.setattr(cfg, "ADJUSTER_LICENSE", "W999999")
        monkeypatch.setattr(cfg, "ADJUSTER_PHONE", "(555) 000-0000")
        monkeypatch.setattr(cfg, "ADJUSTER_EMAIL", "test@test.com")
        monkeypatch.setattr(cfg, "FIRM_WEBSITE", "https://test.com")

        context = {
            "adjuster_name": "Test Adjuster",
            "adjuster_license": "W999999",
            "adjuster_phone": "(555) 000-0000",
            "adjuster_email": "test@test.com",
            "firm_name": "Test Firm",
            "firm_website": "https://test.com",
            "owner_name": "John Doe",
            "property_address": "456 Oak Ave",
            "city": "Orlando",
            "zip_code": "32801",
            "incident_date": "January 01, 2024",
            "damage_description": "fire damage",
        }
        subject, body = _render_template("owner_outreach.txt.j2", context)
        assert len(subject) > 0
        assert "John Doe" in body
        assert "fire damage" in body
        assert "Test Adjuster" in body

    def test_hoa_template_has_subject(self):
        context = {
            "adjuster_name": "Test Adjuster",
            "adjuster_license": "W999999",
            "adjuster_phone": "(555) 000-0000",
            "adjuster_email": "test@test.com",
            "firm_name": "Test Firm",
            "firm_website": "https://test.com",
            "hoa_name": "Sunset Villas HOA",
            "contact_name": "Board Chair",
            "city": "Naples",
            "county": "Collier",
        }
        subject, body = _render_template("hoa_outreach.txt.j2", context)
        assert len(subject) > 0
        assert "Sunset Villas HOA" in body


class TestSendOwnerOutreach:
    def test_dry_run_returns_success_record(self, sample_incident, sample_owner):
        record = send_owner_outreach(sample_incident, sample_owner, dry_run=True)
        assert record.success is True
        assert record.recipient_type == "owner"
        assert record.incident_id == sample_incident.incident_id

    def test_no_email_records_letter_channel(self, sample_incident, sample_owner):
        sample_owner.email = None
        record = send_owner_outreach(sample_incident, sample_owner, dry_run=False)
        assert record.channel == "letter"

    def test_dry_run_does_not_raise_on_missing_smtp(self, sample_incident, sample_owner):
        # Even with no SMTP config, dry_run should succeed
        record = send_owner_outreach(sample_incident, sample_owner, dry_run=True)
        assert record.success is True


class TestSendHoaOutreach:
    def test_dry_run_returns_success_record(self, sample_hoa):
        record = send_hoa_outreach(sample_hoa, dry_run=True)
        assert record.success is True
        assert record.recipient_type == "hoa"

    def test_no_email_records_letter_channel(self, sample_hoa):
        sample_hoa.contact_email = None
        record = send_hoa_outreach(sample_hoa, dry_run=False)
        assert record.channel == "letter"

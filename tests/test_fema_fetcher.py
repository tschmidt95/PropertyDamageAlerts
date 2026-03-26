"""Tests for the FEMA fetcher."""
import pytest
import responses as resp_lib
from datetime import date

from property_damage_alerts.fema_fetcher import (
    _classify_damage,
    _parse_incident,
    fetch_florida_incidents,
)
from property_damage_alerts.models import DamageType


class TestClassifyDamage:
    def test_fire_incident_type(self):
        types = _classify_damage("Fire", "House fire in Tampa")
        assert DamageType.FIRE in types

    def test_wind_incident_hurricane(self):
        types = _classify_damage("Hurricane", "Hurricane Ian")
        assert DamageType.WIND in types

    def test_structural_flood(self):
        types = _classify_damage("Flood", "Flooding in Miami-Dade")
        assert DamageType.STRUCTURAL in types

    def test_wind_keyword_in_title(self):
        types = _classify_damage("Severe Storm(s)", "Tornado damage to residential areas")
        assert DamageType.WIND in types

    def test_fire_keyword_in_title(self):
        types = _classify_damage("Other", "Wildfire destroys multiple homes")
        assert DamageType.FIRE in types

    def test_unknown_becomes_other(self):
        types = _classify_damage("Unknown", "Some unknown event")
        assert types == [DamageType.OTHER]

    def test_multiple_damage_types(self):
        types = _classify_damage("Hurricane", "Hurricane with fire")
        assert DamageType.WIND in types
        assert DamageType.FIRE in types


class TestParseIncident:
    def test_basic_parse(self):
        raw = {
            "disasterNumber": 4567,
            "declarationTitle": "HURRICANE IAN",
            "incidentType": "Hurricane",
            "incidentBeginDate": "2022-09-28T00:00:00.000Z",
            "designatedArea": "Lee County",
        }
        incident = _parse_incident(raw)
        assert incident.incident_id == "fema-4567"
        assert incident.state == "FL"
        assert incident.incident_date == date(2022, 9, 28)
        assert DamageType.WIND in incident.damage_types
        assert incident.county == "Lee County"

    def test_missing_date_defaults_to_today(self):
        raw = {
            "disasterNumber": 9999,
            "declarationTitle": "Test",
            "incidentType": "Fire",
        }
        incident = _parse_incident(raw)
        assert incident.incident_date == date.today()


class TestFetchFloridaIncidents:
    @resp_lib.activate
    def test_returns_empty_on_empty_api_response(self, monkeypatch):
        import property_damage_alerts.config as cfg
        monkeypatch.setattr(cfg, "FEMA_API_BASE", "https://test.fema.gov/api/open/v2")

        resp_lib.add(
            resp_lib.GET,
            "https://test.fema.gov/api/open/v2/disasterDeclarationsSummaries",
            json={"DisasterDeclarationsSummaries": []},
            status=200,
        )
        result = fetch_florida_incidents(days_back=30)
        assert result == []

    @resp_lib.activate
    def test_filters_to_florida_damage_types(self, monkeypatch):
        import property_damage_alerts.config as cfg
        monkeypatch.setattr(cfg, "FEMA_API_BASE", "https://test.fema.gov/api/open/v2")

        raw_records = [
            {
                "disasterNumber": 1001,
                "declarationTitle": "WILDFIRE",
                "incidentType": "Fire",
                "incidentBeginDate": "2024-01-10T00:00:00.000Z",
                "designatedArea": "Alachua County",
            },
            {
                "disasterNumber": 1002,
                "declarationTitle": "HURRICANE",
                "incidentType": "Hurricane",
                "incidentBeginDate": "2024-09-01T00:00:00.000Z",
                "designatedArea": "Charlotte County",
            },
        ]
        resp_lib.add(
            resp_lib.GET,
            "https://test.fema.gov/api/open/v2/disasterDeclarationsSummaries",
            json={"DisasterDeclarationsSummaries": raw_records},
            status=200,
        )
        result = fetch_florida_incidents(
            days_back=730,
            damage_filter={DamageType.FIRE, DamageType.WIND},
        )
        assert len(result) == 2
        ids = {r.incident_id for r in result}
        assert "fema-1001" in ids
        assert "fema-1002" in ids

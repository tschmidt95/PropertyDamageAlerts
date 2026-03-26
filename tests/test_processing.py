"""Tests for the processing pipeline (parser + filter)."""

from __future__ import annotations

from datetime import datetime

from property_damage_alerts.processing.filter import DamageFilter
from property_damage_alerts.processing.parser import parse_incident
from property_damage_alerts.sources.base import Incident

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _incident(title: str = "", summary: str = "") -> Incident:
    return Incident(
        source_name="test",
        title=title,
        summary=summary,
        url="http://example.com",
        published_at=datetime(2024, 1, 1),
    )


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

def test_parse_incident_extracts_address():
    inc = _incident(
        title="Fire at 123 Main St",
        summary="Firefighters responded to 123 Main St after a blaze broke out.",
    )
    parsed = parse_incident(inc)
    assert any("123" in addr for addr in parsed.addresses)


def test_parse_incident_extracts_zip_code():
    inc = _incident(
        summary="The incident occurred near downtown, zip code 90210.",
    )
    parsed = parse_incident(inc)
    assert "90210" in parsed.zip_codes


def test_parse_incident_text_is_lowercase():
    inc = _incident(title="FIRE DAMAGE", summary="Heavy FLOODING.")
    parsed = parse_incident(inc)
    assert parsed.text == parsed.text.lower()


def test_parse_incident_no_address_no_zip():
    inc = _incident(title="General incident", summary="Nothing specific.")
    parsed = parse_incident(inc)
    # Addresses and zips may be empty lists when none are found.
    assert isinstance(parsed.addresses, list)
    assert isinstance(parsed.zip_codes, list)


# ---------------------------------------------------------------------------
# DamageFilter – keyword matching
# ---------------------------------------------------------------------------

_FILTER_CFG = {
    "damage_keywords": ["fire", "flood", "hail", "wind damage"],
    "locations": [],
}


def _filter() -> DamageFilter:
    return DamageFilter(_FILTER_CFG)


def test_filter_matches_keyword_in_title():
    inc = _incident(title="House fire reported")
    parsed = parse_incident(inc)
    assert _filter().is_match(parsed)


def test_filter_matches_keyword_in_summary():
    inc = _incident(summary="Flooding has damaged several homes.")
    parsed = parse_incident(inc)
    assert _filter().is_match(parsed)


def test_filter_no_match_on_unrelated_incident():
    inc = _incident(title="Traffic stop on Main", summary="Officer issued a citation.")
    parsed = parse_incident(inc)
    assert not _filter().is_match(parsed)


def test_filter_case_insensitive():
    inc = _incident(title="HAIL STORM causes damage")
    parsed = parse_incident(inc)
    assert _filter().is_match(parsed)


def test_filter_multi_keyword_phrase():
    cfg = {"damage_keywords": ["wind damage"], "locations": []}
    f = DamageFilter(cfg)
    inc = _incident(summary="Wind damage was reported across the county.")
    parsed = parse_incident(inc)
    assert f.is_match(parsed)


# ---------------------------------------------------------------------------
# DamageFilter – location filtering
# ---------------------------------------------------------------------------

def test_filter_location_restricts_results():
    cfg = {"damage_keywords": ["fire"], "locations": ["springfield"]}
    f = DamageFilter(cfg)

    inc_match = _incident(title="Fire in Springfield neighborhood")
    inc_no_match = _incident(title="Fire on the outskirts")

    assert f.is_match(parse_incident(inc_match))
    assert not f.is_match(parse_incident(inc_no_match))


def test_filter_empty_location_list_accepts_all():
    cfg = {"damage_keywords": ["fire"], "locations": []}
    f = DamageFilter(cfg)
    inc = _incident(title="Fire in Unknown City")
    assert f.is_match(parse_incident(inc))


# ---------------------------------------------------------------------------
# DamageFilter.apply
# ---------------------------------------------------------------------------

def test_filter_apply_returns_only_matches():
    f = _filter()
    incidents = [
        parse_incident(_incident(title="House fire reported")),
        parse_incident(_incident(title="Traffic stop")),
        parse_incident(_incident(summary="Severe flooding near river")),
    ]
    matched = f.apply(incidents)
    assert len(matched) == 2

"""Tests for the news fetcher."""
import pytest
import responses as resp_lib
from datetime import date

from property_damage_alerts.news_fetcher import (
    _extract_location,
    _parse_article,
    _stable_id,
    fetch_florida_news_incidents,
)
from property_damage_alerts.models import DamageType


class TestStableId:
    def test_is_deterministic(self):
        url = "https://example.com/article-1"
        assert _stable_id(url) == _stable_id(url)

    def test_is_prefixed(self):
        assert _stable_id("https://example.com/x").startswith("news-")

    def test_different_urls_give_different_ids(self):
        assert _stable_id("https://a.com") != _stable_id("https://b.com")


class TestExtractLocation:
    def test_known_city(self):
        city, _ = _extract_location("A fire broke out in Tampa last night.")
        assert city.lower() == "tampa"

    def test_unknown_city_defaults(self):
        city, county = _extract_location("A fire broke out somewhere.")
        assert city == "Florida"
        assert county == "Unknown"


class TestParseArticle:
    def test_basic_parse(self):
        article = {
            "title": "House fire in Orlando destroys three units",
            "description": "Orlando, FL – Fire fighters responded to a three-alarm fire.",
            "publishedAt": "2024-03-15T10:00:00Z",
            "url": "https://example.com/orlando-fire",
        }
        incident = _parse_article(article, [DamageType.FIRE])
        assert DamageType.FIRE in incident.damage_types
        assert incident.state == "FL"
        assert incident.incident_date == date(2024, 3, 15)
        assert incident.city.lower() == "orlando"

    def test_bad_date_defaults_to_today(self):
        article = {
            "title": "Wind damage in Miami",
            "description": "",
            "publishedAt": "not-a-date",
            "url": "https://example.com/wind",
        }
        incident = _parse_article(article, [DamageType.WIND])
        assert incident.incident_date == date.today()


class TestFetchFloridaNewsIncidents:
    def test_returns_empty_when_no_api_key(self, monkeypatch):
        import property_damage_alerts.config as cfg
        monkeypatch.setattr(cfg, "NEWS_API_KEY", "")
        result = fetch_florida_news_incidents(days_back=7)
        assert result == []

    @resp_lib.activate
    def test_deduplicates_articles(self, monkeypatch):
        import property_damage_alerts.config as cfg
        monkeypatch.setattr(cfg, "NEWS_API_KEY", "test_key")
        monkeypatch.setattr(cfg, "NEWS_API_BASE", "https://test.newsapi.org/v2")

        article = {
            "title": "Fire in Miami",
            "description": "A house fire in Miami.",
            "publishedAt": "2024-06-01T00:00:00Z",
            "url": "https://example.com/unique-fire",
        }
        # Return same article for all three queries
        for _ in range(3):
            resp_lib.add(
                resp_lib.GET,
                "https://test.newsapi.org/v2/everything",
                json={"articles": [article]},
                status=200,
            )
        result = fetch_florida_news_incidents(days_back=7)
        # Should de-duplicate – only 1 unique article
        assert len(result) == 1

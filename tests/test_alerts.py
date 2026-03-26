"""Tests for the alert notifier."""

from __future__ import annotations

import json
from datetime import datetime
from unittest.mock import MagicMock, patch

from property_damage_alerts.alerts.notifier import Notifier
from property_damage_alerts.processing.parser import ParsedIncident
from property_damage_alerts.sources.base import Incident

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parsed(title: str = "House Fire at 123 Elm St", url: str = "http://x.com/1") -> ParsedIncident:
    inc = Incident(
        source_name="Test Source",
        title=title,
        summary="A fire broke out at a residential property.",
        url=url,
        published_at=datetime(2024, 6, 15, 10, 30),
    )
    return ParsedIncident(
        incident=inc,
        addresses=["123 Elm St"],
        zip_codes=["12345"],
        text=f"{inc.title} {inc.summary}".lower(),
    )


# ---------------------------------------------------------------------------
# Webhook notifications
# ---------------------------------------------------------------------------

def test_notifier_sends_webhook():
    cfg = {
        "email": {"enabled": False},
        "webhook": {
            "enabled": True,
            "urls": ["https://hooks.example.com/pda"],
        },
    }
    notifier = Notifier(cfg)
    parsed = _parsed()

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.raise_for_status = MagicMock()

    with patch("requests.post", return_value=mock_resp) as mock_post:
        notifier.notify(parsed)

    mock_post.assert_called_once()
    call_kwargs = mock_post.call_args
    assert call_kwargs[0][0] == "https://hooks.example.com/pda"

    payload = json.loads(call_kwargs[1]["data"])
    assert payload["title"] == "House Fire at 123 Elm St"
    assert "123 Elm St" in payload["addresses"]


def test_notifier_sends_multiple_webhooks():
    cfg = {
        "email": {"enabled": False},
        "webhook": {
            "enabled": True,
            "urls": ["https://a.com/hook", "https://b.com/hook"],
        },
    }
    notifier = Notifier(cfg)

    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()

    with patch("requests.post", return_value=mock_resp) as mock_post:
        notifier.notify(_parsed())

    assert mock_post.call_count == 2


def test_notifier_webhook_failure_does_not_raise():
    cfg = {
        "email": {"enabled": False},
        "webhook": {"enabled": True, "urls": ["https://bad.example.com"]},
    }
    notifier = Notifier(cfg)

    with patch("requests.post", side_effect=ConnectionError("refused")):
        # Should log the error but not propagate the exception.
        notifier.notify(_parsed())


# ---------------------------------------------------------------------------
# Email notifications
# ---------------------------------------------------------------------------

def test_notifier_sends_email():
    cfg = {
        "webhook": {"enabled": False},
        "email": {
            "enabled": True,
            "smtp_host": "smtp.example.com",
            "smtp_port": 587,
            "use_tls": True,
            "username": "user@example.com",
            "password": "secret",
            "from_address": "user@example.com",
            "to_addresses": ["recipient@example.com"],
        },
    }
    notifier = Notifier(cfg)

    mock_smtp = MagicMock()
    mock_smtp.__enter__ = MagicMock(return_value=mock_smtp)
    mock_smtp.__exit__ = MagicMock(return_value=False)

    with patch("smtplib.SMTP", return_value=mock_smtp):
        notifier.notify(_parsed())

    mock_smtp.send_message.assert_called_once()


def test_notifier_email_failure_does_not_raise():
    cfg = {
        "webhook": {"enabled": False},
        "email": {
            "enabled": True,
            "smtp_host": "smtp.bad.com",
            "smtp_port": 587,
            "use_tls": False,
            "username": "",
            "password": "",
            "from_address": "a@b.com",
            "to_addresses": ["c@d.com"],
        },
    }
    notifier = Notifier(cfg)

    with patch("smtplib.SMTP", side_effect=OSError("connection refused")):
        notifier.notify(_parsed())  # must not raise


# ---------------------------------------------------------------------------
# notify_many
# ---------------------------------------------------------------------------

def test_notifier_notify_many():
    cfg = {"email": {"enabled": False}, "webhook": {"enabled": False}}
    notifier = Notifier(cfg)
    # All disabled – just ensures the method iterates without error.
    notifier.notify_many([_parsed(), _parsed(title="Flood at 456 Oak Ave")])

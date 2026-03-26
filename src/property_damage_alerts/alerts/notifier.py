"""Alert notifier – send email and/or webhook notifications for matched incidents."""

from __future__ import annotations

import json
import logging
import smtplib
import ssl
from email.mime.text import MIMEText
from typing import Any

import requests

from ..processing.parser import ParsedIncident

logger = logging.getLogger(__name__)


class Notifier:
    """Send alerts via email and/or webhook for property-damage incidents.

    Args:
        alerts_config: The ``alerts`` section of the application config.
    """

    def __init__(self, alerts_config: dict[str, Any]) -> None:
        self._email_cfg: dict[str, Any] = alerts_config.get("email", {})
        self._webhook_cfg: dict[str, Any] = alerts_config.get("webhook", {})

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def notify(self, parsed: ParsedIncident) -> None:
        """Send all configured alert types for a matched incident.

        Args:
            parsed: A parsed incident that has passed the damage filter.
        """
        if self._email_cfg.get("enabled"):
            self._send_email(parsed)

        if self._webhook_cfg.get("enabled"):
            self._send_webhooks(parsed)

    def notify_many(self, incidents: list[ParsedIncident]) -> None:
        """Call :meth:`notify` for each incident in *incidents*.

        Args:
            incidents: List of matched, parsed incidents.
        """
        for parsed in incidents:
            self.notify(parsed)

    # ------------------------------------------------------------------
    # Email
    # ------------------------------------------------------------------

    def _send_email(self, parsed: ParsedIncident) -> None:
        cfg = self._email_cfg
        incident = parsed.incident

        subject = f"[PropertyDamageAlert] {incident.source_name}: {incident.title}"
        body_lines = [
            f"Source:    {incident.source_name}",
            f"Title:     {incident.title}",
            f"Published: {incident.published_at.isoformat()}",
            "",
            incident.summary,
        ]
        if incident.url:
            body_lines += ["", f"Link: {incident.url}"]
        if parsed.addresses:
            body_lines += ["", "Detected addresses:"]
            body_lines += [f"  • {addr}" for addr in parsed.addresses]

        body = "\n".join(body_lines)

        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = subject
        msg["From"] = cfg.get("from_address", "")
        msg["To"] = ", ".join(cfg.get("to_addresses", []))

        try:
            context = ssl.create_default_context()
            with smtplib.SMTP(cfg["smtp_host"], cfg.get("smtp_port", 587)) as smtp:
                if cfg.get("use_tls", True):
                    smtp.starttls(context=context)
                if cfg.get("username"):
                    smtp.login(cfg["username"], cfg.get("password", ""))
                smtp.send_message(msg)
            logger.info("Email alert sent for: %s", incident.title)
        except Exception:
            logger.exception("Failed to send email alert for: %s", incident.title)

    # ------------------------------------------------------------------
    # Webhook
    # ------------------------------------------------------------------

    def _send_webhooks(self, parsed: ParsedIncident) -> None:
        payload = parsed.incident.as_dict()
        payload["addresses"] = parsed.addresses
        payload["zip_codes"] = parsed.zip_codes

        for url in self._webhook_cfg.get("urls", []):
            try:
                resp = requests.post(
                    url,
                    data=json.dumps(payload),
                    headers={"Content-Type": "application/json"},
                    timeout=10,
                )
                resp.raise_for_status()
                logger.info("Webhook delivered to %s (status=%d).", url, resp.status_code)
            except Exception:
                logger.exception("Failed to deliver webhook to %s.", url)

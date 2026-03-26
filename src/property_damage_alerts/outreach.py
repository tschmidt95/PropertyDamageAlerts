"""
Outreach module – renders Jinja2 templates and sends email via SMTP.

Handles both property-owner outreach (after a specific incident) and
HOA marketing outreach.
"""

from __future__ import annotations

import logging
import smtplib
from datetime import date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape

from property_damage_alerts import config
from property_damage_alerts.models import (
    HOA,
    DamageType,
    OutreachRecord,
    PropertyIncident,
    PropertyOwner,
)

logger = logging.getLogger(__name__)

_TEMPLATE_DIR = Path(__file__).parent / "templates"
_JINJA_ENV = Environment(
    loader=FileSystemLoader(str(_TEMPLATE_DIR)),
    autoescape=select_autoescape([]),  # plain-text templates
    keep_trailing_newline=True,
)

# ── Damage type helpers ───────────────────────────────────────────────────────

_DAMAGE_LABELS = {
    DamageType.FIRE: "fire damage",
    DamageType.WIND: "wind damage",
    DamageType.STRUCTURAL: "structural damage",
    DamageType.OTHER: "property damage",
}


def _damage_description(damage_types: list[DamageType]) -> str:
    labels = [_DAMAGE_LABELS.get(dt, "property damage") for dt in damage_types]
    if not labels:
        return "property damage"
    if len(labels) == 1:
        return labels[0]
    return ", ".join(labels[:-1]) + " and " + labels[-1]


# ── Template rendering ────────────────────────────────────────────────────────

def _render_template(template_name: str, context: dict) -> tuple[str, str]:
    """
    Render a template and return ``(subject, body)``.

    The first line of the template must be ``Subject: <subject text>``
    followed by a blank line, then the body.
    """
    tmpl = _JINJA_ENV.get_template(template_name)
    rendered = tmpl.render(**context)
    lines = rendered.splitlines()

    subject = ""
    body_start = 0
    for i, line in enumerate(lines):
        if line.startswith("Subject:"):
            subject = line[len("Subject:"):].strip()
            body_start = i + 1
            # Skip blank separator line
            if body_start < len(lines) and not lines[body_start].strip():
                body_start += 1
            break

    body = "\n".join(lines[body_start:])
    return subject, body


def _firm_context() -> dict:
    """Return template context variables common to all outreach."""
    return {
        "adjuster_name": config.ADJUSTER_NAME,
        "adjuster_license": config.ADJUSTER_LICENSE,
        "adjuster_phone": config.ADJUSTER_PHONE,
        "adjuster_email": config.ADJUSTER_EMAIL,
        "firm_name": config.FIRM_NAME,
        "firm_website": config.FIRM_WEBSITE,
    }


# ── SMTP sending ──────────────────────────────────────────────────────────────

def _send_email(to_email: str, to_name: str, subject: str, body: str) -> None:
    """Send a plain-text email via SMTP."""
    if not config.SMTP_USERNAME or not config.SMTP_PASSWORD:
        logger.warning("SMTP credentials not configured – email not sent to %s", to_email)
        raise RuntimeError("SMTP credentials not configured")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{config.FROM_NAME} <{config.FROM_EMAIL}>"
    msg["To"] = f"{to_name} <{to_email}>"
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.login(config.SMTP_USERNAME, config.SMTP_PASSWORD)
            smtp.sendmail(config.FROM_EMAIL, to_email, msg.as_string())
    except smtplib.SMTPAuthenticationError as exc:
        raise RuntimeError(
            f"SMTP authentication failed for {config.SMTP_USERNAME}. "
            "Check SMTP_USERNAME and SMTP_PASSWORD in your .env file."
        ) from exc
    except smtplib.SMTPConnectError as exc:
        raise RuntimeError(
            f"Could not connect to SMTP server {config.SMTP_HOST}:{config.SMTP_PORT}."
        ) from exc
    except smtplib.SMTPException as exc:
        raise RuntimeError(f"Failed to send email to {to_email}: {exc}") from exc


# ── Public API ────────────────────────────────────────────────────────────────

def send_owner_outreach(
    incident: PropertyIncident,
    owner: PropertyOwner,
    dry_run: bool = False,
) -> OutreachRecord:
    """
    Send outreach to a property owner about a specific incident.

    Parameters
    ----------
    incident:
        The property damage incident.
    owner:
        The property owner to contact.
    dry_run:
        If ``True``, render the message and log it but do not send email.

    Returns
    -------
    OutreachRecord
        A record of the outreach attempt.
    """
    context = {
        **_firm_context(),
        "owner_name": owner.name,
        "property_address": incident.address,
        "city": incident.city,
        "zip_suffix": f" {incident.zip_code}" if incident.zip_code else "",
        "incident_date": incident.incident_date.strftime("%B %d, %Y"),
        "damage_description": _damage_description(incident.damage_types),
    }

    subject, body = _render_template("owner_outreach.txt.j2", context)
    success = True
    error: Optional[str] = None
    channel = "email"

    if dry_run:
        logger.info(
            "[DRY RUN] Would send owner outreach to %s <%s>\nSubject: %s\n%s",
            owner.name,
            owner.email or "no-email",
            subject,
            body,
        )
    elif owner.email:
        try:
            _send_email(owner.email, owner.name, subject, body)
            logger.info("Sent owner outreach email to %s <%s>", owner.name, owner.email)
        except Exception as exc:
            logger.error("Failed to send email to %s: %s", owner.email, exc)
            success = False
            error = str(exc)
    else:
        logger.info(
            "No email address for %s – outreach recorded as letter channel", owner.name
        )
        channel = "letter"

    return OutreachRecord(
        recipient_type="owner",
        recipient_id=owner.parcel_id or owner.name,
        incident_id=incident.incident_id,
        sent_date=date.today(),
        channel=channel,
        subject=subject,
        body_preview=body[:200],
        success=success,
        error=error,
    )


def send_hoa_outreach(hoa: HOA, dry_run: bool = False) -> OutreachRecord:
    """
    Send marketing outreach to an HOA.

    Parameters
    ----------
    hoa:
        The HOA to market to.
    dry_run:
        If ``True``, render the message and log it but do not send email.

    Returns
    -------
    OutreachRecord
        A record of the outreach attempt.
    """
    context = {
        **_firm_context(),
        "hoa_name": hoa.name,
        "contact_greeting": hoa.contact_name or "HOA Board Member",
        "city": hoa.city,
        "county": hoa.county,
    }

    subject, body = _render_template("hoa_outreach.txt.j2", context)
    success = True
    error: Optional[str] = None
    channel = "email"

    if dry_run:
        logger.info(
            "[DRY RUN] Would send HOA outreach to %s <%s>\nSubject: %s\n%s",
            hoa.name,
            hoa.contact_email or "no-email",
            subject,
            body,
        )
    elif hoa.contact_email:
        try:
            _send_email(
                hoa.contact_email,
                hoa.contact_name or hoa.name,
                subject,
                body,
            )
            logger.info("Sent HOA outreach email to %s <%s>", hoa.name, hoa.contact_email)
        except Exception as exc:
            logger.error("Failed to send HOA email to %s: %s", hoa.contact_email, exc)
            success = False
            error = str(exc)
    else:
        logger.info("No email address for HOA %s – recorded as letter channel", hoa.name)
        channel = "letter"

    return OutreachRecord(
        recipient_type="hoa",
        recipient_id=hoa.name,
        incident_id=None,
        sent_date=date.today(),
        channel=channel,
        subject=subject,
        body_preview=body[:200],
        success=success,
        error=error,
    )

"""
Command-line interface for Property Damage Alerts.

Usage examples
--------------
# Search for recent Florida disasters and preview outreach (no email sent)
property-damage-alerts disasters --dry-run

# Send outreach for incidents from the last 90 days
property-damage-alerts disasters --days-back 90

# Import HOAs from a CSV and send marketing emails (dry-run)
property-damage-alerts hoa import-csv path/to/hoas.csv
property-damage-alerts hoa market --dry-run

# Show HOA registry count
property-damage-alerts hoa list
"""

from __future__ import annotations

import logging
import sys

import click

from property_damage_alerts.hoa_registry import HOARegistry, get_default_registry, load_hoas_from_csv
from property_damage_alerts.models import DamageType
from property_damage_alerts.pipeline import run_disaster_outreach, run_hoa_marketing

# ── Logging ───────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s – %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ── Column widths for HOA list table ──────────────────────────────────────────

_HOA_LIST_COL_NAME = 40
_HOA_LIST_COL_CITY = 20
_HOA_LIST_COL_COUNTY = 20

# ── Root group ────────────────────────────────────────────────────────────────


@click.group()
@click.version_option()
def main() -> None:
    """Property Damage Alerts – Florida disaster monitoring & Public Adjuster marketing."""


# ── Disasters command ─────────────────────────────────────────────────────────


@main.command("disasters")
@click.option(
    "--days-back",
    default=365,
    show_default=True,
    type=int,
    help="Number of days back to search for incidents.",
)
@click.option(
    "--damage-types",
    default="fire,wind,structural",
    show_default=True,
    help="Comma-separated damage types to include: fire, wind, structural, other.",
)
@click.option("--no-fema", is_flag=True, help="Skip FEMA disaster declarations.")
@click.option("--no-news", is_flag=True, help="Skip news-based incident search.")
@click.option(
    "--dry-run",
    is_flag=True,
    help="Preview messages without sending emails.",
)
def disasters_cmd(
    days_back: int,
    damage_types: str,
    no_fema: bool,
    no_news: bool,
    dry_run: bool,
) -> None:
    """Fetch Florida property-damage incidents and send owner outreach."""
    damage_filter: set[DamageType] = set()
    for dt_str in damage_types.split(","):
        dt_str = dt_str.strip().lower()
        try:
            damage_filter.add(DamageType(dt_str))
        except ValueError:
            click.echo(f"Unknown damage type '{dt_str}' – ignoring.", err=True)

    if not damage_filter:
        click.echo("No valid damage types specified – exiting.", err=True)
        sys.exit(1)

    if dry_run:
        click.echo("🔍  DRY RUN – messages will be rendered but NOT sent.\n")

    records = run_disaster_outreach(
        days_back=days_back,
        damage_filter=damage_filter,
        use_fema=not no_fema,
        use_news=not no_news,
        dry_run=dry_run,
    )

    sent = sum(1 for r in records if r.success)
    failed = sum(1 for r in records if not r.success)
    click.echo(f"\n✅  Owner outreach complete: {sent} sent, {failed} failed.")


# ── HOA commands ──────────────────────────────────────────────────────────────


@main.group("hoa")
def hoa_group() -> None:
    """Manage the HOA registry and send marketing outreach."""


@hoa_group.command("import-csv")
@click.argument("csv_path", type=click.Path(exists=True))
@click.option("--db", default=None, help="Path to HOA registry JSON file.")
def hoa_import_csv(csv_path: str, db: str | None) -> None:
    """Import HOAs from a CSV file into the registry."""
    registry = HOARegistry(db) if db else get_default_registry()
    hoas = load_hoas_from_csv(csv_path)
    count = registry.add_many(hoas)
    click.echo(f"✅  Imported {count} HOAs into registry (total: {registry.count()}).")


@hoa_group.command("list")
@click.option("--db", default=None, help="Path to HOA registry JSON file.")
def hoa_list(db: str | None) -> None:
    """List all HOAs in the registry."""
    registry = HOARegistry(db) if db else get_default_registry()
    hoas = list(registry.all())
    if not hoas:
        click.echo("Registry is empty. Use 'hoa import-csv' to add HOAs.")
        return
    click.echo(f"{'Name':<{_HOA_LIST_COL_NAME}} {'City':<{_HOA_LIST_COL_CITY}} {'County':<{_HOA_LIST_COL_COUNTY}} {'Email'}")
    click.echo("-" * (_HOA_LIST_COL_NAME + _HOA_LIST_COL_CITY + _HOA_LIST_COL_COUNTY + 20))
    for hoa in hoas:
        click.echo(
            f"{hoa.name[:_HOA_LIST_COL_NAME - 1]:<{_HOA_LIST_COL_NAME}} "
            f"{hoa.city[:_HOA_LIST_COL_CITY - 1]:<{_HOA_LIST_COL_CITY}} "
            f"{hoa.county[:_HOA_LIST_COL_COUNTY - 1]:<{_HOA_LIST_COL_COUNTY}} "
            f"{hoa.contact_email or '—'}"
        )
    click.echo(f"\nTotal: {len(hoas)} HOAs")


@hoa_group.command("market")
@click.option("--db", default=None, help="Path to HOA registry JSON file.")
@click.option(
    "--dry-run",
    is_flag=True,
    help="Preview messages without sending emails.",
)
def hoa_market(db: str | None, dry_run: bool) -> None:
    """Send marketing outreach to all HOAs in the registry."""
    registry = HOARegistry(db) if db else get_default_registry()

    if registry.count() == 0:
        click.echo("Registry is empty. Use 'hoa import-csv' to add HOAs first.")
        return

    if dry_run:
        click.echo("🔍  DRY RUN – messages will be rendered but NOT sent.\n")

    records = run_hoa_marketing(registry=registry, dry_run=dry_run)
    sent = sum(1 for r in records if r.success)
    failed = sum(1 for r in records if not r.success)
    click.echo(f"\n✅  HOA marketing complete: {sent} sent, {failed} failed.")

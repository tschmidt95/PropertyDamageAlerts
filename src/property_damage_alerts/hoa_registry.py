"""
HOA registry – manages a list of Florida HOAs to be marketed to.

HOAs can be loaded from:
  • A CSV file (``--hoa-csv path/to/hoas.csv``)
  • Entered manually via the CLI
  • Future: scraped from the Florida Division of Condominiums, Timeshares, and Mobile Homes

CSV format (header row required):
  name, county, city, contact_name, contact_email, contact_phone,
  mailing_address, num_units, notes
"""

from __future__ import annotations

import csv
import json
import logging
from pathlib import Path
from typing import Iterator

from property_damage_alerts.models import HOA

logger = logging.getLogger(__name__)

# Default path for the HOA database (JSON)
_DEFAULT_DB_PATH = Path.home() / ".property_damage_alerts" / "hoa_registry.json"


# ── CSV import ────────────────────────────────────────────────────────────────

def load_hoas_from_csv(csv_path: str | Path) -> list[HOA]:
    """Load HOAs from a CSV file."""
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"HOA CSV file not found: {path}")

    hoas: list[HOA] = []
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            try:
                hoa = HOA(
                    name=row.get("name", "").strip(),
                    county=row.get("county", "").strip(),
                    city=row.get("city", "").strip(),
                    contact_name=row.get("contact_name", "").strip() or None,
                    contact_email=row.get("contact_email", "").strip() or None,
                    contact_phone=row.get("contact_phone", "").strip() or None,
                    mailing_address=row.get("mailing_address", "").strip() or None,
                    num_units=int(row["num_units"]) if row.get("num_units", "").strip().isdigit() else None,
                    notes=row.get("notes", "").strip(),
                )
                if hoa.name:
                    hoas.append(hoa)
            except Exception as exc:
                logger.warning("Skipping malformed HOA row %s: %s", row, exc)

    logger.info("Loaded %d HOAs from %s", len(hoas), path)
    return hoas


# ── JSON persistence ──────────────────────────────────────────────────────────

class HOARegistry:
    """
    A simple file-backed registry of HOAs.

    Entries are stored as JSON in ``~/.property_damage_alerts/hoa_registry.json``
    (or a custom path).  The registry is append-friendly – adding an HOA with the
    same name+county will update the existing record.
    """

    def __init__(self, db_path: str | Path = _DEFAULT_DB_PATH) -> None:
        self._path = Path(db_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._data: dict[str, dict] = {}
        if self._path.exists():
            self._load()

    def _load(self) -> None:
        with self._path.open(encoding="utf-8") as fh:
            self._data = json.load(fh)

    def _save(self) -> None:
        with self._path.open("w", encoding="utf-8") as fh:
            json.dump(self._data, fh, indent=2, default=str)

    def _key(self, hoa: HOA) -> str:
        return f"{hoa.name.lower().strip()}|{hoa.county.lower().strip()}"

    def add(self, hoa: HOA) -> None:
        """Add or update an HOA in the registry."""
        self._data[self._key(hoa)] = hoa.model_dump()
        self._save()

    def add_many(self, hoas: list[HOA]) -> int:
        """Add multiple HOAs. Returns the count of new/updated entries."""
        for hoa in hoas:
            self._data[self._key(hoa)] = hoa.model_dump()
        self._save()
        return len(hoas)

    def all(self) -> Iterator[HOA]:
        """Iterate over all registered HOAs."""
        for record in self._data.values():
            try:
                yield HOA(**record)
            except Exception as exc:
                logger.warning("Skipping malformed HOA record: %s", exc)

    def count(self) -> int:
        return len(self._data)


# ── Convenience factory ───────────────────────────────────────────────────────

def get_default_registry() -> HOARegistry:
    """Return the registry stored at the default path."""
    return HOARegistry(_DEFAULT_DB_PATH)

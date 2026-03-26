"""Tests for the HOA registry."""
import csv
import json
import tempfile
from pathlib import Path

import pytest

from property_damage_alerts.hoa_registry import HOARegistry, load_hoas_from_csv
from property_damage_alerts.models import HOA


class TestLoadHoasFromCsv:
    def _write_csv(self, rows: list[dict], tmp_path: Path) -> Path:
        csv_path = tmp_path / "hoas.csv"
        fieldnames = [
            "name", "county", "city", "contact_name", "contact_email",
            "contact_phone", "mailing_address", "num_units", "notes",
        ]
        with csv_path.open("w", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        return csv_path

    def test_loads_valid_rows(self, tmp_path):
        rows = [
            {
                "name": "Lakewood HOA",
                "county": "Orange",
                "city": "Orlando",
                "contact_name": "Alice",
                "contact_email": "alice@lakewood.example.com",
                "contact_phone": "",
                "mailing_address": "",
                "num_units": "200",
                "notes": "",
            }
        ]
        path = self._write_csv(rows, tmp_path)
        hoas = load_hoas_from_csv(path)
        assert len(hoas) == 1
        assert hoas[0].name == "Lakewood HOA"
        assert hoas[0].num_units == 200

    def test_skips_rows_with_empty_name(self, tmp_path):
        rows = [
            {"name": "", "county": "Orange", "city": "Orlando",
             "contact_name": "", "contact_email": "", "contact_phone": "",
             "mailing_address": "", "num_units": "", "notes": ""},
        ]
        path = self._write_csv(rows, tmp_path)
        hoas = load_hoas_from_csv(path)
        assert len(hoas) == 0

    def test_file_not_found(self, tmp_path):
        nonexistent = str(tmp_path / "nonexistent_hoas.csv")
        with pytest.raises(FileNotFoundError):
            load_hoas_from_csv(nonexistent)


class TestHOARegistry:
    def test_add_and_retrieve(self, tmp_path):
        db = tmp_path / "registry.json"
        registry = HOARegistry(db)
        hoa = HOA(name="Bayfront HOA", county="Pinellas", city="St. Petersburg")
        registry.add(hoa)
        all_hoas = list(registry.all())
        assert len(all_hoas) == 1
        assert all_hoas[0].name == "Bayfront HOA"

    def test_update_existing(self, tmp_path):
        db = tmp_path / "registry.json"
        registry = HOARegistry(db)
        hoa = HOA(name="Cypress HOA", county="Broward", city="Fort Lauderdale")
        registry.add(hoa)
        # Update with an email
        hoa_updated = HOA(
            name="Cypress HOA",
            county="Broward",
            city="Fort Lauderdale",
            contact_email="board@cypress.example.com",
        )
        registry.add(hoa_updated)
        all_hoas = list(registry.all())
        assert len(all_hoas) == 1
        assert all_hoas[0].contact_email == "board@cypress.example.com"

    def test_persists_to_disk(self, tmp_path):
        db = tmp_path / "registry.json"
        registry = HOARegistry(db)
        hoa = HOA(name="Palm HOA", county="Miami-Dade", city="Miami")
        registry.add(hoa)
        # Re-open
        registry2 = HOARegistry(db)
        assert registry2.count() == 1

    def test_count(self, tmp_path):
        db = tmp_path / "registry.json"
        registry = HOARegistry(db)
        registry.add_many([
            HOA(name="HOA A", county="X", city="Y"),
            HOA(name="HOA B", county="X", city="Y"),
        ])
        assert registry.count() == 2

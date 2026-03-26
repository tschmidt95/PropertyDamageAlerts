"""Tests for the CLI."""
import pytest
from click.testing import CliRunner

from property_damage_alerts.cli import main


@pytest.fixture
def runner():
    return CliRunner()


class TestDisastersCommand:
    def test_help(self, runner):
        result = runner.invoke(main, ["disasters", "--help"])
        assert result.exit_code == 0
        assert "days-back" in result.output

    def test_invalid_damage_type(self, runner, monkeypatch):
        """Invalid damage types are ignored; if all invalid, exit with error."""
        import property_damage_alerts.pipeline as pipeline
        monkeypatch.setattr(pipeline, "run_disaster_outreach", lambda **kw: [])
        result = runner.invoke(main, ["disasters", "--damage-types", "invalid_type"])
        assert result.exit_code != 0

    def test_dry_run_calls_pipeline(self, runner, monkeypatch):
        import property_damage_alerts.cli as cli_mod
        calls = []
        monkeypatch.setattr(
            cli_mod,
            "run_disaster_outreach",
            lambda **kw: (calls.append(kw), [])[1],
        )
        result = runner.invoke(main, ["disasters", "--dry-run", "--days-back", "30"])
        assert result.exit_code == 0
        assert calls[0]["dry_run"] is True
        assert calls[0]["days_back"] == 30


class TestHoaCommands:
    def test_hoa_list_empty(self, runner, tmp_path):
        db = str(tmp_path / "registry.json")
        result = runner.invoke(main, ["hoa", "list", "--db", db])
        assert result.exit_code == 0
        assert "empty" in result.output.lower()

    def test_hoa_import_csv(self, runner, tmp_path):
        import csv
        csv_path = tmp_path / "hoas.csv"
        with csv_path.open("w", newline="") as fh:
            writer = csv.DictWriter(
                fh,
                fieldnames=["name", "county", "city", "contact_name", "contact_email",
                             "contact_phone", "mailing_address", "num_units", "notes"],
            )
            writer.writeheader()
            writer.writerow({
                "name": "Sunset HOA", "county": "Orange", "city": "Orlando",
                "contact_name": "", "contact_email": "", "contact_phone": "",
                "mailing_address": "", "num_units": "50", "notes": "",
            })
        db = str(tmp_path / "registry.json")
        result = runner.invoke(main, ["hoa", "import-csv", str(csv_path), "--db", db])
        assert result.exit_code == 0
        assert "1" in result.output

    def test_hoa_market_dry_run(self, runner, tmp_path, sample_hoa, monkeypatch):
        import property_damage_alerts.cli as cli_mod
        calls = []
        monkeypatch.setattr(
            cli_mod,
            "run_hoa_marketing",
            lambda **kw: (calls.append(kw), [])[1],
        )
        # Add an HOA first so it's not empty
        from property_damage_alerts.hoa_registry import HOARegistry
        db = str(tmp_path / "registry.json")
        reg = HOARegistry(db)
        reg.add(sample_hoa)

        result = runner.invoke(main, ["hoa", "market", "--dry-run", "--db", db])
        assert result.exit_code == 0
        assert calls[0]["dry_run"] is True

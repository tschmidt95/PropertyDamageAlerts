"""Tests for configuration loading and secret resolution."""

from __future__ import annotations

from property_damage_alerts.config import load_config, resolve_env_secrets


def test_load_config_returns_defaults_when_file_missing(tmp_path):
    cfg = load_config(tmp_path / "nonexistent.yaml")
    assert "sources" in cfg
    assert "filter" in cfg
    assert "alerts" in cfg
    assert "storage" in cfg


def test_load_config_reads_yaml_file(tmp_path):
    yaml_content = """
sources:
  - name: Test Source
    type: rss
    enabled: true
    urls: []
filter:
  damage_keywords:
    - fire
  locations: []
alerts:
  email:
    enabled: false
  webhook:
    enabled: false
storage:
  db_path: data/test.db
logging:
  level: DEBUG
"""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(yaml_content)
    cfg = load_config(config_file)
    assert cfg["sources"][0]["name"] == "Test Source"
    assert cfg["filter"]["damage_keywords"] == ["fire"]
    assert cfg["storage"]["db_path"] == "data/test.db"


def test_resolve_env_secrets_expands_password(monkeypatch):
    monkeypatch.setenv("MY_SMTP_PASS", "supersecret")
    cfg = {
        "alerts": {
            "email": {
                "enabled": True,
                "password_env": "MY_SMTP_PASS",
            }
        }
    }
    resolve_env_secrets(cfg)
    assert cfg["alerts"]["email"]["password"] == "supersecret"
    assert "password_env" not in cfg["alerts"]["email"]


def test_resolve_env_secrets_missing_env_gives_empty_string(monkeypatch):
    monkeypatch.delenv("UNSET_VAR", raising=False)
    cfg = {
        "alerts": {
            "email": {
                "password_env": "UNSET_VAR",
            }
        }
    }
    resolve_env_secrets(cfg)
    assert cfg["alerts"]["email"]["password"] == ""

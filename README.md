# PropertyDamageAlerts

> Aggregate signals from police, fire departments, and news sources to alert on property-damage events for Public Adjusting work.

---

## Overview

PropertyDamageAlerts (PDA) continuously polls RSS feeds published by local police departments, fire departments, and news outlets.  
When an entry matches a configurable list of property-damage keywords (fire, flood, hail, etc.) it is:

1. **Parsed** – street addresses and ZIP codes are extracted from the text.  
2. **Stored** – written to a local SQLite database (deduplication prevents re-alerting).  
3. **Notified** – an email and/or webhook notification is sent to configured recipients.

---

## Repository Layout

```
PropertyDamageAlerts/
├── config/
│   └── config.example.yaml     # Template – copy to config/config.yaml
├── src/
│   └── property_damage_alerts/
│       ├── config.py            # YAML config loader
│       ├── main.py              # CLI entry point
│       ├── sources/             # Data-source connectors
│       │   ├── base.py          # Abstract BaseSource + Incident dataclass
│       │   ├── rss.py           # Generic RSS/Atom poller
│       │   ├── police.py        # Police blotter connector
│       │   ├── fire.py          # Fire department connector
│       │   ├── news.py          # News RSS connector
│       │   └── factory.py       # Build sources from config
│       ├── processing/
│       │   ├── parser.py        # Extract addresses / ZIP codes from text
│       │   └── filter.py        # Keyword + location filtering
│       ├── alerts/
│       │   └── notifier.py      # Email + webhook alert delivery
│       └── storage/
│           └── database.py      # SQLite incident store
├── tests/                       # pytest test suite (41 tests)
├── requirements.txt
├── requirements-dev.txt
└── pyproject.toml
```

---

## Quick Start

### 1. Install

```bash
# Runtime dependencies
pip install -r requirements.txt

# Development / test dependencies
pip install -r requirements-dev.txt

# Or install the package in editable mode (includes dev extras)
pip install -e ".[dev]"
```

### 2. Configure

```bash
cp config/config.example.yaml config/config.yaml
```

Edit `config/config.yaml` and fill in:

- **sources** – RSS feed URLs for your local police / fire / news outlets  
- **filter.damage_keywords** – terms that indicate property damage  
- **filter.locations** – optional geographic whitelist (city names, zip codes, etc.)  
- **alerts.email** – SMTP settings for email notifications  
- **alerts.webhook** – HTTP endpoint(s) to receive JSON payloads  
- **storage.db_path** – path to the SQLite database file  

Sensitive values (SMTP password) are read from environment variables:

```bash
export PDA_EMAIL_PASSWORD="your-smtp-password"
```

### 3. Run

```bash
# Single poll cycle (useful for testing / cron jobs)
pda --once

# Continuous polling every 5 minutes (default)
pda

# Custom interval (seconds) and explicit config path
pda --config /path/to/config.yaml --interval 600
```

---

## Adding a New Data Source

1. Create a new file in `src/property_damage_alerts/sources/` that subclasses `BaseSource` (or `RSSSource` for RSS feeds).  
2. Register the new type string in `sources/factory.py`'s `_SOURCE_REGISTRY`.  
3. Add the source to `config.yaml` with `type: your_new_type`.

---

## Running Tests

```bash
pytest
```

Coverage report:

```bash
pytest --cov=property_damage_alerts --cov-report=term-missing
```

---

## License

Apache 2.0 – see [LICENSE](LICENSE).


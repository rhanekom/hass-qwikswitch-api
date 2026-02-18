# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Home Assistant custom component (`qwikswitch_api`) that integrates QwikSwitch smart home devices via cloud polling. Supports dimmers (QS-D-S5) as lights and relays (QS-R-S5, QS-R-S30) as switches. Uses the `qwikswitch-api` Python library for API communication.

## Common Commands

### Development
```bash
.devcontainer/scripts/setup    # Install dependencies and pre-commit hooks
.devcontainer/scripts/develop  # Start a local Home Assistant instance (port 8123)
.devcontainer/scripts/clean    # Reset Home Assistant config directory
```

### Linting & Formatting
```bash
.devcontainer/scripts/lint     # Run ruff format + ruff check --fix
ruff check .                   # Lint only (CI uses this)
ruff format . --check          # Format check only (CI uses this)
pre-commit run --all-files     # Run all pre-commit hooks (pyupgrade, black, codespell, ruff)
```

### Testing
```bash
pytest tests/                  # Run all tests
pytest tests/test_foo.py       # Run a single test file
pytest tests/test_foo.py::test_bar -v  # Run a single test
```

Tests use `pytest-homeassistant-custom-component` which provides Home Assistant's test infrastructure. See `tests/conftest.py` for fixtures (`mock_qsclient`, `setup_integration`).

## Architecture

### Data Flow
```
User action → Light/Switch.turn_on/off()
  → BaseEntity.control_device_optimistic() → CommandQueue.enqueue_set_device()
  → CommandQueue processes with priority & delay → QSClient API call
  → UI shows optimistic value immediately

Coordinator polls periodically (default 5s)
  → CommandQueue.enqueue_poll() → QSClient.get_devices_status()
  → Coordinator distributes data → Entities reconcile optimistic values
```

### Key Modules (in `custom_components/qwikswitch_api/`)

- **`__init__.py`** — Integration setup/teardown. Creates QSClient, CommandQueue, and DataUpdateCoordinator. Handles config entry migration (v1→v2).
- **`command_queue.py`** — Priority queue managing API rate limits (30 req/min). Device commands take priority over polls. Debounces duplicate commands to the same device. Configurable delay between requests (default 2s).
- **`coordinator.py`** — Standard HA DataUpdateCoordinator wrapping poll requests through the command queue.
- **`entity.py`** — Base entity with optimistic update pattern: updates UI immediately on command, reconciles with polled data later.
- **`light.py`** / **`switch.py`** — Platform entities. Lights use brightness (0-255 HA ↔ 0-100 internal). Switches are binary (0 or 100).
- **`config_flow.py`** — Config and options flows. Validates credentials via API key generation. Unique ID from slugified master key.
- **`const.py`** — Domain, config keys, data keys, device models.

### External Dependency

The `qwikswitch-api` library (`QSClient`) handles all HTTP communication with the QwikSwitch cloud API. The integration never makes direct HTTP calls.

## Ruff Configuration

All lint rules enabled (`select = ["ALL"]`) with specific exclusions. Target: Python 3.12. Max complexity: 25. Test files have relaxed rules (asserts, magic values, missing docstrings allowed). See `.ruff.toml` for details.

## CI/CD

Two GitHub Actions workflows on push/PR to main:
- **lint.yml** — `ruff check` and `ruff format --check`
- **validate.yml** — Home Assistant `hassfest` manifest validation and HACS validation

## Config Entry

Version 2 with migration support from v1 (adds `command_delay`). Config data includes: email, master_key, poll_frequency, command_delay.

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Home Assistant custom component (`qwikswitch_api`) that integrates QwikSwitch smart home devices via cloud polling. Supports dimmers (QS-D-S5) as lights and relays (QS-R-S5, QS-R-S30) as switches. Uses the `qwikswitch-api` Python library for API communication.

## Common Commands

The project uses [uv](https://docs.astral.sh/uv/) for dependency management. All
Python tooling runs inside the uv-managed environment (`uv run …`).

### Development

```bash
.devcontainer/scripts/setup    # Sync deps (uv sync) and install pre-commit hooks
.devcontainer/scripts/develop  # Start a local Home Assistant instance (port 8123)
.devcontainer/scripts/clean    # Reset Home Assistant config directory
uv sync                        # Install/update .venv from uv.lock
uv lock                        # Re-resolve uv.lock after changing dependencies
```

### Linting & Formatting

```bash
.devcontainer/scripts/lint         # Run ruff format + ruff check --fix (via uv)
uv run ruff check .                # Lint only (CI uses this)
uv run ruff format . --check       # Format check only (CI uses this)
uv run pre-commit run --all-files  # Run all pre-commit hooks
```

### Testing

```bash
uv run pytest tests/                          # Run all tests
uv run pytest tests/test_foo.py               # Run a single test file
uv run pytest tests/test_foo.py::test_bar -v  # Run a single test
```

Tests use `pytest-homeassistant-custom-component` which provides Home Assistant's test infrastructure. See `tests/conftest.py` for fixtures (`mock_qsclient`, `setup_integration`).

## Architecture

### Data Flow

```text
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

## Dependencies

`pyproject.toml` + `uv.lock` are the single source of truth for dependencies (there is no `requirements.txt`).

- **`[project.dependencies]`** — the component's *runtime* deps. Keep in sync with `manifest.json` `requirements`. Currently just `qwikswitch-api`.
- **`[dependency-groups.dev]`** — Home Assistant plus dev/test/lint tooling (not shipped to users).
- After changing either, run `uv lock` and commit the updated `uv.lock`.

Vulnerability scanning (`pip-audit` pre-commit hook) audits **only our runtime tree**, resolved independently via `uv pip compile pyproject.toml`. It deliberately excludes Home Assistant's large transitive tree — HA hard-pins many packages (e.g. `requests`) that are not ours to fix, and its unified lock resolution would otherwise leak those pins into the audit.

## Ruff Configuration

All lint rules enabled (`select = ["ALL"]`) with specific exclusions. Target: Python 3.13. Max complexity: 25. Test files have relaxed rules (asserts, magic values, missing docstrings allowed). See `.ruff.toml` for details.

## CI/CD

Two GitHub Actions workflows on push/PR to main:

- **lint.yml** — installs uv, `uv sync`, then `uv run ruff check` and `uv run ruff format --check`
- **validate.yml** — Home Assistant `hassfest` manifest validation and HACS validation

## Pre-commit Hooks

Configured in `.pre-commit-config.yaml` (run with `uv run pre-commit run --all-files`):
file hygiene + JSON/YAML/TOML validation + private-key/AWS-credential detection, codespell,
ruff lint + format, markdownlint, shellcheck, actionlint, gitleaks (secret scanning),
pip-audit (dependency vuln scan, our runtime tree only), and pytest (the full test suite).
`actionlint` and `gitleaks` use the `-system` hook variants and rely on the binaries baked
into the Dockerfile.

## Working Conventions

- **Never auto-commit or push** — always ask first.
- **Don't branch automatically** — the user handles branching.
- **No self-attribution** — do not add "Authored by / Generated with Claude Code" or `Co-Authored-By` lines to commits, PRs, or any artifact.
- **Commit the complete change set** — when committing, include all changed and new files (`git add -A`). Never create partial commits.
- **Before finalizing a commit, scan for secrets and accidental files** — check the staged diff for credentials/keys and for anything that shouldn't be committed (virtualenvs, config artifacts, scratch files) and stop if found.
- **Don't let issues hang** — surface problems proactively; fix low-impact ones directly, ask before fixing high-impact ones. Never bypass failing checks, broken tests, or other issues just to keep going.
- **Research, don't assume** — verify options (including via web search) rather than assuming APIs/libraries behave as described.
- **If something can be caught by a pre-commit hook, add it** — prefer enforcing a rule mechanically over relying on memory.

## Documentation & Source of Truth

- Keep an authoritative design/spec doc and a canonical TODO list; treat them as the source of truth for design decisions and next actions, and keep them current as work lands.
- Record *why* decisions were taken, not just *what* — so future work doesn't re-litigate settled choices.

## Dev Environment

Setup is split by scope so frequently-run setup stays fast:

- **System-wide / global installs** (apt packages, standalone binaries: `uv`, `actionlint`, `gitleaks`, Claude Code) live in `.devcontainer/Dockerfile`, which is baked into the image and changes rarely.
- **User- and project-specific setup** (dependency sync, pre-commit hook install, shell aliases) lives in `.devcontainer/scripts/setup`, which re-runs on every container create.
- Persist every tool you install in one of these two places — never rely on an ad-hoc install that vanishes on the next rebuild. Pinned tool versions in the Dockerfile must be mirrored in `.pre-commit-config.yaml` (e.g. `actionlint`, `gitleaks`).

## MCP / External Capabilities

If a task needs a capability outside the current tools, check the MCP Launchpad (`mcpl`) gateway first. **Always discover before calling — never guess tool names.**

```bash
mcpl search "<query>"            # Find tools across all servers (shows required params)
mcpl list                        # List servers; `mcpl list <server>` lists its tools
mcpl inspect <server> <tool> --example   # Full schema + a ready-to-run example call
mcpl call <server> <tool> '{"param": "value"}'   # Execute a tool
```

Typical flow: `search` for the tool → `inspect --example` to see its schema → `call` it. If calls fail, `mcpl verify` tests connections and `mcpl auth login <server>` handles OAuth.

## Git Workflow

- **Always commit all changed and new files.** Never create partial commits — every commit should include the complete set of changes.

## Config Entry

Version 2 with migration support from v1 (adds `command_delay`). Config data includes: email, master_key, poll_frequency, command_delay.

# Contributing

Thanks for considering a contribution to Aviation Weather. This document
covers the practical steps; see [`CLAUDE.md`](CLAUDE.md) for a deeper
architecture overview if you're making a non-trivial change.

Participation in this project is governed by our
[Code of Conduct](CODE_OF_CONDUCT.md).

## Getting started

```bash
git clone <your fork>
cd aviation_weather
pip install -e ".[dev]" --config-settings editable_mode=compat
```

This installs the integration in editable mode plus dev dependencies
(`ruff`, `pytest`, `pytest-homeassistant-custom-component`, and the
airport-database generator's dependencies).

The `--config-settings editable_mode=compat` flag is required, not
optional: modern setuptools' default (PEP 660) editable install adds a
synthetic import-hook entry to `sys.path` instead of a real directory,
which crashes Home Assistant's `custom_components` auto-discovery
(`homeassistant/loader.py`) with a `FileNotFoundError` mentioning
`__editable__...finder.__path_hook__` — `compat` mode falls back to the
older, plain-directory-on-`sys.path` behavior HA's loader expects.

## Running tests and lint

```bash
pytest                          # full test suite
pytest --cov=custom_components.aviation_weather --cov-report=term-missing
pytest tests/metar/test_api.py  # a single file
pytest tests/metar/test_api.py::TestGetMetar::test_returns_mapped_data_on_success

ruff check .                    # lint
ruff format --check .           # format check
```

CI runs hassfest validation, `ruff check`/`ruff format --check`, `pytest`
across Python 3.12/3.13/3.14, and a job that regenerates the airport
database from fresh source data and re-runs the suite against it. All of
these should pass locally before you open a PR.

### Checking HACS validation locally

If you touch `manifest.json`, `hacs.json`, or anything else HACS
validates, you can run the exact same check as
`.github/workflows/hacs.yml` locally instead of waiting on CI:

```bash
./scripts/check_hacs.sh
```

Requires Docker and a GitHub token with read access to this repo (it
reuses the one already stored by `git` in `~/.git-credentials` if you
don't set `GITHUB_TOKEN` yourself). Note that a couple of checks
(`hacsjson`, `integration_manifest`) fetch files via
`raw.githubusercontent.com`, which only serves **public** repositories
regardless of the token — if this repo is private, those two will fail
here exactly as they do in CI, and there's nothing to fix in the files
themselves.

## Making a change

- **New field on an existing report** (METAR/TAF/SIGMET): touch all four
  layers — API payload → mapper → model → sensor/binary_sensor attribute.
  Mirror the existing tests for that layer.
- **New sensor or entity**: follow the vertical-slice pattern already
  used by `metar/`, `taf/`, and `sigmet/` — see `CLAUDE.md` for the
  shape and the conventions each layer follows (coordinator error
  handling, device info, optional-vs-always-created entities).
- **Airport or FIR database changes**: never hand-edit
  `airports/countries/*.py`, `airports/registry.py`, or
  `airports/country_registry.py` — they're generated. See
  [`scripts/README.md`](scripts/README.md).
- **Translations**: `strings.json` is the source of truth for English;
  `translations/*.json` holds every other language, structured
  identically. `tests/test_translations.py` guards against missing or
  empty labels for continents, additional-entity options, and system
  health keys — add new selector options there if you introduce one.
- **New automation example in the README**: add a matching blueprint
  under `blueprints/automation/aviation_weather/` (entity selectors +
  a `notify` domain target, not hardcoded ICAO-based entity_ids) and
  link it from the README section.
- **New entity needing a per-state icon**: add it to `icons.json`
  keyed by `_attr_translation_key`, and don't also set a static
  `_attr_icon` on that entity — see `CLAUDE.md`.

## Submitting a pull request

1. Add or update tests for your change — this project aims for full
   coverage on new code, not just "it doesn't crash."
2. Run the full check list above; fix anything that fails.
3. Keep PRs focused — one feature or fix per PR is easier to review
   and release.
4. Add an entry describing the user-visible change to
   [`CHANGELOG.md`](CHANGELOG.md) (skip this for internal-only
   refactors with no behavior change) — under the current top version
   heading until that version has actually been released (see
   `RELEASING.md`), or under `## [Unreleased]` if it has.

## Releasing

Releasing is a maintainer task, not something contributors need to do —
see [`RELEASING.md`](RELEASING.md) if you are a maintainer preparing a
new version.

# Releasing a new version

This repository's release process is fully automated, triggered by a
single change: bumping the version number.

## How it works

1. **`custom_components/aviation_weather/manifest.json`** is the
   source of truth for the version. HACS reads the *Git tag* of your
   latest GitHub Release to determine what version is installable —
   not the manifest directly — so the `.github/workflows/release.yml`
   workflow exists to keep the two in sync automatically.
2. When you push a commit to `main` that changes `manifest.json`'s
   `version` field, the **Release** workflow:
   - Reads the new version (e.g. `0.2.0`)
   - Checks whether a tag `v0.2.0` already exists (skips if so — this
     makes the workflow safe to re-run or to trigger on unrelated
     `manifest.json` edits that don't change the version)
   - **Fails the build** if `pyproject.toml`'s `version` doesn't match
     `manifest.json`'s — this is what keeps `pip install -e .` working
     (see below) without you having to remember to update both files
     by hand
   - Builds a zip of `custom_components/aviation_weather/`
   - Creates the Git tag and a GitHub Release with that zip attached,
     with auto-generated release notes from merged PRs / commits since
     the last release

## Your actual workflow for a new release

1. Make your changes, get them merged to `main` as normal (CI runs on
   every PR regardless of version).
2. In a final commit (or PR), bump **both**:
   - `custom_components/aviation_weather/manifest.json` → `"version"`
   - `pyproject.toml` → `[project]` → `version`

   to the same new value, e.g. `0.2.0`. Follow [semantic
   versioning](https://semver.org/): `MAJOR.MINOR.PATCH` — patch for
   bug fixes, minor for new features, major for breaking changes.

   In the same commit, update [`CHANGELOG.md`](CHANGELOG.md):
   - **Before the first real release** (currently the case — nothing
     has been tagged yet): keep adding new entries directly under the
     current top heading (`## [1.0.0] - YYYY-MM-DD`, date-bumped to the
     day you actually release), rather than accumulating them in a
     separate `[Unreleased]` section. There's no released `1.0.0` to
     diff against yet, so there's nothing for `[Unreleased]` to usefully
     mean.
   - **After that first release exists**, switch to the normal
     Keep a Changelog flow: accumulate new changes under
     `## [Unreleased]` as you make them, then on the next release move
     that section's entries under a new `## [0.2.0] - YYYY-MM-DD`
     heading and add the corresponding compare/tag link at the bottom
     of the file.
3. Merge to `main`.
4. The Release workflow runs automatically. Check the **Actions** tab
   — within a minute or two you should see a new tag and release under
   **Releases** in the repo sidebar.
5. Done. HACS will pick up the new release on its next check
   (or immediately if a user manually checks for updates).

## Why pyproject.toml needs a version at all

`pyproject.toml`'s `version` has nothing to do with HACS or Home
Assistant — it's required by `setuptools` (the Python packaging
backend) for `pip install -e ".[dev]"` to work at all, which is what
your local dev environment and CI both rely on for running tests.
Without it, `pip install` fails outright with `project must contain
['version'] properties`.

The two version fields are kept in sync by convention and enforced by
the release workflow, not by any technical link between them — HA/HACS
never reads `pyproject.toml`, and `pip`/`setuptools` never read
`manifest.json`.

## Manual release (bypassing automation)

If you ever need to create a release without going through the
manifest-bump flow (e.g. re-releasing the same code with a
documentation-only tag), use the **Actions** tab → **Release** →
**Run workflow**. It reads whatever version is currently in
`manifest.json` and will skip if that version was already released.

#!/usr/bin/env bash
set -euo pipefail

# Runs the same HACS validation as .github/workflows/hacs.yml, locally,
# using the actual hacs/action Docker image — so manifest.json/hacs.json
# changes can be checked before pushing instead of waiting on CI.
#
# Requires: Docker, and a GitHub token with read access to this
# repository (a fine-grained PAT with Contents: read is enough; the
# same one used for `git push` works). Some checks (fetching
# hacs.json/manifest.json) go through raw.githubusercontent.com, which
# only serves PUBLIC repositories regardless of the token — if this
# repo is private, those specific checks will fail here exactly as
# they do in CI.
#
# Usage:
#   GITHUB_TOKEN=github_pat_xxx ./scripts/check_hacs.sh
#   ./scripts/check_hacs.sh                    # falls back to the
#                                               # token already stored
#                                               # in ~/.git-credentials
#   HACS_CATEGORY=integration ./scripts/check_hacs.sh   # default category

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CATEGORY="${HACS_CATEGORY:-integration}"

if [ -z "${GITHUB_TOKEN:-}" ]; then
  if [ -f "$HOME/.git-credentials" ] && grep -q "github.com" "$HOME/.git-credentials"; then
    GITHUB_TOKEN="$(grep "github.com" "$HOME/.git-credentials" | head -1 |
      sed -E 's#https://[^:]*:([^@]+)@github\.com.*#\1#')"
    echo "Using GitHub token from ~/.git-credentials" >&2
  else
    echo "Error: set GITHUB_TOKEN, or configure git credential storage" \
      "(~/.git-credentials) so one can be found automatically." >&2
    exit 1
  fi
fi

ORIGIN_URL="$(git -C "$REPO_ROOT" remote get-url origin)"
REPOSITORY="$(echo "$ORIGIN_URL" |
  sed -E 's#.*github\.com[:/]([^/]+/[^/.]+)(\.git)?$#\1#')"

echo "Repository: $REPOSITORY" >&2
echo "Category:   $CATEGORY" >&2

docker run --rm \
  -v "$REPO_ROOT":/github/workspace \
  -e GITHUB_WORKSPACE=/github/workspace \
  -e GITHUB_REPOSITORY="$REPOSITORY" \
  -e INPUT_CATEGORY="$CATEGORY" \
  -e INPUT_GITHUB_TOKEN="$GITHUB_TOKEN" \
  ghcr.io/hacs/action:main

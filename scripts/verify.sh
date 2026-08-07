#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"
export UV_CACHE_DIR="$REPO_ROOT/.uv-cache"
export COREPACK_HOME="$REPO_ROOT/.corepack"

uv run pytest apps/backend/tests/architecture -q
uv run ruff check .
uv run mypy apps/backend/src apps/backend/tests scripts
uv run pytest apps/backend/tests -q
python scripts/check_boundaries.py
corepack pnpm lint
corepack pnpm typecheck
corepack pnpm build

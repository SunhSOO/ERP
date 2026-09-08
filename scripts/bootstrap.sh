#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"
export UV_CACHE_DIR="$REPO_ROOT/.uv-cache"
export COREPACK_HOME="$REPO_ROOT/.corepack"

command -v uv >/dev/null || { echo "uv is required" >&2; exit 1; }
command -v corepack >/dev/null || { echo "Corepack is required" >&2; exit 1; }

uv sync
corepack pnpm install --frozen-lockfile
echo "Foundation dependencies are ready."

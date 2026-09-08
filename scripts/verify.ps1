$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot
$env:UV_CACHE_DIR = Join-Path $repoRoot ".uv-cache"
$env:COREPACK_HOME = Join-Path $repoRoot ".corepack"

function Invoke-Checked {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][scriptblock]$Command
    )
    Write-Host "== $Name =="
    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw "$Name failed with exit code $LASTEXITCODE"
    }
}

Invoke-Checked "backend architecture tests" { uv run pytest apps/backend/tests/architecture -q }
Invoke-Checked "Python lint" { uv run ruff check . }
Invoke-Checked "Python type check" { uv run mypy apps/backend/src apps/backend/tests scripts }
Invoke-Checked "backend unit tests" { uv run pytest apps/backend/tests -q }
Invoke-Checked "module boundary check" { python scripts/check_boundaries.py }
Invoke-Checked "frontend lint" { corepack pnpm lint }
Invoke-Checked "frontend type check" { corepack pnpm typecheck }
Invoke-Checked "frontend unit tests" { corepack pnpm test-unit }
Invoke-Checked "frontend build" { corepack pnpm build }

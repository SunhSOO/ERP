$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot
$env:UV_CACHE_DIR = Join-Path $repoRoot ".uv-cache"
$env:COREPACK_HOME = Join-Path $repoRoot ".corepack"

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    throw "uv is required"
}
if (-not (Get-Command corepack -ErrorAction SilentlyContinue)) {
    throw "Corepack is required"
}

uv sync
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
corepack pnpm install --frozen-lockfile
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "Foundation dependencies are ready."

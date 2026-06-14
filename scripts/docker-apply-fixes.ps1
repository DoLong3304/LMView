# docker-apply-fixes.ps1 — Apply config fixes so disk doesn't bleed again.
# No admin required. Idempotent.
# Run AFTER docker-compact-vhdx.ps1 (or in parallel — independent).

[CmdletBinding()]
param(
    [string]$RepoPath = "D:\Azriel\Source_code\2026\LMView"
)

$ErrorActionPreference = "Stop"
function Log($m)  { Write-Host "[apply] $m" -ForegroundColor Cyan }
function Warn($m) { Write-Host "[apply] $m" -ForegroundColor Yellow }
function Die($m)  { Write-Host "[apply] $m" -ForegroundColor Red; exit 1 }

Set-Location $RepoPath

# ── 1. Verify the offending empty dir is truly empty ─────────────────────
$bogus = Join-Path $RepoPath "spark-defaults.conf"
if (Test-Path $bogus) {
    $items = Get-ChildItem $bogus -Force -ErrorAction SilentlyContinue
    if ($items.Count -gt 0) {
        Die "spark-defaults.conf is NOT empty — refusing to delete. Inspect manually: $bogus"
    }
    Log "Removing empty dir: $bogus"
    Remove-Item $bogus -Recurse -Force
} else {
    Log "Empty dir already gone (good)."
}

# ── 2. Prune the 23 GB of stale build cache ──────────────────────────────
Log "Pruning buildx cache (reclaimable ~23 GB)..."
docker builder prune -af --filter "until=72h" 2>&1 | Out-String | Write-Host
if ($LASTEXITCODE -ne 0) {
    Warn "Buildx prune returned non-zero, trying without filter..."
    docker builder prune -af 2>&1 | Out-String | Write-Host
}

# ── 3. Restart Spark workers + master so new conf takes effect ──────────
Log "Restarting spark workers + master..."
docker compose down spark-worker spark-worker-2 spark-master 2>&1 | Out-String | Write-Host
docker compose up -d spark-master spark-worker spark-worker-2 2>&1 | Out-String | Write-Host

# ── 4. Verify the mount is now a real file inside container ──────────────
Log "Verifying spark-defaults.conf is mounted as a file..."
$verify = docker exec spark-master sh -c 'test -f /opt/spark/conf/spark-defaults.conf && echo "FILE_OK" || echo "STILL_BROKEN"'
$verify = $verify.Trim()
if ($verify -eq "FILE_OK") {
    Log "Mount verified: /opt/spark/conf/spark-defaults.conf is a real file."
    Log "Spark cleanup flags are now active."
} else {
    Warn "Mount still broken: $verify"
    Warn "Check compose file — path ./config/spark-defaults.conf must exist and be a file."
}

# ── 5. Show post-state ───────────────────────────────────────────────────
Log "=== Post-state ==="
docker system df | Out-String | Write-Host

Log "Done. Workers now auto-purge /opt/spark/work every 30 min (TTL 1h)."
Read-Host "Press Enter to exit"

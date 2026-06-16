# docker-scheduled-reclaim.ps1 — Weekly automatic reclaim + compact.
# Register with Task Scheduler:
#
#   Register-ScheduledTask -TaskName "Docker Weekly Reclaim" `
#     -Action (New-ScheduledTaskAction -Execute "powershell.exe" `
#         -Argument "-NoProfile -ExecutionPolicy Bypass -File C:\path\to\docker-scheduled-reclaim.ps1") `
#     -Trigger (New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At 3am) `
#     -RunLevel Highest -User "SYSTEM"
#
# Or use the companion docker-scheduled-reclaim-register.ps1.

[CmdletBinding()]
param(
    [string]$RepoPath       = "D:\Azriel\Source_code\2026\LMView",
    [string]$VHDXPath       = "D:\Docker\DockerDesktopWSL\disk\docker_data.vhdx",
    [string]$DistroVHDX     = "$env:USERPROFILE\AppData\Local\wsl\{9e2ac8f9-3499-42fe-b4f4-eb7ed2890a88}\ext4.vhdx",
    [int]   $ThresholdGB    = 100,           # skip compact if VHDX under this
    [switch]$SkipCompact
)

$ErrorActionPreference = "Stop"
$logFile = Join-Path $RepoPath "logs\docker-reclaim-$(Get-Date -Format 'yyyyMMdd-HHmm').log"
New-Item -ItemType Directory -Force -Path (Split-Path $logFile) | Out-Null

function Log($m) {
    $line = "[$(Get-Date -Format 'o')] $m"
    Write-Host $line -ForegroundColor Cyan
    Add-Content -Path $logFile -Value $line
}

# ── 1. WSL-side reclaim ───────────────────────────────────────────────────
Log "Launching WSL reclaim script..."
$wslScript = Join-Path $RepoPath "scripts\docker-reclaim.sh"
wsl -d Ubuntu -- bash -c "cd '$($RepoPath -replace '\\','/')' && bash ./scripts/docker-reclaim.sh 2>&1" |
    ForEach-Object { Log "WSL: $_" }

# ── 2. VHDX compact (only if oversized) ──────────────────────────────────
if ($SkipCompact) { Log "SkipCompact flag set, done."; return }

if (Test-Path $VHDXPath) {
    $sizeGB = [math]::Round((Get-Item $VHDXPath).Length / 1GB, 2)
    Log "Current $VHDXPath = $sizeGB GB (threshold = $ThresholdGB GB)"
    if ($sizeGB -ge $ThresholdGB) {
        Log "Compacting VHDX..."
        & "$PSScriptRoot\docker-compact-vhdx.ps1" -VHDXPath $VHDXPath -DistroVHDX $DistroVHDX |
            ForEach-Object { Log "Compact: $_" }
    } else {
        Log "VHDX under threshold, skipping compact."
    }
}

# ── 3. Garbage-collect old logs (keep 8 weeks) ────────────────────────────
Get-ChildItem (Join-Path $RepoPath "logs") -Filter "docker-reclaim-*.log" |
    Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-56) } |
    ForEach-Object {
        Log "Pruning old log: $($_.Name)"
        Remove-Item $_.FullName -Force
    }

Log "Weekly reclaim complete."

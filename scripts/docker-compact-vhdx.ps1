# docker-compact-vhdx.ps1 — Shrink Docker WSL2 VHDX after in-container cleanup.
# Reclaiming disk INSIDE the container does NOT shrink the host VHDX.
# You MUST compact the VHDX from Windows to actually free host disk.
#
# This script self-elevates via UAC. Just run it — a consent dialog appears.

[CmdletBinding()]
param(
    [string]$VHDXPath   = "D:\Docker\DockerDesktopWSL\disk\docker_data.vhdx",
    [string]$DistroVHDX = "$env:USERPROFILE\AppData\Local\wsl\{9e2ac8f9-3499-42fe-b4f4-eb7ed2890a88}\ext4.vhdx"
)

$ErrorActionPreference = "Stop"
function Log($m) { Write-Host "[compact] $m" -ForegroundColor Cyan }
function Warn($m) { Write-Host "[compact] $m" -ForegroundColor Yellow }
function Die($m)  { Write-Host "[compact] $m" -ForegroundColor Red; exit 1 }

# ── Self-elevate to admin if not already ──────────────────────────────────
$id = [System.Security.Principal.WindowsIdentity]::GetCurrent()
$pr = New-Object System.Security.Principal.WindowsPrincipal($id)
if (-not $pr.IsInRole([System.Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Log "Not elevated — relaunching with UAC prompt. Click YES."
    $arg = "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`""
    if ($PSBoundParameters.Count -gt 0) {
        $arg += " " + (($PSBoundParameters.GetEnumerator() | ForEach-Object { "-$($_.Key) `"$($_.Value)`"" }) -join " ")
    }
    Start-Process powershell -Verb RunAs -ArgumentList $arg
    return
}

# ── Pre-flight ────────────────────────────────────────────────────────────
foreach ($p in @($VHDXPath, $DistroVHDX)) {
    if (Test-Path $p) {
        $size = (Get-Item $p).Length
        Log "Before: $p = $([math]::Round($size/1GB,2)) GB"
    } else {
        Warn "Not found, skipping: $p"
    }
}

# Optional Hyper-V check (works now that we're elevated)
$haveOptimizeVhd = $false
try {
    $cmd = Get-Command Optimize-VHD -ErrorAction Stop
    $haveOptimizeVhd = $true
    Log "Hyper-V cmdlet available: Optimize-VHD"
} catch {
    Warn "Optimize-VHD cmdlet not available. Will use diskpart fallback."
}

# ── Stop WSL so VHDX is not in use ────────────────────────────────────────
Log "Stopping WSL..."
wsl --shutdown
Start-Sleep -Seconds 3

# ── Compact each VHDX ──────────────────────────────────────────────────────
function Compact-VHDX {
    param([string]$Path)
    if (-not (Test-Path $Path)) { Warn "Skip (missing): $Path"; return }
    $before = (Get-Item $Path).Length

    $ok = $false
    if ($haveOptimizeVhd) {
        try {
            Log "Optimize-VHD -Mode Full on $Path"
            Optimize-VHD -Path $Path -Mode Full -ErrorAction Stop
            $ok = $true
        } catch {
            Warn "Optimize-VHD failed: $($_.Exception.Message). Trying diskpart."
        }
    }

    if (-not $ok) {
        # diskpart can `compact vdisk` even without Hyper-V module
        $tmp = Join-Path $env:TEMP "compact_$(Get-Random).txt"
        @"
select vdisk file="$Path"
compact vdisk
"@ | Set-Content $tmp -Encoding ASCII
        Log "diskpart compact vdisk on $Path"
        $out = diskpart /s $tmp 2>&1
        $out | ForEach-Object { Write-Host "  $_" }
        Remove-Item $tmp -Force -ErrorAction SilentlyContinue
        if ($LASTEXITCODE -eq 0) { $ok = $true }
    }

    Start-Sleep -Seconds 1
    $after = (Get-Item $Path).Length
    $saved = $before - $after
    if ($saved -gt 0) {
        Log "After : $Path = $([math]::Round($after/1GB,2)) GB  (saved $([math]::Round($saved/1GB,2)) GB)"
    } else {
        Warn "After : $Path = $([math]::Round($after/1GB,2)) GB  (no change — file may already be compact)"
    }
}

Compact-VHDX -Path $VHDXPath
Compact-VHDX -Path $DistroVHDX

# ── Restart WSL ───────────────────────────────────────────────────────────
Log "Restarting docker-desktop..."
wsl -d docker-desktop -- echo "ok" 2>$null
wsl -d Ubuntu -- echo "ok" 2>$null

Log "Done. Confirm with: wsl -d Ubuntu -- docker system df"
Read-Host "Press Enter to exit"

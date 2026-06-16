# docker-scheduled-reclaim-register.ps1 — One-time Task Scheduler registration.
# Run elevated.

[CmdletBinding()]
param(
    [string]$RepoPath = "D:\Azriel\Source_code\2026\LMView"
)

$ErrorActionPreference = "Stop"
$taskName = "Docker Weekly Reclaim"
$script   = Join-Path $RepoPath "scripts\docker-scheduled-reclaim.ps1"

if (-not (Test-Path $script)) { throw "Script not found: $script" }

# Remove existing
Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue

$action  = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$script`"" `
    -WorkingDirectory $RepoPath

$trigger = New-ScheduledTaskTrigger `
    -Weekly `
    -DaysOfWeek Sunday `
    -At 3am

$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -DontStopOnIdleEnd `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2)

Register-ScheduledTask `
    -TaskName $taskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -RunLevel Highest `
    -User "SYSTEM" `
    -Description "Weekly Docker reclaim + WSL2 VHDX compact for cryptoprice stack."

Write-Host "Registered: $taskName" -ForegroundColor Green
Write-Host "Run now:    Start-ScheduledTask -TaskName '$taskName'" -ForegroundColor Green

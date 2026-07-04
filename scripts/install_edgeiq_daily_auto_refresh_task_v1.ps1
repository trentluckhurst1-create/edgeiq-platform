[CmdletBinding()]
param(
    [string]$ProjectRoot = "",
    [string]$TaskName = "EDGEIQ_DAILY_AUTO_REFRESH_V1",
    [string]$RunAt = "05:00",
    [switch]$RunNow
)

$ErrorActionPreference = "Stop"

function Resolve-InstallProjectRoot {
    param([string]$CandidateRoot)

    if (![string]::IsNullOrWhiteSpace($CandidateRoot)) {
        if (!(Test-Path $CandidateRoot)) {
            throw "Project root does not exist: $CandidateRoot"
        }
        return (Resolve-Path $CandidateRoot).Path
    }

    $defaultRoot = Split-Path -Parent $PSScriptRoot
    if ((Test-Path (Join-Path $defaultRoot "scripts")) -and (Test-Path (Join-Path $defaultRoot "public"))) {
        return (Resolve-Path $defaultRoot).Path
    }

    throw "Unable to resolve project root."
}

function Parse-RunAtTime {
    param([string]$Value)

    try {
        return [datetime]::ParseExact($Value, "HH:mm", $null)
    } catch {
        throw "RunAt must be in HH:mm format. Received: $Value"
    }
}

$resolvedRoot = Resolve-InstallProjectRoot -CandidateRoot $ProjectRoot
$scriptPath = Join-Path $resolvedRoot "scripts\run_edgeiq_daily_auto_refresh_v1.ps1"

if (!(Test-Path $scriptPath -PathType Leaf)) {
    throw "Daily auto refresh script not found: $scriptPath"
}

$runTime = Parse-RunAtTime -Value $RunAt
$userId = "$env:USERDOMAIN\$env:USERNAME"
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$scriptPath`"" -WorkingDirectory $resolvedRoot
$trigger = New-ScheduledTaskTrigger -Daily -At $runTime
$principal = New-ScheduledTaskPrincipal -UserId $userId -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -MultipleInstances IgnoreNew
$description = "EDGEiQ daily auto refresh. Rebuilds calendar, universe, live card, intelligence, DNA, and freshness audit each morning."

if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Description $description | Out-Null

Write-Host "[EDGEIQ_DAILY_AUTO_REFRESH_TASK_V1] INSTALLED"
Write-Host "task_name=$TaskName"
Write-Host "run_at=$RunAt"
Write-Host "script=$scriptPath"
Write-Host "working_directory=$resolvedRoot"
Write-Host "user=$userId"

if ($RunNow) {
    Start-ScheduledTask -TaskName $TaskName
    Write-Host "run_now=YES"
} else {
    Write-Host "run_now=NO"
}

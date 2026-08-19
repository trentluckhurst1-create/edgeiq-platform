[CmdletBinding()]
param(
    [string]$ProjectRoot = "",
    [string]$TaskName = "EDGEIQ_BUILD_TOMORROW_V1",
    [string]$LogsFolderRelativePath = "logs"
)

$ErrorActionPreference = "Stop"

$resolvedProjectRoot = if ([string]::IsNullOrWhiteSpace($ProjectRoot)) {
    Split-Path -Parent $PSScriptRoot
} else {
    $ProjectRoot
}

. (Join-Path $PSScriptRoot "edgeiq_logger_v1.ps1")
. (Join-Path $PSScriptRoot "edgeiq_lock_manager_v1.ps1")
. (Join-Path $PSScriptRoot "edgeiq_preflight_v1.ps1")

function Invoke-EdgeIQPythonStep {
    param(
        [psobject]$LogContext,
        [string]$ResolvedProjectRoot,
        [string]$Label,
        [string]$ScriptRelativePath
    )

    $scriptPath = Join-Path $ResolvedProjectRoot $ScriptRelativePath
    if (!(Test-Path $scriptPath -PathType Leaf)) {
        throw "Missing script: $scriptPath"
    }

    Write-EdgeIQLog -Context $LogContext -Level "INFO" -Message ("{0} -> {1}" -f $Label, $ScriptRelativePath) | Out-Null
    $output = & python $scriptPath 2>&1
    $exitCode = $LASTEXITCODE
    foreach ($line in $output) {
        $text = ([string]$line).TrimEnd()
        if (![string]::IsNullOrWhiteSpace($text)) {
            Write-EdgeIQLog -Context $LogContext -Level "INFO" -Message $text | Out-Null
        }
    }
    if ($exitCode -ne 0) {
        throw "Python step failed: $ScriptRelativePath"
    }
}

$logContext = New-EdgeIQLogContext -ProjectRoot $resolvedProjectRoot -TaskName $TaskName -LogsFolderRelativePath $LogsFolderRelativePath
$lockContext = $null

try {
    Write-EdgeIQLogSeparator -Context $logContext | Out-Null
    Write-EdgeIQLog -Context $logContext -Level "INFO" -Message "Tomorrow universe wrapper starting." | Out-Null

    $preflight = Invoke-EdgeIQPreflight -ProjectRoot $resolvedProjectRoot -RequiredCsvPaths @("public\data\edgeiq_racingcom_historical_calendar_backfill_v1.csv") -LogsFolderRelativePath $LogsFolderRelativePath
    Write-EdgeIQLog -Context $logContext -Level "INFO" -Message ("Preflight passed. Python={0} LogsDirectory={1}" -f $preflight.PythonVersion, $preflight.LogsDirectory) | Out-Null

    $lockContext = Acquire-EdgeIQLock -ProjectRoot $resolvedProjectRoot -LockName $TaskName -LogsFolderRelativePath $LogsFolderRelativePath
    Write-EdgeIQLog -Context $logContext -Level "INFO" -Message ("Lock acquired: {0}" -f $lockContext.LockPath) | Out-Null

    Set-Location $resolvedProjectRoot
    Invoke-EdgeIQPythonStep -LogContext $logContext -ResolvedProjectRoot $resolvedProjectRoot -Label "23:00 build calendar" -ScriptRelativePath "scripts\build_edgeiq_vic_three_day_meeting_calendar_v1.py"
    Invoke-EdgeIQPythonStep -LogContext $logContext -ResolvedProjectRoot $resolvedProjectRoot -Label "23:01 build universe" -ScriptRelativePath "scripts\build_edgeiq_vic_three_day_meeting_universe.py"
    Invoke-EdgeIQPythonStep -LogContext $logContext -ResolvedProjectRoot $resolvedProjectRoot -Label "23:02 rollover audit" -ScriptRelativePath "scripts\build_edgeiq_date_rollover_audit_v1.py"

    Write-EdgeIQLog -Context $logContext -Level "INFO" -Message "Tomorrow universe wrapper completed successfully." | Out-Null
    Write-Host "[EDGEIQ_BUILD_TOMORROW_V1] COMPLETE"
    Write-Host "task_name=$TaskName"
    Write-Host "log_path=$($logContext.LogPath)"
    Write-Host "lock_path=$($lockContext.LockPath)"
    exit 0
} catch {
    Write-EdgeIQLog -Context $logContext -Level "ERROR" -Message $_.Exception.Message | Out-Null
    Write-Host "[EDGEIQ_BUILD_TOMORROW_V1] FAILED"
    Write-Host "task_name=$TaskName"
    Write-Host "log_path=$($logContext.LogPath)"
    if ($lockContext) {
        Write-Host "lock_path=$($lockContext.LockPath)"
    }
    exit 1
} finally {
    if ($lockContext) {
        try {
            $releaseResult = Release-EdgeIQLock -ProjectRoot $resolvedProjectRoot -LockName $TaskName -LogsFolderRelativePath $LogsFolderRelativePath
            Write-EdgeIQLog -Context $logContext -Level "INFO" -Message ("Lock release status: {0}" -f $releaseResult.Status) | Out-Null
        } catch {
            Write-EdgeIQLog -Context $logContext -Level "ERROR" -Message ("Lock release failed: {0}" -f $_.Exception.Message) | Out-Null
        }
    }
}

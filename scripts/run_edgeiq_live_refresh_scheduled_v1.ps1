[CmdletBinding()]
param(
    [string]$ProjectRoot = "",
    [string]$TaskName = "EDGEIQ_LIVE_REFRESH_SCHEDULED_V1",
    [string]$LiveRefreshScriptRelativePath = "scripts\run_edgeiq_today_tab_only_dashboard_refresh_v1.ps1",
    [string]$LogsFolderRelativePath = "logs",
    [string[]]$RequiredCsvPaths = @(
        "public\data\race_card_report.csv",
        "public\data\edgeiq_live_runner_board_v1.csv",
        "public\data\edgeiq_active_race_selector.csv"
    )
)

$ErrorActionPreference = "Stop"

$resolvedProjectRoot = if ([string]::IsNullOrWhiteSpace($ProjectRoot)) {
    Split-Path -Parent $PSScriptRoot
} else {
    $ProjectRoot
}

$sourceInventoryAuditPath = Join-Path $resolvedProjectRoot "public\data\edgeiq_current_day_source_inventory_audit_v1.csv"
$sourceInventorySummaryPath = Join-Path $resolvedProjectRoot "public\data\edgeiq_current_day_source_inventory_summary_v1.csv"

. (Join-Path $PSScriptRoot "edgeiq_logger_v1.ps1")
. (Join-Path $PSScriptRoot "edgeiq_lock_manager_v1.ps1")
. (Join-Path $PSScriptRoot "edgeiq_preflight_v1.ps1")

$logContext = New-EdgeIQLogContext -ProjectRoot $resolvedProjectRoot -TaskName $TaskName -LogsFolderRelativePath $LogsFolderRelativePath
$lockContext = $null

try {
    Write-EdgeIQLogSeparator -Context $logContext | Out-Null
    Write-EdgeIQLog -Context $logContext -Level "INFO" -Message "Scheduled live refresh wrapper starting." | Out-Null

    $preflight = Invoke-EdgeIQPreflight -ProjectRoot $resolvedProjectRoot -RequiredCsvPaths $RequiredCsvPaths -LogsFolderRelativePath $LogsFolderRelativePath
    Write-EdgeIQLog -Context $logContext -Level "INFO" -Message ("Preflight passed. Python={0} LogsDirectory={1}" -f $preflight.PythonVersion, $preflight.LogsDirectory) | Out-Null

    $lockContext = Acquire-EdgeIQLock -ProjectRoot $resolvedProjectRoot -LockName $TaskName -LogsFolderRelativePath $LogsFolderRelativePath
    Write-EdgeIQLog -Context $logContext -Level "INFO" -Message ("Lock acquired: {0}" -f $lockContext.LockPath) | Out-Null

    $liveRefreshScript = if ([System.IO.Path]::IsPathRooted($LiveRefreshScriptRelativePath)) {
        $LiveRefreshScriptRelativePath
    } else {
        Join-Path $resolvedProjectRoot $LiveRefreshScriptRelativePath
    }

    if (!(Test-Path $liveRefreshScript -PathType Leaf)) {
        throw "Live refresh script not found: $liveRefreshScript"
    }

    Write-EdgeIQLog -Context $logContext -Level "INFO" -Message ("Executing live refresh chain: {0}" -f $liveRefreshScript) | Out-Null

    Set-Location $resolvedProjectRoot
    $previousErrorActionPreference = $ErrorActionPreference
    $nativeErrorPreferenceVariable = Get-Variable -Name PSNativeCommandUseErrorActionPreference -ErrorAction SilentlyContinue
    $previousNativeCommandPreference = $null
    try {
        $ErrorActionPreference = "Continue"
        if ($nativeErrorPreferenceVariable) {
            $previousNativeCommandPreference = $PSNativeCommandUseErrorActionPreference
            $PSNativeCommandUseErrorActionPreference = $false
        }
        $refreshOutput = & powershell -NoProfile -ExecutionPolicy Bypass -File $liveRefreshScript 2>&1
        $refreshExitCode = $LASTEXITCODE
    } finally {
        if ($nativeErrorPreferenceVariable) {
            $PSNativeCommandUseErrorActionPreference = $previousNativeCommandPreference
        }
        $ErrorActionPreference = $previousErrorActionPreference
    }

    foreach ($line in $refreshOutput) {
        $text = ([string]$line).TrimEnd()
        if (![string]::IsNullOrWhiteSpace($text)) {
            Write-EdgeIQLog -Context $logContext -Level "INFO" -Message $text | Out-Null
        }
    }

    if ($refreshExitCode -ne 0) {
        if (Test-Path $sourceInventorySummaryPath) {
            try {
                $inventorySummary = Import-Csv $sourceInventorySummaryPath | Select-Object -First 1
                if ($inventorySummary) {
                    Write-EdgeIQLog -Context $logContext -Level "ERROR" -Message (
                        "Current-day source audit status={0} selected_meeting={1} files_with_today_rows={2} files_with_selected_meeting_rows={3} best_scrape_source={4} best_terminal_source={5}" -f
                        $inventorySummary.status,
                        $inventorySummary.selected_meeting,
                        $inventorySummary.files_with_today_rows,
                        $inventorySummary.files_with_selected_meeting_rows,
                        $inventorySummary.best_scrape_inventory_source,
                        $inventorySummary.best_terminal_inventory_source
                    ) | Out-Null
                }
            } catch {
                Write-EdgeIQLog -Context $logContext -Level "ERROR" -Message ("Failed reading source inventory summary: {0}" -f $_.Exception.Message) | Out-Null
            }
        }

        if (Test-Path $sourceInventoryAuditPath) {
            try {
                $inventoryAuditRows = Import-Csv $sourceInventoryAuditPath
                foreach ($row in $inventoryAuditRows) {
                    Write-EdgeIQLog -Context $logContext -Level "ERROR" -Message (
                        "Source inventory row file={0} freshness={1} max_date={2} today_rows={3} selected_meeting_rows={4}" -f
                        $row.file_name,
                        $row.freshness_status,
                        $row.max_race_date,
                        $row.today_row_count,
                        $row.selected_meeting_row_count
                    ) | Out-Null
                }
            } catch {
                Write-EdgeIQLog -Context $logContext -Level "ERROR" -Message ("Failed reading source inventory audit: {0}" -f $_.Exception.Message) | Out-Null
            }
        }

        throw "Live refresh chain returned exit code $refreshExitCode."
    }

    Write-EdgeIQLog -Context $logContext -Level "INFO" -Message "Scheduled live refresh wrapper completed successfully." | Out-Null
    Write-Host "[EDGEIQ_LIVE_REFRESH_SCHEDULED_V1] COMPLETE"
    Write-Host "task_name=$TaskName"
    Write-Host "log_path=$($logContext.LogPath)"
    Write-Host "lock_path=$($lockContext.LockPath)"
    exit 0
} catch {
    Write-EdgeIQLog -Context $logContext -Level "ERROR" -Message $_.Exception.Message | Out-Null
    Write-Host "[EDGEIQ_LIVE_REFRESH_SCHEDULED_V1] FAILED"
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

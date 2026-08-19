[CmdletBinding()]
param(
    [string]$ProjectRoot = "",
    [string]$TaskName = "EDGEIQ_MIDNIGHT_PROMOTION_V1",
    [string]$LogsFolderRelativePath = "logs"
)

$ErrorActionPreference = "Stop"

$resolvedProjectRoot = if ([string]::IsNullOrWhiteSpace($ProjectRoot)) {
    Split-Path -Parent $PSScriptRoot
} else {
    $ProjectRoot
}

$sourceInventorySummaryPath = Join-Path $resolvedProjectRoot "public\data\edgeiq_current_day_source_inventory_summary_v1.csv"
$meetingDiagnosticsPath = Join-Path $resolvedProjectRoot "public\data\edgeiq_vic_three_day_meeting_diagnostics.csv"
$rolloverAuditPath = Join-Path $resolvedProjectRoot "public\data\edgeiq_date_rollover_audit_v1.csv"
$backupRoot = Join-Path (Join-Path $resolvedProjectRoot $LogsFolderRelativePath) "rollover_backups"

$dashboardFiles = @(
    "public\data\edgeiq_live_terminal_feed_v1_TAB_ONLY_TODAY.csv",
    "public\data\edgeiq_vic_live_terminal_feed_v1.csv",
    "public\data\edgeiq_live_terminal_feed_v1.csv",
    "public\data\edgeiq_live_runner_board_v1.csv",
    "public\data\edgeiq_active_race_selector.csv",
    "public\data\edgeiq_model_tracking_dashboard_v1.csv",
    "public\data\edgeiq_live_runner_style_v1.csv",
    "public\data\edgeiq_live_track_intelligence_v1.csv",
    "public\data\edgeiq_track_intelligence_card_v1.csv",
    "public\data\edgeiq_real_speed_map_positions.csv",
    "public\data\edgeiq_runner_intelligence_v1.csv",
    "public\data\edgeiq_race_intelligence_cards_v1.csv",
    "public\data\edgeiq_race_briefing_v1.csv",
    "public\data\edgeiq_race_verdict_v1.csv",
    "public\data\edgeiq_market_intelligence_v1.csv",
    "public\data\edgeiq_horse_intelligence_drawer_v1.csv"
)

. (Join-Path $PSScriptRoot "edgeiq_logger_v1.ps1")
. (Join-Path $PSScriptRoot "edgeiq_lock_manager_v1.ps1")
. (Join-Path $PSScriptRoot "edgeiq_preflight_v1.ps1")

function Invoke-EdgeIQPythonStep {
    param(
        [psobject]$LogContext,
        [string]$ResolvedProjectRoot,
        [string]$Label,
        [string]$ScriptRelativePath,
        [string[]]$Arguments = @()
    )

    $scriptPath = Join-Path $ResolvedProjectRoot $ScriptRelativePath
    if (!(Test-Path $scriptPath -PathType Leaf)) {
        throw "Missing script: $scriptPath"
    }

    Write-EdgeIQLog -Context $LogContext -Level "INFO" -Message ("{0} -> {1} {2}" -f $Label, $ScriptRelativePath, ($Arguments -join " ")) | Out-Null
    $command = @($scriptPath) + $Arguments
    $output = & python @command 2>&1
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

function Invoke-EdgeIQPowerShellStep {
    param(
        [psobject]$LogContext,
        [string]$ResolvedProjectRoot,
        [string]$Label,
        [string]$ScriptRelativePath
    )

    $scriptPath = Join-Path $ResolvedProjectRoot $ScriptRelativePath
    if (!(Test-Path $scriptPath -PathType Leaf)) {
        throw "Missing PowerShell script: $scriptPath"
    }

    Write-EdgeIQLog -Context $LogContext -Level "INFO" -Message ("{0} -> {1}" -f $Label, $ScriptRelativePath) | Out-Null
    $output = & powershell -NoProfile -ExecutionPolicy Bypass -File $scriptPath 2>&1
    $exitCode = $LASTEXITCODE
    foreach ($line in $output) {
        $text = ([string]$line).TrimEnd()
        if (![string]::IsNullOrWhiteSpace($text)) {
            Write-EdgeIQLog -Context $LogContext -Level "INFO" -Message $text | Out-Null
        }
    }
    if ($exitCode -ne 0) {
        throw "PowerShell step failed: $ScriptRelativePath"
    }
}

function New-EdgeIQDashboardBackupManifest {
    param(
        [string]$ResolvedProjectRoot,
        [string]$BackupRootPath,
        [string[]]$RelativePaths
    )

    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $runBackupRoot = Join-Path $BackupRootPath $timestamp
    if (!(Test-Path $runBackupRoot)) {
        New-Item -ItemType Directory -Path $runBackupRoot -Force | Out-Null
    }

    $manifest = New-Object System.Collections.Generic.List[object]
    foreach ($relativePath in $RelativePaths) {
        $targetPath = Join-Path $ResolvedProjectRoot $relativePath
        $safeRelativePath = $relativePath -replace "[:]", "" -replace "/", "\"
        $backupPath = Join-Path $runBackupRoot $safeRelativePath
        $backupDirectory = Split-Path -Parent $backupPath
        if (!(Test-Path $backupDirectory)) {
            New-Item -ItemType Directory -Path $backupDirectory -Force | Out-Null
        }

        $existsBefore = Test-Path $targetPath -PathType Leaf
        if ($existsBefore) {
            Copy-Item $targetPath $backupPath -Force
        }

        $manifest.Add([PSCustomObject]@{
            RelativePath = $relativePath
            TargetPath = $targetPath
            BackupPath = $backupPath
            ExistsBefore = $existsBefore
        }) | Out-Null
    }

    return [PSCustomObject]@{
        BackupRoot = $runBackupRoot
        Items = $manifest.ToArray()
    }
}

function Restore-EdgeIQDashboardBackupManifest {
    param(
        [psobject]$BackupManifest
    )

    foreach ($item in $BackupManifest.Items) {
        $targetDirectory = Split-Path -Parent $item.TargetPath
        if (!(Test-Path $targetDirectory)) {
            New-Item -ItemType Directory -Path $targetDirectory -Force | Out-Null
        }

        if ($item.ExistsBefore -and (Test-Path $item.BackupPath -PathType Leaf)) {
            Copy-Item $item.BackupPath $item.TargetPath -Force
            continue
        }

        if ((!$item.ExistsBefore) -and (Test-Path $item.TargetPath -PathType Leaf)) {
            Remove-Item $item.TargetPath -Force
        }
    }
}

function Get-EdgeIQCurrentDaySourceSummary {
    param([string]$SummaryPath)

    if (!(Test-Path $SummaryPath -PathType Leaf)) {
        return $null
    }

    $rows = @(Import-Csv $SummaryPath)
    if ($rows.Count -eq 0) {
        return $null
    }

    return $rows[0]
}

function Get-EdgeIQTodayMeetingDiagnostic {
    param([string]$DiagnosticsPath)

    if (!(Test-Path $DiagnosticsPath -PathType Leaf)) {
        return $null
    }

    $rows = @(Import-Csv $DiagnosticsPath | Where-Object { $_.record_type -eq "MEETING" -and $_.day_bucket -eq "TODAY" })
    if ($rows.Count -eq 0) {
        return $null
    }

    return $rows[0]
}

function Get-EdgeIQLastRolloverAuditRow {
    param([string]$AuditPath)

    if (!(Test-Path $AuditPath -PathType Leaf)) {
        return $null
    }

    $rows = @(Import-Csv $AuditPath)
    if ($rows.Count -eq 0) {
        return $null
    }

    return $rows[-1]
}

$logContext = New-EdgeIQLogContext -ProjectRoot $resolvedProjectRoot -TaskName $TaskName -LogsFolderRelativePath $LogsFolderRelativePath
$lockContext = $null
$backupManifest = $null
$dashboardMutationStarted = $false

try {
    Write-EdgeIQLogSeparator -Context $logContext | Out-Null
    Write-EdgeIQLog -Context $logContext -Level "INFO" -Message "Midnight promotion chain starting." | Out-Null

    $preflight = Invoke-EdgeIQPreflight -ProjectRoot $resolvedProjectRoot -RequiredCsvPaths @("public\data\edgeiq_racingcom_historical_calendar_backfill_v1.csv") -LogsFolderRelativePath $LogsFolderRelativePath
    Write-EdgeIQLog -Context $logContext -Level "INFO" -Message ("Preflight passed. Python={0} LogsDirectory={1}" -f $preflight.PythonVersion, $preflight.LogsDirectory) | Out-Null

    $lockContext = Acquire-EdgeIQLock -ProjectRoot $resolvedProjectRoot -LockName $TaskName -LogsFolderRelativePath $LogsFolderRelativePath
    Write-EdgeIQLog -Context $logContext -Level "INFO" -Message ("Lock acquired: {0}" -f $lockContext.LockPath) | Out-Null

    $backupManifest = New-EdgeIQDashboardBackupManifest -ResolvedProjectRoot $resolvedProjectRoot -BackupRootPath $backupRoot -RelativePaths $dashboardFiles
    Write-EdgeIQLog -Context $logContext -Level "INFO" -Message ("Dashboard state checkpointed to {0}" -f $backupManifest.BackupRoot) | Out-Null

    Set-Location $resolvedProjectRoot

    Invoke-EdgeIQPythonStep -LogContext $logContext -ResolvedProjectRoot $resolvedProjectRoot -Label "23:55 refresh calendar" -ScriptRelativePath "scripts\build_edgeiq_vic_three_day_meeting_calendar_v1.py"
    Invoke-EdgeIQPythonStep -LogContext $logContext -ResolvedProjectRoot $resolvedProjectRoot -Label "00:00 rebuild meeting calendar" -ScriptRelativePath "scripts\build_edgeiq_vic_three_day_meeting_calendar_v1.py"
    Invoke-EdgeIQPythonStep -LogContext $logContext -ResolvedProjectRoot $resolvedProjectRoot -Label "00:01 rebuild three-day universe" -ScriptRelativePath "scripts\build_edgeiq_vic_three_day_meeting_universe.py"
    Invoke-EdgeIQPythonStep -LogContext $logContext -ResolvedProjectRoot $resolvedProjectRoot -Label "00:01 source inventory audit" -ScriptRelativePath "scripts\audit_edgeiq_current_day_source_inventory_v1.py"

    $sourceSummary = Get-EdgeIQCurrentDaySourceSummary -SummaryPath $sourceInventorySummaryPath
    if ($null -eq $sourceSummary) {
        throw "Midnight promotion chain could not read current-day source inventory summary."
    }

    $todayMeeting = ([string]$sourceSummary.selected_meeting).Trim().ToUpper()
    if ([string]::IsNullOrWhiteSpace($todayMeeting)) {
        throw "Midnight promotion chain resolved a blank today meeting."
    }

    $todayMeetingDiag = Get-EdgeIQTodayMeetingDiagnostic -DiagnosticsPath $meetingDiagnosticsPath
    if ($null -ne $todayMeetingDiag) {
        Write-EdgeIQLog -Context $logContext -Level "INFO" -Message (
            "Today meeting promoted to {0}. status={1} dashboard_ready={2} field_rows={3} field_races={4}" -f
            $todayMeeting,
            $todayMeetingDiag.meeting_status,
            $todayMeetingDiag.dashboard_ready,
            $todayMeetingDiag.field_rows,
            $todayMeetingDiag.field_races
        ) | Out-Null
    } else {
        Write-EdgeIQLog -Context $logContext -Level "WARN" -Message ("Today meeting promoted to {0}, but meeting diagnostics row was unavailable." -f $todayMeeting) | Out-Null
    }

    $currentDaySourceReady = ([string]$sourceSummary.status).Trim().ToUpper() -eq "CURRENT_DAY_SOURCE_READY"
    if ($currentDaySourceReady) {
        $dashboardMutationStarted = $true
        Write-EdgeIQLog -Context $logContext -Level "INFO" -Message ("00:02 rebuilding active selectors and dashboard feeds for {0}." -f $todayMeeting) | Out-Null
        Invoke-EdgeIQPowerShellStep -LogContext $logContext -ResolvedProjectRoot $resolvedProjectRoot -Label "00:02 rebuild selectors / 00:03 rebuild dashboard feeds" -ScriptRelativePath "scripts\run_edgeiq_today_tab_only_dashboard_refresh_v1.ps1"
    } else {
        Write-EdgeIQLog -Context $logContext -Level "WARN" -Message (
            "No current-day meeting source rows are ready for {0}. Retaining previous live dashboard state. files_with_selected_meeting_rows={1} selected_meeting_status={2}" -f
            $todayMeeting,
            $sourceSummary.files_with_selected_meeting_rows,
            $sourceSummary.selected_meeting_status
        ) | Out-Null
    }

    Invoke-EdgeIQPythonStep -LogContext $logContext -ResolvedProjectRoot $resolvedProjectRoot -Label "00:05 verify TODAY meeting exists" -ScriptRelativePath "scripts\build_edgeiq_date_rollover_audit_v1.py"

    $rolloverAudit = Get-EdgeIQLastRolloverAuditRow -AuditPath $rolloverAuditPath
    if ($null -eq $rolloverAudit) {
        throw "Midnight promotion chain could not read rollover audit output."
    }

    if ([string]::IsNullOrWhiteSpace([string]$rolloverAudit.today_meeting)) {
        throw "Midnight promotion chain verification failed because today_meeting is blank in rollover audit."
    }

    Write-EdgeIQLog -Context $logContext -Level "INFO" -Message (
        "Rollover verification status={0} today={1} tomorrow={2} day2={3} universe_rows={4} runner_rows={5}" -f
        $rolloverAudit.status,
        $rolloverAudit.today_meeting,
        $rolloverAudit.tomorrow_meeting,
        $rolloverAudit.day2_meeting,
        $rolloverAudit.universe_rows,
        $rolloverAudit.runner_rows
    ) | Out-Null

    Write-EdgeIQLog -Context $logContext -Level "INFO" -Message "Midnight promotion chain completed successfully." | Out-Null
    Write-Host "[EDGEIQ_MIDNIGHT_PROMOTION_V1] COMPLETE"
    Write-Host "task_name=$TaskName"
    Write-Host "today_meeting=$($rolloverAudit.today_meeting)"
    Write-Host "tomorrow_meeting=$($rolloverAudit.tomorrow_meeting)"
    Write-Host "day2_meeting=$($rolloverAudit.day2_meeting)"
    Write-Host "status=$($rolloverAudit.status)"
    Write-Host "log_path=$($logContext.LogPath)"
    Write-Host "lock_path=$($lockContext.LockPath)"
    exit 0
} catch {
    if ($dashboardMutationStarted -and $backupManifest) {
        try {
            Restore-EdgeIQDashboardBackupManifest -BackupManifest $backupManifest
            Write-EdgeIQLog -Context $logContext -Level "WARN" -Message "Dashboard files restored from rollover checkpoint after failure." | Out-Null
        } catch {
            Write-EdgeIQLog -Context $logContext -Level "ERROR" -Message ("Dashboard restore failed: {0}" -f $_.Exception.Message) | Out-Null
        }
    }

    try {
        Set-Location $resolvedProjectRoot
        Invoke-EdgeIQPythonStep -LogContext $logContext -ResolvedProjectRoot $resolvedProjectRoot -Label "failure-path rollover audit" -ScriptRelativePath "scripts\build_edgeiq_date_rollover_audit_v1.py"
    } catch {
        Write-EdgeIQLog -Context $logContext -Level "ERROR" -Message ("Failure-path rollover audit failed: {0}" -f $_.Exception.Message) | Out-Null
    }

    Write-EdgeIQLog -Context $logContext -Level "ERROR" -Message $_.Exception.Message | Out-Null
    Write-Host "[EDGEIQ_MIDNIGHT_PROMOTION_V1] FAILED"
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

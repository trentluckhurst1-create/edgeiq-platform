[CmdletBinding()]
param(
    [switch]$RunFrontendBuild
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

$DataDir = Join-Path $ProjectRoot "public\data"
$LogPath = Join-Path $DataDir "edgeiq_current_day_full_refresh_v1_log.txt"
$SummaryPath = Join-Path $DataDir "edgeiq_current_day_full_refresh_v1_summary.csv"
$StatusPath = Join-Path $DataDir "edgeiq_current_day_full_refresh_v1_status.json"
$FreshnessPath = Join-Path $DataDir "edgeiq_current_day_artifact_freshness_v1.csv"

$CalendarPath = Join-Path $DataDir "edgeiq_vic_three_day_meeting_calendar_v1.csv"
$TabCalendarPath = Join-Path $DataDir "edgeiq_tab_calendar_racecards_vic_v1.csv"
$RaceCardReportPath = Join-Path $DataDir "race_card_report.csv"
$UniversePath = Join-Path $DataDir "edgeiq_vic_three_day_meeting_universe.csv"
$TerminalPath = Join-Path $DataDir "edgeiq_vic_live_terminal_feed_v1.csv"
$ClassCorrectionPath = Join-Path $DataDir "edgeiq_current_race_class_correction_v5_1.csv"
$ProjectionV52Path = Join-Path $DataDir "edgeiq_current_field_projection_v5_2.csv"
$ProjectionV61Path = Join-Path $DataDir "edgeiq_current_field_projection_V6_1_RESEARCH_replay.csv"
$FairPriceV61Path = Join-Path $DataDir "edgeiq_current_fair_prices_V6_1_RESEARCH_replay.csv"
$RunnerBoardPath = Join-Path $DataDir "edgeiq_live_runner_board_v1.csv"
$GovernedBoardPath = Join-Path $DataDir "edgeiq_live_runner_board_governed_v1.csv"

$PreflightHelperPath = Join-Path $PSScriptRoot "edgeiq_preflight_v1.ps1"
$LockHelperPath = Join-Path $PSScriptRoot "edgeiq_lock_manager_v1.ps1"

$RunStartedAt = (Get-Date).ToString("o")
$StepResults = New-Object System.Collections.Generic.List[object]
$ValidationResults = [ordered]@{}
$OverallStatus = "FAIL"
$FailureStep = ""
$FailureMessage = ""
$TodayDate = ""
$TodayTrack = ""
$LockContext = $null

$SummaryRecord = [ordered]@{
    run_started_at = $RunStartedAt
    run_finished_at = ""
    duration_seconds = ""
    status = "FAIL"
    failure_step = ""
    failure_message = ""
    today_date = ""
    today_track = ""
    calendar_today_rows = 0
    tab_calendar_rows = 0
    universe_today_rows = 0
    terminal_rows = 0
    class_correction_rows = 0
    projection_v5_2_rows = 0
    projection_v6_1_rows = 0
    fair_price_v6_1_rows = 0
    runner_board_rows = 0
    governed_board_rows = 0
    live_price_rows = 0
    scratched_rows = 0
    research_rated_rows = 0
    no_price_rows = 0
    validation_A_calendar_today_meeting_exists = ""
    validation_B_tab_calendar_rows = ""
    validation_C_universe_rows = ""
    validation_D_terminal_alignment = ""
    validation_E_class_correction_alignment = ""
    validation_F_projection_alignment = ""
    validation_G_fair_price_rows = ""
    validation_H_governed_board_alignment = ""
    validation_I_scratched_preserved = ""
    validation_J_live_price_rows = ""
    validation_K_research_rated_rows = ""
    validation_L_no_stale_date_mismatch = ""
    freshness_fail_rows = 0
    freshness_warn_rows = 0
    npm_build_requested = if ($RunFrontendBuild) { "YES" } else { "NO" }
    npm_build_status = if ($RunFrontendBuild) { "PENDING" } else { "SKIPPED" }
    log_file = $LogPath
    status_json = $StatusPath
    freshness_audit_file = $FreshnessPath
}

if (!(Test-Path $DataDir)) {
    New-Item -ItemType Directory -Path $DataDir -Force | Out-Null
}
Set-Content -Path $LogPath -Value "" -Encoding UTF8

function Write-RefreshLog {
    param(
        [string]$Level,
        [string]$Message
    )

    $timestamp = (Get-Date).ToString("yyyy-MM-ddTHH:mm:ssK")
    $line = "{0} [{1}] {2}" -f $timestamp, $Level, $Message
    Add-Content -Path $LogPath -Value $line -Encoding UTF8

    switch ($Level) {
        "ERROR" { Write-Host $line -ForegroundColor Red }
        "WARN" { Write-Host $line -ForegroundColor Yellow }
        default { Write-Host $line }
    }
}

function Add-StepResult {
    param(
        [int]$StepNumber,
        [string]$StepName,
        [string]$CommandText,
        [string]$Status,
        [string]$StartedAt,
        [string]$FinishedAt,
        [int]$ExitCode,
        [string]$Message
    )

    $StepResults.Add(
        [PSCustomObject]@{
            step_number = $StepNumber
            step_name = $StepName
            command = $CommandText
            status = $Status
            started_at = $StartedAt
            finished_at = $FinishedAt
            exit_code = $ExitCode
            message = $Message
        }
    ) | Out-Null
}

function Invoke-PythonStep {
    param(
        [int]$StepNumber,
        [string]$StepName,
        [string]$ScriptPath,
        [string[]]$Arguments = @()
    )

    $commandText = "python `"$ScriptPath`""
    if ($Arguments.Count -gt 0) {
        $commandText += " " + ($Arguments -join " ")
    }

    $startedAt = (Get-Date).ToString("o")
    Write-RefreshLog "INFO" ("STEP {0} START {1}" -f $StepNumber, $StepName)
    Write-RefreshLog "INFO" $commandText

    $output = & python $ScriptPath @Arguments 2>&1
    $exitCode = $LASTEXITCODE

    foreach ($line in $output) {
        $text = ([string]$line).TrimEnd()
        if (![string]::IsNullOrWhiteSpace($text)) {
            Write-RefreshLog "INFO" $text
        }
    }

    $finishedAt = (Get-Date).ToString("o")
    if ($exitCode -ne 0) {
        Add-StepResult -StepNumber $StepNumber -StepName $StepName -CommandText $commandText -Status "FAIL" -StartedAt $startedAt -FinishedAt $finishedAt -ExitCode $exitCode -Message "Python step failed."
        throw "Step $StepNumber failed: $StepName"
    }

    Add-StepResult -StepNumber $StepNumber -StepName $StepName -CommandText $commandText -Status "PASS" -StartedAt $startedAt -FinishedAt $finishedAt -ExitCode 0 -Message "Completed."
    Write-RefreshLog "INFO" ("STEP {0} PASS {1}" -f $StepNumber, $StepName)
}

function Invoke-PowerShellStep {
    param(
        [int]$StepNumber,
        [string]$StepName,
        [scriptblock]$ScriptBlock,
        [string]$CommandText
    )

    $startedAt = (Get-Date).ToString("o")
    Write-RefreshLog "INFO" ("STEP {0} START {1}" -f $StepNumber, $StepName)
    Write-RefreshLog "INFO" $CommandText

    try {
        & $ScriptBlock
        $finishedAt = (Get-Date).ToString("o")
        Add-StepResult -StepNumber $StepNumber -StepName $StepName -CommandText $CommandText -Status "PASS" -StartedAt $startedAt -FinishedAt $finishedAt -ExitCode 0 -Message "Completed."
        Write-RefreshLog "INFO" ("STEP {0} PASS {1}" -f $StepNumber, $StepName)
    } catch {
        $finishedAt = (Get-Date).ToString("o")
        Add-StepResult -StepNumber $StepNumber -StepName $StepName -CommandText $CommandText -Status "FAIL" -StartedAt $startedAt -FinishedAt $finishedAt -ExitCode 1 -Message $_.Exception.Message
        throw
    }
}

function Get-CsvRows {
    param([string]$Path)

    if (!(Test-Path $Path)) {
        throw "Missing required CSV: $Path"
    }

    return @(Import-Csv $Path)
}

function Get-RowCount {
    param([string]$Path)
    return (Get-CsvRows -Path $Path).Count
}

function Get-TodayMeetingContext {
    $rows = Get-CsvRows -Path $CalendarPath
    $todayRows = @($rows | Where-Object { ([string]$_.day_bucket).Trim().ToUpper() -eq "TODAY" })
    if ($todayRows.Count -eq 0) {
        throw "Calendar does not contain a TODAY meeting."
    }

    $track = ([string]$todayRows[0].track).Trim().ToUpper()
    $dateValue = ([string]$todayRows[0].race_date).Trim()
    if ([string]::IsNullOrWhiteSpace($track) -or [string]::IsNullOrWhiteSpace($dateValue)) {
        throw "Calendar TODAY meeting is missing race_date or track."
    }

    return [PSCustomObject]@{
        RaceDate = $dateValue
        Track = $track
        Rows = $todayRows.Count
    }
}

function Get-CurrentRows {
    param(
        [string]$Path,
        [string]$DateColumn = "race_date",
        [string]$TrackColumn = "track"
    )

    $rows = Get-CsvRows -Path $Path
    return @(
        $rows | Where-Object {
            $rowDate = ([string]($_.$DateColumn)).Trim()
            $rowTrack = ([string]($_.$TrackColumn)).Trim().ToUpper()
            ($rowDate.Substring(0, [Math]::Min(10, $rowDate.Length)) -eq $TodayDate) -and ($rowTrack -eq $TodayTrack)
        }
    )
}

function Get-ExactCurrentDayAlignment {
    param(
        [string]$Path,
        [string]$DateColumn = "race_date",
        [string]$TrackColumn = "track"
    )

    $rows = Get-CsvRows -Path $Path
    if ($rows.Count -eq 0) {
        return $false
    }

    $dates = @(
        $rows |
        ForEach-Object { ([string]($_.$DateColumn)).Trim() } |
        Where-Object { $_ -ne "" } |
        ForEach-Object { $_.Substring(0, [Math]::Min(10, $_.Length)) } |
        Sort-Object -Unique
    )
    $tracks = @(
        $rows |
        ForEach-Object { ([string]($_.$TrackColumn)).Trim().ToUpper() } |
        Where-Object { $_ -ne "" } |
        Sort-Object -Unique
    )

    return ($dates.Count -eq 1 -and $dates[0] -eq $TodayDate -and $tracks.Count -eq 1 -and $tracks[0] -eq $TodayTrack)
}

function Get-NonBlankCount {
    param(
        [object[]]$Rows,
        [string]$ColumnName
    )

    return @(
        $Rows | Where-Object {
            $value = [string]($_.$ColumnName)
            ![string]::IsNullOrWhiteSpace($value)
        }
    ).Count
}

function Get-ScratchedCount {
    param([object[]]$Rows)

    return @(
        $Rows | Where-Object {
            $text = @(
                [string]$_.runner_status,
                [string]$_.scratch_status,
                [string]$_.is_scratched,
                [string]$_.tab_fixed_betting_status
            ) -join " "
            $upper = $text.ToUpper()
            $upper.Contains("SCRATCH") -or $upper.Contains("LATESCRATCHED") -or $upper.Contains("TRUE")
        }
    ).Count
}

function Set-ValidationResult {
    param(
        [string]$Key,
        [bool]$Passed,
        [string]$Detail
    )

    $ValidationResults[$Key] = [ordered]@{
        status = if ($Passed) { "PASS" } else { "FAIL" }
        detail = $Detail
    }
    Write-RefreshLog ($(if ($Passed) { "INFO" } else { "ERROR" })) ("VALIDATION {0} {1} - {2}" -f $Key, $ValidationResults[$Key].status, $Detail)
}

function Get-ValidationStatus {
    param([string]$Key)

    if ($ValidationResults.Contains($Key)) {
        return [string]$ValidationResults[$Key].status
    }
    return ""
}

function Write-StatusArtifacts {
    $finishedAt = (Get-Date).ToString("o")
    $SummaryRecord.run_finished_at = $finishedAt
    $SummaryRecord.duration_seconds = [math]::Round(((Get-Date $finishedAt) - (Get-Date $RunStartedAt)).TotalSeconds, 2)
    $SummaryRecord.status = $OverallStatus
    $SummaryRecord.failure_step = $FailureStep
    $SummaryRecord.failure_message = $FailureMessage
    $SummaryRecord.today_date = $TodayDate
    $SummaryRecord.today_track = $TodayTrack

    $SummaryRecord.validation_A_calendar_today_meeting_exists = Get-ValidationStatus -Key "A"
    $SummaryRecord.validation_B_tab_calendar_rows = Get-ValidationStatus -Key "B"
    $SummaryRecord.validation_C_universe_rows = Get-ValidationStatus -Key "C"
    $SummaryRecord.validation_D_terminal_alignment = Get-ValidationStatus -Key "D"
    $SummaryRecord.validation_E_class_correction_alignment = Get-ValidationStatus -Key "E"
    $SummaryRecord.validation_F_projection_alignment = Get-ValidationStatus -Key "F"
    $SummaryRecord.validation_G_fair_price_rows = Get-ValidationStatus -Key "G"
    $SummaryRecord.validation_H_governed_board_alignment = Get-ValidationStatus -Key "H"
    $SummaryRecord.validation_I_scratched_preserved = Get-ValidationStatus -Key "I"
    $SummaryRecord.validation_J_live_price_rows = Get-ValidationStatus -Key "J"
    $SummaryRecord.validation_K_research_rated_rows = Get-ValidationStatus -Key "K"
    $SummaryRecord.validation_L_no_stale_date_mismatch = Get-ValidationStatus -Key "L"

    @([PSCustomObject]$SummaryRecord) | Export-Csv -Path $SummaryPath -NoTypeInformation -Encoding UTF8

    $validationPayload = [ordered]@{}
    foreach ($entry in $ValidationResults.GetEnumerator()) {
        $validationPayload[$entry.Key] = [PSCustomObject]@{
            status = [string]$entry.Value.status
            detail = [string]$entry.Value.detail
        }
    }

    $stepPayload = if ($StepResults.Count -gt 0) { @($StepResults.ToArray()) } else { @() }

    $statusPayload = [ordered]@{
        run_started_at = $RunStartedAt
        run_finished_at = $finishedAt
        duration_seconds = $SummaryRecord.duration_seconds
        status = $OverallStatus
        failure_step = $FailureStep
        failure_message = $FailureMessage
        today_date = $TodayDate
        today_track = $TodayTrack
        summary = [PSCustomObject]$SummaryRecord
        validations = $validationPayload
        steps = $stepPayload
    }
    $statusPayload | ConvertTo-Json -Depth 6 | Set-Content -Path $StatusPath -Encoding UTF8
}

try {
    Write-RefreshLog "INFO" "EDGEIQ current-day full refresh starting."

    if (Test-Path $PreflightHelperPath) {
        . $PreflightHelperPath
        $preflight = Invoke-EdgeIQPreflight -ProjectRoot $ProjectRoot -RequiredDirectories @("scripts", "public", "public\data")
        Write-RefreshLog "INFO" ("Preflight passed. PythonVersion={0}" -f $preflight.PythonVersion)
    } else {
        Write-RefreshLog "WARN" "Preflight helper not found. Continuing without helper."
    }

    if (Test-Path $LockHelperPath) {
        . $LockHelperPath
        $LockContext = Acquire-EdgeIQLock -ProjectRoot $ProjectRoot -LockName "EDGEIQ_CURRENT_DAY_FULL_REFRESH_V1"
        Write-RefreshLog "INFO" ("Lock acquired: {0}" -f $LockContext.LockPath)
    } else {
        Write-RefreshLog "WARN" "Lock helper not found. Continuing without lock."
    }

    Invoke-PythonStep -StepNumber 1 -StepName "Build TAB calendar racecards" -ScriptPath ".\scripts\build_edgeiq_tab_calendar_racecards_v1.py" -Arguments @("--day-bucket", "TODAY", "--max-races", "12")

    Invoke-PowerShellStep -StepNumber 2 -StepName "Sync TAB calendar racecards into race_card_report.csv" -CommandText "Copy-Item `"$TabCalendarPath`" `"$RaceCardReportPath`" -Force" -ScriptBlock {
        if (!(Test-Path $TabCalendarPath)) {
            throw "Missing TAB calendar racecards source: $TabCalendarPath"
        }
        $tabRows = @(Import-Csv $TabCalendarPath)
        if ($tabRows.Count -le 0) {
            throw "TAB calendar racecards source is empty: $TabCalendarPath"
        }
        Copy-Item $TabCalendarPath $RaceCardReportPath -Force
        Write-RefreshLog "INFO" ("Synced race_card_report.csv from TAB calendar source. rows={0}" -f $tabRows.Count)
    }

    Invoke-PythonStep -StepNumber 3 -StepName "Build VIC three-day meeting universe" -ScriptPath ".\scripts\build_edgeiq_vic_three_day_meeting_universe.py"
    Invoke-PythonStep -StepNumber 4 -StepName "Build VIC live terminal feed" -ScriptPath ".\scripts\build_edgeiq_live_terminal_feed_v1.py"
    Invoke-PythonStep -StepNumber 5 -StepName "Build current race class correction V5.1" -ScriptPath ".\scripts\build_edgeiq_current_race_class_correction_v5_1.py"
    Invoke-PythonStep -StepNumber 6 -StepName "Build current field projection V5.2" -ScriptPath ".\scripts\build_edgeiq_current_field_projection_v5_2.py"
    Invoke-PythonStep -StepNumber 7 -StepName "Build current field projection V6.1 research replay" -ScriptPath ".\scripts\build_edgeiq_current_field_projection_v6_1_research_replay.py"
    Invoke-PythonStep -StepNumber 8 -StepName "Build current fair prices V6.1 research replay" -ScriptPath ".\scripts\build_edgeiq_current_fair_prices_v6_1_research_replay.py"
    Invoke-PythonStep -StepNumber 9 -StepName "Build live runner board from terminal" -ScriptPath ".\scripts\build_edgeiq_live_runner_board_from_terminal_v1.py"
    Invoke-PythonStep -StepNumber 10 -StepName "Merge TAB calendar into runner board" -ScriptPath ".\scripts\merge_tab_calendar_into_runner_board_v1.py"
    Invoke-PythonStep -StepNumber 11 -StepName "Build governed live runner board" -ScriptPath ".\scripts\build_edgeiq_live_runner_board_governed_v1.py"

    if ($RunFrontendBuild) {
        Invoke-PowerShellStep -StepNumber 12 -StepName "npm run build" -CommandText "npm run build" -ScriptBlock {
            $output = & npm run build 2>&1
            $exitCode = $LASTEXITCODE
            foreach ($line in $output) {
                $text = ([string]$line).TrimEnd()
                if (![string]::IsNullOrWhiteSpace($text)) {
                    Write-RefreshLog "INFO" $text
                }
            }
            if ($exitCode -ne 0) {
                throw "npm run build failed with exit code $exitCode"
            }
        }
        $SummaryRecord.npm_build_status = "PASS"
    } else {
        $SummaryRecord.npm_build_status = "SKIPPED"
        Write-RefreshLog "INFO" "npm build skipped by default."
    }

    Invoke-PythonStep -StepNumber 13 -StepName "Audit current-day artifact freshness" -ScriptPath ".\scripts\audit_edgeiq_current_day_artifact_freshness_v1.py"

    $todayContext = Get-TodayMeetingContext
    $TodayDate = $todayContext.RaceDate
    $TodayTrack = $todayContext.Track
    $SummaryRecord.calendar_today_rows = $todayContext.Rows

    $tabRows = Get-CurrentRows -Path $TabCalendarPath -DateColumn "race_date" -TrackColumn "track"
    $universeRows = Get-CurrentRows -Path $UniversePath -DateColumn "race_date" -TrackColumn "track"
    $terminalRows = Get-CurrentRows -Path $TerminalPath -DateColumn "race_date" -TrackColumn "track"
    $classRows = Get-CurrentRows -Path $ClassCorrectionPath -DateColumn "race_date" -TrackColumn "track"
    $projectionV52Rows = Get-CurrentRows -Path $ProjectionV52Path -DateColumn "race_date" -TrackColumn "track"
    $projectionV61Rows = Get-CurrentRows -Path $ProjectionV61Path -DateColumn "race_date" -TrackColumn "track"
    $fairRows = Get-CurrentRows -Path $FairPriceV61Path -DateColumn "race_date" -TrackColumn "track"
    $boardRows = Get-CurrentRows -Path $RunnerBoardPath -DateColumn "race_date" -TrackColumn "track"
    $governedRows = Get-CurrentRows -Path $GovernedBoardPath -DateColumn "race_date" -TrackColumn "track"
    $freshnessRows = Get-CsvRows -Path $FreshnessPath

    $SummaryRecord.tab_calendar_rows = $tabRows.Count
    $SummaryRecord.universe_today_rows = $universeRows.Count
    $SummaryRecord.terminal_rows = $terminalRows.Count
    $SummaryRecord.class_correction_rows = $classRows.Count
    $SummaryRecord.projection_v5_2_rows = $projectionV52Rows.Count
    $SummaryRecord.projection_v6_1_rows = $projectionV61Rows.Count
    $SummaryRecord.fair_price_v6_1_rows = $fairRows.Count
    $SummaryRecord.runner_board_rows = $boardRows.Count
    $SummaryRecord.governed_board_rows = $governedRows.Count
    $SummaryRecord.live_price_rows = Get-NonBlankCount -Rows $governedRows -ColumnName "live_price"
    $SummaryRecord.scratched_rows = Get-ScratchedCount -Rows $governedRows
    $SummaryRecord.research_rated_rows = @($governedRows | Where-Object { ([string]$_.V6_1_RESEARCH_price_status).Trim().ToUpper() -eq "RESEARCH_RATED" }).Count
    $SummaryRecord.no_price_rows = @($governedRows | Where-Object { ([string]$_.V6_1_RESEARCH_price_status).Trim().ToUpper() -eq "NO_PRICE" }).Count
    $SummaryRecord.freshness_fail_rows = @($freshnessRows | Where-Object { ([string]$_.status).Trim().ToUpper() -eq "FAIL" }).Count
    $SummaryRecord.freshness_warn_rows = @($freshnessRows | Where-Object { ([string]$_.status).Trim().ToUpper() -eq "WARN" }).Count

    Set-ValidationResult -Key "A" -Passed ($todayContext.Rows -gt 0) -Detail ("today_date={0} today_track={1}" -f $TodayDate, $TodayTrack)
    Set-ValidationResult -Key "B" -Passed ($tabRows.Count -gt 0) -Detail ("tab_calendar_rows={0}" -f $tabRows.Count)
    Set-ValidationResult -Key "C" -Passed ($universeRows.Count -gt 0) -Detail ("universe_today_rows={0}" -f $universeRows.Count)

    $terminalExact = Get-ExactCurrentDayAlignment -Path $TerminalPath -DateColumn "race_date" -TrackColumn "track"
    Set-ValidationResult -Key "D" -Passed ($terminalRows.Count -gt 0 -and $terminalExact -and $terminalRows.Count -eq $universeRows.Count) -Detail ("terminal_rows={0} universe_rows={1} exact={2}" -f $terminalRows.Count, $universeRows.Count, $terminalExact)

    $classExact = Get-ExactCurrentDayAlignment -Path $ClassCorrectionPath -DateColumn "race_date" -TrackColumn "track"
    Set-ValidationResult -Key "E" -Passed ($classRows.Count -eq $terminalRows.Count -and $classExact) -Detail ("class_rows={0} terminal_rows={1} exact={2}" -f $classRows.Count, $terminalRows.Count, $classExact)

    $projectionV52Exact = Get-ExactCurrentDayAlignment -Path $ProjectionV52Path -DateColumn "race_date" -TrackColumn "track"
    $projectionV61Exact = Get-ExactCurrentDayAlignment -Path $ProjectionV61Path -DateColumn "race_date" -TrackColumn "track"
    $projectionPass = (
        $projectionV52Rows.Count -gt 0 -and
        $projectionV52Rows.Count -eq $projectionV61Rows.Count -and
        $projectionV61Rows.Count -eq $fairRows.Count -and
        $projectionV52Exact -and
        $projectionV61Exact
    )
    Set-ValidationResult -Key "F" -Passed $projectionPass -Detail ("projection_v5_2_rows={0} projection_v6_1_rows={1} fair_rows={2} terminal_rows={3}" -f $projectionV52Rows.Count, $projectionV61Rows.Count, $fairRows.Count, $terminalRows.Count)

    $fairExact = Get-ExactCurrentDayAlignment -Path $FairPriceV61Path -DateColumn "race_date" -TrackColumn "track"
    $fairRatedCount = @($fairRows | Where-Object { ([string]$_.V6_1_RESEARCH_price_status).Trim().ToUpper() -eq "RESEARCH_RATED" }).Count
    Set-ValidationResult -Key "G" -Passed ($fairRows.Count -gt 0 -and $fairRows.Count -eq $projectionV61Rows.Count -and $fairRatedCount -gt 0 -and $fairExact) -Detail ("fair_rows={0} research_rated_rows={1} exact={2}" -f $fairRows.Count, $fairRatedCount, $fairExact)

    $governedExact = Get-ExactCurrentDayAlignment -Path $GovernedBoardPath -DateColumn "race_date" -TrackColumn "track"
    Set-ValidationResult -Key "H" -Passed ($governedRows.Count -eq $terminalRows.Count -and $governedExact) -Detail ("governed_rows={0} terminal_rows={1} exact={2}" -f $governedRows.Count, $terminalRows.Count, $governedExact)

    $boardScratchCount = Get-ScratchedCount -Rows $boardRows
    $governedScratchCount = Get-ScratchedCount -Rows $governedRows
    Set-ValidationResult -Key "I" -Passed ($boardScratchCount -eq $governedScratchCount) -Detail ("runner_board_scratched={0} governed_scratched={1}" -f $boardScratchCount, $governedScratchCount)

    $livePriceCount = Get-NonBlankCount -Rows $governedRows -ColumnName "live_price"
    Set-ValidationResult -Key "J" -Passed ($livePriceCount -gt 0) -Detail ("live_price_rows={0}" -f $livePriceCount)

    $researchRatedCount = @($governedRows | Where-Object { ([string]$_.V6_1_RESEARCH_price_status).Trim().ToUpper() -eq "RESEARCH_RATED" }).Count
    Set-ValidationResult -Key "K" -Passed ($researchRatedCount -gt 0) -Detail ("research_rated_rows={0}" -f $researchRatedCount)

    $noStaleMismatch = $terminalExact -and $projectionV52Exact -and $projectionV61Exact -and $fairExact -and $governedExact
    Set-ValidationResult -Key "L" -Passed $noStaleMismatch -Detail "terminal/projection/fair/governed artifacts all align to calendar TODAY."

    $validationFailures = @($ValidationResults.GetEnumerator() | Where-Object { $_.Value.status -ne "PASS" }).Count
    $freshnessFailures = $SummaryRecord.freshness_fail_rows

    if ($validationFailures -eq 0 -and $freshnessFailures -eq 0) {
        $OverallStatus = "PASS"
        Write-RefreshLog "INFO" "EDGEIQ current-day full refresh completed successfully."
    } else {
        $OverallStatus = "FAIL"
        $FailureStep = "VALIDATION"
        $FailureMessage = "One or more validations or freshness checks failed."
        throw $FailureMessage
    }
} catch {
    if ([string]::IsNullOrWhiteSpace($FailureStep)) {
        $FailureStep = if ($StepResults.Count -gt 0) { $StepResults[$StepResults.Count - 1].step_name } else { "INITIALISATION" }
    }
    $FailureMessage = $_.Exception.Message
    $OverallStatus = "FAIL"
    Write-RefreshLog "ERROR" $FailureMessage
} finally {
    if ($LockContext) {
        try {
            $release = Release-EdgeIQLock -ProjectRoot $ProjectRoot -LockName "EDGEIQ_CURRENT_DAY_FULL_REFRESH_V1"
            Write-RefreshLog "INFO" ("Lock release status: {0}" -f $release.Status)
        } catch {
            Write-RefreshLog "ERROR" ("Lock release failed: {0}" -f $_.Exception.Message)
        }
    }

    Write-StatusArtifacts

    if ($OverallStatus -eq "PASS") {
        Write-Host "[EDGEIQ_CURRENT_DAY_FULL_REFRESH_V1] COMPLETE"
        Write-Host "status=PASS"
        Write-Host "today_date=$TodayDate"
        Write-Host "today_track=$TodayTrack"
        Write-Host "governed_board_rows=$($SummaryRecord.governed_board_rows)"
        Write-Host "live_price_rows=$($SummaryRecord.live_price_rows)"
        Write-Host "research_rated_rows=$($SummaryRecord.research_rated_rows)"
        Write-Host "wrote=$SummaryPath"
        Write-Host "wrote=$StatusPath"
        Write-Host "wrote=$FreshnessPath"
        exit 0
    }

    Write-Host "[EDGEIQ_CURRENT_DAY_FULL_REFRESH_V1] FAILED"
    Write-Host "status=FAIL"
    Write-Host "failure_step=$FailureStep"
    Write-Host "failure_message=$FailureMessage"
    Write-Host "wrote=$SummaryPath"
    Write-Host "wrote=$StatusPath"
    exit 1
}

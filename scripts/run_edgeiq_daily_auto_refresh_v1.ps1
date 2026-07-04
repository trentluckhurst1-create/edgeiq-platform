[CmdletBinding()]
param(
    [switch]$RunFrontendBuild,
    [switch]$StopBundlersIfRunning
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

$DataDir = Join-Path $ProjectRoot "public\data"
$LogsDir = Join-Path $ProjectRoot "logs"
$LogPath = Join-Path $LogsDir "edgeiq_daily_auto_refresh_latest.log"

$CalendarPath = Join-Path $DataDir "edgeiq_vic_three_day_meeting_calendar_v1.csv"
$UniversePath = Join-Path $DataDir "edgeiq_vic_three_day_meeting_universe.csv"
$UniverseDiagPath = Join-Path $DataDir "edgeiq_vic_three_day_meeting_diagnostics.csv"
$SourceInventorySummaryPath = Join-Path $DataDir "edgeiq_current_day_source_inventory_summary_v1.csv"
$SourceInventoryAuditPath = Join-Path $DataDir "edgeiq_current_day_source_inventory_audit_v1.csv"
$VicTabRacecardsPath = Join-Path $DataDir "edgeiq_tab_calendar_racecards_vic_v1.csv"
$AllTabRacecardsPath = Join-Path $DataDir "edgeiq_tab_calendar_racecards_v1.csv"
$RaceCardReportPath = Join-Path $DataDir "race_card_report.csv"
$TerminalTodayPath = Join-Path $DataDir "edgeiq_live_terminal_feed_v1_TAB_ONLY_TODAY.csv"
$VicTerminalPath = Join-Path $DataDir "edgeiq_vic_live_terminal_feed_v1.csv"
$TerminalPath = Join-Path $DataDir "edgeiq_live_terminal_feed_v1.csv"
$RunnerBoardPath = Join-Path $DataDir "edgeiq_live_runner_board_v1.csv"
$ProbabilityIntegrityDetailPath = Join-Path $DataDir "edgeiq_race_probability_integrity_v1.csv"
$RunnerDnaV62AliasPath = Join-Path $DataDir "edgeiq_runner_dna_v6_2.csv"
$RunnerDnaV62LivePath = Join-Path $DataDir "edgeiq_live_runner_dna_v6_2.csv"
$DailyFreshnessSummaryPath = Join-Path $DataDir "edgeiq_daily_freshness_audit_v1_summary.csv"

. (Join-Path $PSScriptRoot "edgeiq_preflight_v1.ps1")
. (Join-Path $PSScriptRoot "edgeiq_lock_manager_v1.ps1")

if (!(Test-Path $DataDir)) {
    New-Item -ItemType Directory -Path $DataDir -Force | Out-Null
}
if (!(Test-Path $LogsDir)) {
    New-Item -ItemType Directory -Path $LogsDir -Force | Out-Null
}
Set-Content -Path $LogPath -Value "" -Encoding UTF8

$RunStartedAt = Get-Date
$TodayDate = (Get-Date).ToString("yyyy-MM-dd")
$TomorrowDate = (Get-Date).AddDays(1).ToString("yyyy-MM-dd")
$Day2Date = (Get-Date).AddDays(2).ToString("yyyy-MM-dd")
$SelectedTrack = ""
$LockContext = $null
$ExternalFailureHint = ""

function Write-DailyLog {
    param(
        [ValidateSet("INFO", "WARN", "ERROR")]
        [string]$Level,
        [string]$Message
    )

    $timestamp = (Get-Date).ToString("yyyy-MM-ddTHH:mm:ssK")
    $line = "{0} [{1}] [EDGEIQ_DAILY_AUTO_REFRESH_V1] {2}" -f $timestamp, $Level, $Message
    Add-Content -Path $LogPath -Value $line -Encoding UTF8

    switch ($Level) {
        "ERROR" { Write-Host $line -ForegroundColor Red }
        "WARN" { Write-Host $line -ForegroundColor Yellow }
        default { Write-Host $line }
    }
}

function Invoke-PythonScript {
    param(
        [string]$Label,
        [string]$ScriptRelativePath,
        [string[]]$Arguments = @()
    )

    $scriptPath = Join-Path $ProjectRoot $ScriptRelativePath
    if (!(Test-Path $scriptPath -PathType Leaf)) {
        throw "Missing script: $scriptPath"
    }

    Write-DailyLog -Level "INFO" -Message ("START {0}" -f $Label)
    Write-DailyLog -Level "INFO" -Message ("python `"{0}`" {1}" -f $scriptPath, ($Arguments -join " "))

    $output = & python $scriptPath @Arguments 2>&1
    $exitCode = $LASTEXITCODE

    foreach ($line in $output) {
        $text = ([string]$line).TrimEnd()
        if (![string]::IsNullOrWhiteSpace($text)) {
            Write-DailyLog -Level "INFO" -Message $text
        }
    }

    if ($exitCode -ne 0) {
        throw "Python step failed: $ScriptRelativePath"
    }

    Write-DailyLog -Level "INFO" -Message ("PASS {0}" -f $Label)
}

function Invoke-PowerShellStep {
    param(
        [string]$Label,
        [scriptblock]$ScriptBlock
    )

    Write-DailyLog -Level "INFO" -Message ("START {0}" -f $Label)
    & $ScriptBlock
    Write-DailyLog -Level "INFO" -Message ("PASS {0}" -f $Label)
}

function Get-CsvRows {
    param([string]$Path)
    if (!(Test-Path $Path -PathType Leaf)) {
        return @()
    }
    return @(Import-Csv $Path)
}

function Summarise-RaceDates {
    param([object[]]$Rows)
    $dates = @(
        $Rows |
        ForEach-Object {
            $value = [string]$_.race_date
            if ([string]::IsNullOrWhiteSpace($value)) { $value = [string]$_.meeting_date }
            if ([string]::IsNullOrWhiteSpace($value)) { $value = [string]$_.date }
            $value.Trim()
        } |
        Where-Object { $_ -ne "" } |
        ForEach-Object { $_.Substring(0, [Math]::Min(10, $_.Length)) } |
        Sort-Object -Unique
    )
    return ($dates -join "|")
}

function Get-TodayCalendarTrack {
    $rows = Get-CsvRows -Path $CalendarPath
    $todayRow = $rows | Where-Object { ([string]$_.day_bucket).Trim().ToUpper() -eq "TODAY" } | Select-Object -First 1
    if ($null -eq $todayRow) {
        throw "Calendar does not contain a TODAY row."
    }
    $track = ([string]$todayRow.track).Trim().ToUpper()
    if ([string]::IsNullOrWhiteSpace($track)) {
        throw "Calendar TODAY row track is blank."
    }
    return $track
}

function Get-SelectedTrackFromSourceInventory {
    if (!(Test-Path $SourceInventorySummaryPath -PathType Leaf)) {
        return ""
    }
    $rows = @(Import-Csv $SourceInventorySummaryPath)
    if ($rows.Count -eq 0) {
        return ""
    }
    return ([string]$rows[0].selected_meeting).Trim().ToUpper()
}

function Merge-ThreeDayTabRacecards {
    $bucketFiles = @(
        [PSCustomObject]@{ DayBucket = "TODAY"; Path = Join-Path $DataDir "edgeiq_tab_calendar_racecards_vic_TODAY_v1.csv" },
        [PSCustomObject]@{ DayBucket = "TOMORROW"; Path = Join-Path $DataDir "edgeiq_tab_calendar_racecards_vic_TOMORROW_v1.csv" },
        [PSCustomObject]@{ DayBucket = "DAY+2"; Path = Join-Path $DataDir "edgeiq_tab_calendar_racecards_vic_DAYPLUS2_v1.csv" }
    )

    $allRows = New-Object System.Collections.Generic.List[object]
    foreach ($bucketFile in $bucketFiles) {
        if (!(Test-Path $bucketFile.Path -PathType Leaf)) {
            Write-DailyLog -Level "WARN" -Message ("Missing bucket racecard file: {0}" -f $bucketFile.Path)
            continue
        }
        $rows = @(Import-Csv $bucketFile.Path)
        foreach ($row in $rows) {
            $allRows.Add($row) | Out-Null
        }
    }

    if ($allRows.Count -eq 0) {
        throw "No TAB calendar racecard rows captured for TODAY/TOMORROW/DAY+2."
    }

    $columns = New-Object System.Collections.Generic.List[string]
    $seenColumns = @{}
    foreach ($row in $allRows) {
        foreach ($property in $row.PSObject.Properties.Name) {
            if (-not $seenColumns.ContainsKey($property)) {
                $seenColumns[$property] = $true
                $columns.Add($property) | Out-Null
            }
        }
    }

    $dedupe = @{}
    foreach ($row in $allRows) {
        $meetingDate = [string]$row.meeting_date
        $track = [string]$row.track
        $raceNo = [string]$row.race_no
        $runnerNo = [string]$row.runner_no
        $horse = [string]$row.horse
        $key = "{0}|{1}|{2}|{3}|{4}" -f $meetingDate, $track, $raceNo, $runnerNo, $horse
        if (-not $dedupe.ContainsKey($key)) {
            $dedupe[$key] = $row
        }
    }

    $normalizedRows = foreach ($row in $dedupe.Values) {
        $obj = [ordered]@{}
        foreach ($column in $columns) {
            $obj[$column] = [string]$row.$column
        }
        [PSCustomObject]$obj
    }

    $sortedRows = $normalizedRows | Sort-Object meeting_date, meeting_name, @{
        Expression = {
            $digits = [string]$_.race_no -replace '[^0-9]', ''
            if ([string]::IsNullOrWhiteSpace($digits)) { 0 } else { [int]$digits }
        }
    }, @{
        Expression = {
            $digits = [string]$_.runner_no -replace '[^0-9]', ''
            if ([string]::IsNullOrWhiteSpace($digits)) { 0 } else { [int]$digits }
        }
    }
    $sortedRows | Export-Csv -Path $VicTabRacecardsPath -NoTypeInformation -Encoding UTF8
    $sortedRows | Export-Csv -Path $AllTabRacecardsPath -NoTypeInformation -Encoding UTF8
    $sortedRows | Export-Csv -Path $RaceCardReportPath -NoTypeInformation -Encoding UTF8

    Write-DailyLog -Level "INFO" -Message ("Merged multi-day TAB racecards rows={0} dates={1}" -f $sortedRows.Count, (Summarise-RaceDates -Rows $sortedRows))
}

function Copy-CurrentBucketCapture {
    param(
        [string]$DayBucket,
        [string]$TargetPath
    )

    if (!(Test-Path $VicTabRacecardsPath -PathType Leaf)) {
        throw "Missing expected TAB calendar racecard output after $DayBucket capture: $VicTabRacecardsPath"
    }
    $rows = @(Import-Csv $VicTabRacecardsPath)
    if ($rows.Count -eq 0) {
        Write-DailyLog -Level "WARN" -Message ("No VIC TAB racecard rows returned for {0}" -f $DayBucket)
    }
    Copy-Item $VicTabRacecardsPath $TargetPath -Force
    Write-DailyLog -Level "INFO" -Message ("Captured {0} TAB racecards -> {1} rows={2}" -f $DayBucket, $TargetPath, $rows.Count)
}

function Invoke-DailyFreshnessAudit {
    Invoke-PythonScript -Label "DAILY FRESHNESS AUDIT" -ScriptRelativePath "scripts\audit_edgeiq_daily_freshness_v1.py"
}

function Assert-ProbabilityIntegrityWindow {
    param(
        [string]$Label
    )

    if (!(Test-Path $ProbabilityIntegrityDetailPath -PathType Leaf)) {
        throw "Missing probability integrity audit output: $ProbabilityIntegrityDetailPath"
    }

    $rows = @(Import-Csv $ProbabilityIntegrityDetailPath)
    if ($rows.Count -eq 0) {
        throw "Probability integrity audit output is empty: $ProbabilityIntegrityDetailPath"
    }

    $windowRows = @(
        $rows |
        Where-Object {
            $raceDate = ([string]$_.race_date).Trim()
            $raceDate -eq $TodayDate -or $raceDate -eq $TomorrowDate
        }
    )

    if ($windowRows.Count -eq 0) {
        throw "$Label did not produce any TODAY/TOMORROW race integrity rows."
    }

    foreach ($row in ($windowRows | Sort-Object race_date, track, @{ Expression = {
        $digits = [string]$_.race_no -replace '[^0-9]', ''
        if ([string]::IsNullOrWhiteSpace($digits)) { 9999 } else { [int]$digits }
    } })) {
        Write-DailyLog -Level "INFO" -Message (
            "probability_integrity race_date={0} track={1} race_no={2} win_pct_sum={3} status={4}" -f
            $row.race_date,
            $row.track,
            $row.race_no,
            $row.win_pct_sum,
            $row.status
        )
    }

    $failRows = @(
        $windowRows |
        Where-Object { ([string]$_.status).Trim().ToUpper().StartsWith("FAIL") }
    )

    if ($failRows.Count -gt 0) {
        foreach ($row in $failRows) {
            Write-DailyLog -Level "ERROR" -Message (
                "probability_integrity_fail race_date={0} track={1} race_no={2} status={3} active_runner_count={4} win_pct_sum={5}" -f
                $row.race_date,
                $row.track,
                $row.race_no,
                $row.status,
                $row.active_runner_count,
                $row.win_pct_sum
            )
        }
        throw "$Label failed. TODAY/TOMORROW race probability integrity contains FAIL statuses."
    }
}

function Stop-StaleBundlers {
    if (-not $StopBundlersIfRunning) {
        Write-DailyLog -Level "INFO" -Message "Bundler stop not requested."
        return
    }

    $node = Get-Process node -ErrorAction SilentlyContinue
    $esbuild = Get-Process esbuild -ErrorAction SilentlyContinue

    if ($node) {
        Write-DailyLog -Level "WARN" -Message ("Stopping node processes count={0}" -f @($node).Count)
        $node | Stop-Process -Force
    }
    if ($esbuild) {
        Write-DailyLog -Level "WARN" -Message ("Stopping esbuild processes count={0}" -f @($esbuild).Count)
        $esbuild | Stop-Process -Force
    }
}

try {
    Write-DailyLog -Level "INFO" -Message "EDGEIQ daily auto refresh starting."
    Write-DailyLog -Level "INFO" -Message ("today={0} tomorrow={1} day_plus_2={2}" -f $TodayDate, $TomorrowDate, $Day2Date)

    $preflight = Invoke-EdgeIQPreflight -ProjectRoot $ProjectRoot -RequiredDirectories @("scripts", "public", "public\data") -RequiredCsvPaths @("public\data\edgeiq_racingcom_historical_calendar_backfill_v1.csv")
    Write-DailyLog -Level "INFO" -Message ("Preflight passed. PythonVersion={0}" -f $preflight.PythonVersion)

    $LockContext = Acquire-EdgeIQLock -ProjectRoot $ProjectRoot -LockName "EDGEIQ_DAILY_AUTO_REFRESH_V1"
    Write-DailyLog -Level "INFO" -Message ("Lock acquired: {0}" -f $LockContext.LockPath)

    Stop-StaleBundlers

    Invoke-PythonScript -Label "THREE DAY MEETING CALENDAR" -ScriptRelativePath "scripts\build_edgeiq_vic_three_day_meeting_calendar_v1.py"

    Invoke-PowerShellStep -Label "VALIDATE CALENDAR WINDOW" -ScriptBlock {
        $calendarRows = Get-CsvRows -Path $CalendarPath
        if ($calendarRows.Count -eq 0) {
            throw "Calendar output is empty: $CalendarPath"
        }
        $dayBuckets = $calendarRows | Group-Object day_bucket | Select-Object Name,Count
        $hasToday = @($calendarRows | Where-Object { ([string]$_.day_bucket).Trim().ToUpper() -eq "TODAY" }).Count -gt 0
        $hasTomorrow = @($calendarRows | Where-Object { ([string]$_.day_bucket).Trim().ToUpper() -eq "TOMORROW" }).Count -gt 0
        $hasDay2 = @($calendarRows | Where-Object { ([string]$_.day_bucket).Trim().ToUpper() -eq "DAY+2" }).Count -gt 0

        foreach ($row in $dayBuckets) {
            Write-DailyLog -Level "INFO" -Message ("calendar_day_bucket={0} count={1}" -f $row.Name, $row.Count)
        }

        if (-not $hasToday) { throw "Calendar is missing TODAY meeting rows." }
        if (-not $hasTomorrow) { throw "Calendar is missing TOMORROW meeting rows." }
        if (-not $hasDay2) {
            Write-DailyLog -Level "WARN" -Message "Calendar is missing DAY+2 meeting rows."
        }
    }

    $todayBucketPath = Join-Path $DataDir "edgeiq_tab_calendar_racecards_vic_TODAY_v1.csv"
    $tomorrowBucketPath = Join-Path $DataDir "edgeiq_tab_calendar_racecards_vic_TOMORROW_v1.csv"
    $day2BucketPath = Join-Path $DataDir "edgeiq_tab_calendar_racecards_vic_DAYPLUS2_v1.csv"

    Invoke-PythonScript -Label "TAB CALENDAR RACECARDS TODAY" -ScriptRelativePath "scripts\build_edgeiq_tab_calendar_racecards_v1.py" -Arguments @("--day-bucket", "TODAY", "--max-races", "12")
    Invoke-PowerShellStep -Label "CAPTURE TODAY RACECARDS" -ScriptBlock { Copy-CurrentBucketCapture -DayBucket "TODAY" -TargetPath $todayBucketPath }

    Invoke-PythonScript -Label "TAB CALENDAR RACECARDS TOMORROW" -ScriptRelativePath "scripts\build_edgeiq_tab_calendar_racecards_v1.py" -Arguments @("--day-bucket", "TOMORROW", "--max-races", "12")
    Invoke-PowerShellStep -Label "CAPTURE TOMORROW RACECARDS" -ScriptBlock { Copy-CurrentBucketCapture -DayBucket "TOMORROW" -TargetPath $tomorrowBucketPath }

    Invoke-PythonScript -Label "TAB CALENDAR RACECARDS DAY+2" -ScriptRelativePath "scripts\build_edgeiq_tab_calendar_racecards_v1.py" -Arguments @("--day-bucket", "DAY+2", "--max-races", "12")
    Invoke-PowerShellStep -Label "CAPTURE DAY+2 RACECARDS" -ScriptBlock { Copy-CurrentBucketCapture -DayBucket "DAY+2" -TargetPath $day2BucketPath }

    Invoke-PowerShellStep -Label "MERGE MULTI-DAY TAB RACECARDS" -ScriptBlock { Merge-ThreeDayTabRacecards }

    Invoke-PythonScript -Label "THREE DAY MEETING UNIVERSE" -ScriptRelativePath "scripts\build_edgeiq_vic_three_day_meeting_universe.py"
    Invoke-PythonScript -Label "CURRENT DAY SOURCE INVENTORY AUDIT" -ScriptRelativePath "scripts\audit_edgeiq_current_day_source_inventory_v1.py"

    Invoke-PowerShellStep -Label "VALIDATE UNIVERSE DATES" -ScriptBlock {
        $universeRows = Get-CsvRows -Path $UniversePath
        if ($universeRows.Count -eq 0) {
            throw "Universe output is empty: $UniversePath"
        }

        $universeDates = @(
            $universeRows |
            ForEach-Object { ([string]$_.race_date).Trim() } |
            Where-Object { $_ -ne "" } |
            ForEach-Object { $_.Substring(0, [Math]::Min(10, $_.Length)) } |
            Sort-Object -Unique
        )
        Write-DailyLog -Level "INFO" -Message ("universe_race_dates={0}" -f ($universeDates -join "|"))

        if ($universeDates -notcontains $TodayDate -or $universeDates -notcontains $TomorrowDate) {
            $ExternalFailureHint = "Universe does not contain both TODAY and TOMORROW after multi-day racecard harvest."
            Write-DailyLog -Level "ERROR" -Message $ExternalFailureHint
        }

        if ($universeDates -notcontains $Day2Date) {
            Write-DailyLog -Level "WARN" -Message "Universe does not currently contain DAY+2 rows."
        }
    }

    $SelectedTrack = Get-SelectedTrackFromSourceInventory
    if ([string]::IsNullOrWhiteSpace($SelectedTrack)) {
        $SelectedTrack = Get-TodayCalendarTrack
        Write-DailyLog -Level "WARN" -Message ("Selected meeting fell back to calendar TODAY track: {0}" -f $SelectedTrack)
    } else {
        Write-DailyLog -Level "INFO" -Message ("Selected meeting from source inventory: {0}" -f $SelectedTrack)
    }

    Invoke-PythonScript -Label "TODAY TERMINAL FEED" -ScriptRelativePath "scripts\build_edgeiq_live_terminal_feed_v1_tab_only_today.py"
    Invoke-PythonScript -Label "THREE DAY TERMINAL SEED" -ScriptRelativePath "scripts\build_edgeiq_vic_three_day_terminal_seed_v1.py"

    Invoke-PythonScript -Label "ACTIVE RACE SELECTOR" -ScriptRelativePath "scripts\build_edgeiq_active_race_selector.py"
    Invoke-PythonScript -Label "CURRENT RACE CLASS CORRECTION V5.1" -ScriptRelativePath "scripts\build_edgeiq_current_race_class_correction_v5_1.py"
    Invoke-PythonScript -Label "CURRENT FIELD PROJECTION V5.2" -ScriptRelativePath "scripts\build_edgeiq_current_field_projection_v5_2.py"
    Invoke-PythonScript -Label "CURRENT FAIR PRICES REVIEW V5.2" -ScriptRelativePath "scripts\build_edgeiq_current_fair_prices_review_v5_2.py"
    Invoke-PythonScript -Label "HISTORICAL PERFORMANCE RATING V6.1 RESEARCH" -ScriptRelativePath "scripts\build_edgeiq_historical_performance_rating_v6_1_research.py"
    Invoke-PythonScript -Label "CURRENT FIELD PROJECTION V6.1 RESEARCH REPLAY" -ScriptRelativePath "scripts\build_edgeiq_current_field_projection_v6_1_research_replay.py"
    Invoke-PythonScript -Label "CURRENT FAIR PRICES V6.1 RESEARCH REPLAY" -ScriptRelativePath "scripts\build_edgeiq_current_fair_prices_v6_1_research_replay.py"
    Invoke-PythonScript -Label "LIVE V6.1 RESEARCH VS PRODUCTION COMPARISON" -ScriptRelativePath "scripts\build_edgeiq_live_v6_1_research_vs_production_comparison_v1_TAB_ONLY_TODAY.py"
    Invoke-PythonScript -Label "LIVE RUNNER BOARD FROM TERMINAL" -ScriptRelativePath "scripts\build_edgeiq_live_runner_board_from_terminal_v1.py"
    Invoke-PythonScript -Label "NO PROJECTION FALLBACK ADJUSTMENT" -ScriptRelativePath "scripts\apply_edgeiq_no_projection_fallback_adjustment_v1.py"
    Invoke-PythonScript -Label "MERGE TAB CALENDAR INTO RUNNER BOARD" -ScriptRelativePath "scripts\merge_tab_calendar_into_runner_board_v1.py"
    Invoke-PythonScript -Label "LIVE RUNNER BOARD PROBABILITY NORMALISATION" -ScriptRelativePath "scripts\fix_edgeiq_live_runner_board_probability_normalisation_v1.py"
    Invoke-PythonScript -Label "RACE PROBABILITY INTEGRITY AUDIT PRE-DOWNSTREAM" -ScriptRelativePath "scripts\audit_edgeiq_race_probability_integrity_v1.py"
    Invoke-PowerShellStep -Label "VALIDATE RACE PROBABILITY INTEGRITY PRE-DOWNSTREAM" -ScriptBlock {
        Assert-ProbabilityIntegrityWindow -Label "Pre-downstream probability integrity audit"
    }
    Invoke-PythonScript -Label "GOVERNED LIVE RUNNER BOARD" -ScriptRelativePath "scripts\build_edgeiq_live_runner_board_governed_v1.py"

    Invoke-PythonScript -Label "LIVE RUNNER STYLE" -ScriptRelativePath "scripts\build_edgeiq_live_runner_style_v1.py"
    Invoke-PythonScript -Label "LIVE TRACK INTELLIGENCE" -ScriptRelativePath "scripts\build_edgeiq_live_track_intelligence_v1.py"
    Invoke-PythonScript -Label "TRACK INTELLIGENCE CARD" -ScriptRelativePath "scripts\build_edgeiq_track_intelligence_card_v1.py"
    Invoke-PythonScript -Label "REAL SPEED MAP ENGINE" -ScriptRelativePath "scripts\build_edgeiq_real_speed_map_engine.py"
    Invoke-PythonScript -Label "LIVE SECTIONAL INTELLIGENCE" -ScriptRelativePath "scripts\build_edgeiq_live_sectional_intelligence_v1.py"
    Invoke-PythonScript -Label "RUNNER INTELLIGENCE V1" -ScriptRelativePath "scripts\build_edgeiq_runner_intelligence_v1.py"
    Invoke-PythonScript -Label "RACE INTELLIGENCE CARDS" -ScriptRelativePath "scripts\build_edgeiq_race_intelligence_cards_v1.py"
    Invoke-PythonScript -Label "INTELLIGENCE TERMINAL" -ScriptRelativePath "scripts\build_edgeiq_intelligence_terminal_v1.py"
    Invoke-PythonScript -Label "HORSE INTELLIGENCE DRAWER" -ScriptRelativePath "scripts\build_edgeiq_horse_intelligence_drawer_v1.py"

    Invoke-PythonScript -Label "HORSE PROFILE V3" -ScriptRelativePath "scripts\build_edgeiq_horse_profile_v3.py"
    Invoke-PowerShellStep -Label "SYNC HORSE PROFILE CURRENT ALIASES" -ScriptBlock {
        $horseProfileLiveV3 = Join-Path $DataDir "edgeiq_live_horse_profile_v3.csv"
        $horseProfileLiveCurrent = Join-Path $DataDir "edgeiq_live_horse_profile_current.csv"
        $horseProfileV3 = Join-Path $DataDir "edgeiq_horse_profile_v3.csv"
        $horseProfileCurrent = Join-Path $DataDir "edgeiq_horse_profile_current.csv"

        if (Test-Path $horseProfileLiveV3 -PathType Leaf) {
            Copy-Item $horseProfileLiveV3 $horseProfileLiveCurrent -Force
            Write-DailyLog -Level "INFO" -Message ("synced_horse_profile_alias={0}" -f $horseProfileLiveCurrent)
        } else {
            throw "Missing horse profile live v3 source: $horseProfileLiveV3"
        }

        if (Test-Path $horseProfileV3 -PathType Leaf) {
            Copy-Item $horseProfileV3 $horseProfileCurrent -Force
            Write-DailyLog -Level "INFO" -Message ("synced_horse_profile_alias={0}" -f $horseProfileCurrent)
        } else {
            throw "Missing horse profile v3 source: $horseProfileV3"
        }
    }

    Invoke-PythonScript -Label "RUNNER DNA V1" -ScriptRelativePath "scripts\build_edgeiq_runner_dna_v1.py"
    Invoke-PythonScript -Label "RUNNER DNA V2" -ScriptRelativePath "scripts\build_edgeiq_runner_dna_v2.py"
    Invoke-PythonScript -Label "RUNNER DNA V3" -ScriptRelativePath "scripts\build_edgeiq_runner_dna_v3.py"
    Invoke-PythonScript -Label "RUNNER DNA V4 COMPONENT BREAKDOWN" -ScriptRelativePath "scripts\build_edgeiq_runner_dna_v4_component_breakdown.py"
    Invoke-PythonScript -Label "RUNNER DNA V5 SIGNAL HARVEST" -ScriptRelativePath "scripts\build_edgeiq_runner_dna_v5_signal_harvest.py"

    Invoke-PythonScript -Label "DISTANCE DNA V1" -ScriptRelativePath "scripts\build_edgeiq_distance_dna_v1.py"
    Invoke-PythonScript -Label "CONDITION DNA V1" -ScriptRelativePath "scripts\build_edgeiq_condition_dna_v1.py"
    Invoke-PythonScript -Label "CLASS DNA V3" -ScriptRelativePath "scripts\build_edgeiq_class_dna_v3.py"

    Invoke-PythonScript -Label "RUNNER DNA V6.2" -ScriptRelativePath "scripts\build_edgeiq_runner_dna_v6_2.py"
    Invoke-PythonScript -Label "RUNNER DNA CONTRIBUTION BREAKDOWN" -ScriptRelativePath "scripts\build_edgeiq_runner_dna_contribution_breakdown_v1.py"
    Invoke-PythonScript -Label "RUNNER DNA EXPLAINABILITY PANEL" -ScriptRelativePath "scripts\build_edgeiq_runner_dna_explainability_panel_v1.py"
    Invoke-PythonScript -Label "RUNNER DNA DRAWER FEED V1" -ScriptRelativePath "scripts\build_edgeiq_runner_dna_drawer_feed_v1.py"
    Invoke-PythonScript -Label "RUNNER DNA DRAWER FEED V2" -ScriptRelativePath "scripts\build_edgeiq_runner_dna_drawer_feed_v2.py"

    Invoke-PowerShellStep -Label "SYNC RUNNER DNA V6.2 ALIAS" -ScriptBlock {
        if (Test-Path $RunnerDnaV62LivePath -PathType Leaf) {
            Copy-Item $RunnerDnaV62LivePath $RunnerDnaV62AliasPath -Force
            Write-DailyLog -Level "INFO" -Message ("synced_runner_dna_alias={0}" -f $RunnerDnaV62AliasPath)
        } else {
            Write-DailyLog -Level "WARN" -Message ("runner_dna_v6_2 live source missing: {0}" -f $RunnerDnaV62LivePath)
        }
    }

    Invoke-PythonScript -Label "FUTURE MEETING FEED COVERAGE AUDIT" -ScriptRelativePath "scripts\audit_edgeiq_future_meeting_feed_coverage_v1.py"
    Invoke-PythonScript -Label "RACE PROBABILITY INTEGRITY AUDIT FINAL" -ScriptRelativePath "scripts\audit_edgeiq_race_probability_integrity_v1.py"
    Invoke-PowerShellStep -Label "VALIDATE RACE PROBABILITY INTEGRITY FINAL" -ScriptBlock {
        Assert-ProbabilityIntegrityWindow -Label "Final probability integrity audit"
    }

    Invoke-DailyFreshnessAudit

    if (!(Test-Path $DailyFreshnessSummaryPath -PathType Leaf)) {
        throw "Missing freshness summary after audit: $DailyFreshnessSummaryPath"
    }

    $freshnessSummaryRows = @(Import-Csv $DailyFreshnessSummaryPath)
    if ($freshnessSummaryRows.Count -eq 0) {
        throw "Freshness summary is empty: $DailyFreshnessSummaryPath"
    }

    $freshnessSummary = $freshnessSummaryRows[0]
    $overallStatus = ([string]$freshnessSummary.overall_status).Trim().ToUpper()
    Write-DailyLog -Level "INFO" -Message ("freshness_overall_status={0}" -f $overallStatus)
    Write-DailyLog -Level "INFO" -Message ("freshness_universe_dates={0}" -f ([string]$freshnessSummary.universe_race_dates))

    if ($RunFrontendBuild) {
        Invoke-PowerShellStep -Label "NPM BUILD" -ScriptBlock {
            $output = & npm run build 2>&1
            $exitCode = $LASTEXITCODE
            foreach ($line in $output) {
                $text = ([string]$line).TrimEnd()
                if (![string]::IsNullOrWhiteSpace($text)) {
                    Write-DailyLog -Level "INFO" -Message $text
                }
            }
            if ($exitCode -ne 0) {
                throw "npm run build failed with exit code $exitCode"
            }
        }
    } else {
        Write-DailyLog -Level "INFO" -Message "npm build skipped."
    }

    $finalStatus = "PASS"
    if ($overallStatus -eq "WARN") {
        $finalStatus = "PASS_WITH_WARNINGS"
        Write-DailyLog -Level "WARN" -Message ("Daily freshness finished with warnings: {0}" -f ([string]$freshnessSummary.warn_files_list))
    }

    if ($overallStatus -eq "FAIL") {
        $reason = ([string]$freshnessSummary.status_reason).Trim()
        if ([string]::IsNullOrWhiteSpace($reason)) {
            $reason = "Freshness audit did not pass."
        }
        if ($ExternalFailureHint) {
            $reason = "{0} {1}" -f $reason, $ExternalFailureHint
        }
        throw $reason.Trim()
    }

    Write-DailyLog -Level "INFO" -Message "EDGEIQ daily auto refresh completed successfully."
    Write-Host "[EDGEIQ_DAILY_AUTO_REFRESH_V1] COMPLETE"
    Write-Host "status=$finalStatus"
    Write-Host "today=$TodayDate"
    Write-Host "selected_meeting=$SelectedTrack"
    Write-Host "log=$LogPath"
    exit 0
} catch {
    Write-DailyLog -Level "ERROR" -Message $_.Exception.Message
    if ($ExternalFailureHint) {
        Write-DailyLog -Level "ERROR" -Message ("external_feed_hint={0}" -f $ExternalFailureHint)
    }
    Write-Host "[EDGEIQ_DAILY_AUTO_REFRESH_V1] FAILED"
    Write-Host "status=FAIL"
    Write-Host "today=$TodayDate"
    Write-Host "selected_meeting=$SelectedTrack"
    Write-Host "log=$LogPath"
    exit 1
} finally {
    if ($LockContext) {
        try {
            $release = Release-EdgeIQLock -ProjectRoot $ProjectRoot -LockName "EDGEIQ_DAILY_AUTO_REFRESH_V1"
            Write-DailyLog -Level "INFO" -Message ("Lock release status: {0}" -f $release.Status)
        } catch {
            Write-DailyLog -Level "ERROR" -Message ("Lock release failed: {0}" -f $_.Exception.Message)
        }
    }
}

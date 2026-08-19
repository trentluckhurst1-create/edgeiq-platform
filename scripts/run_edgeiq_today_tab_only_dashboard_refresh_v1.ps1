$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$today = (Get-Date).ToString("yyyy-MM-dd")
$blockedTracks = @("SANDOWN", "BENDIGO", "WANGARATTA", "WARRNAMBOOL")
$requiredTrack = ""
$sourceInventorySummary = ".\public\data\edgeiq_current_day_source_inventory_summary_v1.csv"
$meetingCalendar = ".\public\data\edgeiq_vic_three_day_meeting_calendar_v1.csv"
$meetingDiagnostics = ".\public\data\edgeiq_vic_three_day_meeting_diagnostics.csv"
$meetingUniverse = ".\public\data\edgeiq_vic_three_day_meeting_universe.csv"

$terminalFeed = ".\public\data\edgeiq_live_terminal_feed_v1_TAB_ONLY_TODAY.csv"
$legacyVicTerminalFeed = ".\public\data\edgeiq_vic_live_terminal_feed_v1.csv"
$legacyTerminalFeed = ".\public\data\edgeiq_live_terminal_feed_v1.csv"
$runnerBoard = ".\public\data\edgeiq_live_runner_board_v1.csv"
$activeSelector = ".\public\data\edgeiq_active_race_selector.csv"
$trackingDashboard = ".\public\data\edgeiq_model_tracking_dashboard_v1.csv"
$liveRunnerStyle = ".\public\data\edgeiq_live_runner_style_v1.csv"
$liveTrackIntel = ".\public\data\edgeiq_live_track_intelligence_v1.csv"
$trackIntel = ".\public\data\edgeiq_track_intelligence_card_v1.csv"
$speedMap = ".\public\data\edgeiq_real_speed_map_positions.csv"
$runnerIntel = ".\public\data\edgeiq_runner_intelligence_v1.csv"
$runnerIntelDiag = ".\public\data\edgeiq_runner_intelligence_v1_diagnostics.csv"
$raceCards = ".\public\data\edgeiq_race_intelligence_cards_v1.csv"
$raceBriefing = ".\public\data\edgeiq_race_briefing_v1.csv"
$raceVerdict = ".\public\data\edgeiq_race_verdict_v1.csv"
$marketIntel = ".\public\data\edgeiq_market_intelligence_v1.csv"
$horseDrawer = ".\public\data\edgeiq_horse_intelligence_drawer_v1.csv"

function Run-Python([string]$label, [string]$scriptPath) {
    Write-Host ""
    Write-Host ("=" * 100)
    Write-Host $label
    Write-Host ("=" * 100)
    $output = & python $scriptPath 2>&1
    $exitCode = $LASTEXITCODE
    foreach ($line in $output) {
        $text = ([string]$line).TrimEnd()
        if (![string]::IsNullOrWhiteSpace($text)) {
            Write-Output $text
        }
    }
    if ($exitCode -ne 0) {
        throw "Failed: $scriptPath"
    }
}

function Sync-FeedAlias([string]$sourcePath, [string]$targetPath) {
    if (!(Test-Path $sourcePath)) {
        throw "Cannot sync missing source feed: $sourcePath"
    }
    Copy-Item $sourcePath $targetPath -Force
}

function Get-TodayCalendarMeeting() {
    if (!(Test-Path $meetingCalendar)) {
        throw "Missing meeting calendar: $meetingCalendar"
    }

    $rows = @(Import-Csv $meetingCalendar)
    if ($rows.Count -eq 0) {
        throw "Meeting calendar is empty: $meetingCalendar"
    }

    $todayRow = $rows | Where-Object { ([string]$_.day_bucket).Trim().ToUpper() -eq "TODAY" } | Select-Object -First 1
    if ($null -eq $todayRow) {
        throw "Meeting calendar does not contain a TODAY row for local date $today"
    }

    $track = ([string]$todayRow.track).Trim().ToUpper()
    if ([string]::IsNullOrWhiteSpace($track)) {
        throw "Meeting calendar TODAY row has blank track: $meetingCalendar"
    }

    return $track
}

function Get-SelectedTrackFromAuditSummary() {
    if (!(Test-Path $sourceInventorySummary)) {
        throw "Missing source inventory summary: $sourceInventorySummary"
    }

    $summaryRows = @(Import-Csv $sourceInventorySummary)
    if ($summaryRows.Count -eq 0) {
        throw "Source inventory summary is empty: $sourceInventorySummary"
    }

    $selectedTrack = ([string]$summaryRows[0].selected_meeting).Trim().ToUpper()
    if ([string]::IsNullOrWhiteSpace($selectedTrack)) {
        throw "Source inventory summary selected_meeting is blank: $sourceInventorySummary"
    }

    return $selectedTrack
}

function Assert-SelectedMeetingAligned() {
    $calendarTrack = Get-TodayCalendarMeeting
    $auditTrack = Get-SelectedTrackFromAuditSummary

    if ($calendarTrack -ne $auditTrack) {
        throw "Selected meeting mismatch. calendar_today=$calendarTrack audit_selected_meeting=$auditTrack"
    }

    return $calendarTrack
}

function Assert-TodayOnlyFile([string]$path, [string]$dateColumn, [string]$trackColumn, [string]$label) {
    if (!(Test-Path $path)) {
        throw "$label missing: $path"
    }

    $rows = @(Import-Csv $path)
    if ($rows.Count -eq 0) {
        throw "$label is empty: $path"
    }

    $badDates = @($rows | Where-Object {
        $value = [string]($_.$dateColumn)
        (!$value) -or ($value.Substring(0, [Math]::Min(10, $value.Length)) -ne $today)
    })
    if ($badDates.Count -gt 0) {
        throw "$label contains rows not on local today $today"
    }

    $badTracks = @($rows | Where-Object {
        $track = ([string]($_.$trackColumn)).Trim().ToUpper()
        ($track -ne $requiredTrack) -or (($blockedTracks | Where-Object { $_ -ne $requiredTrack -and $track -match $_ }).Count -gt 0)
    })
    if ($badTracks.Count -gt 0) {
        throw "$label contains stale or non-target tracks"
    }
}

function Assert-OptionalTodayOnlyFile([string]$path, [string]$dateColumn, [string]$trackColumn, [string]$label) {
    if (!(Test-Path $path)) {
        throw "$label missing: $path"
    }

    $rows = @(Import-Csv $path)
    if ($rows.Count -eq 0) {
        return
    }

    $badDates = @($rows | Where-Object {
        $value = [string]($_.$dateColumn)
        (!$value) -or ($value.Substring(0, [Math]::Min(10, $value.Length)) -ne $today)
    })
    if ($badDates.Count -gt 0) {
        throw "$label contains rows not on local today $today"
    }

    $badTracks = @($rows | Where-Object {
        $track = ([string]($_.$trackColumn)).Trim().ToUpper()
        ($track -ne $requiredTrack) -or (($blockedTracks | Where-Object { $_ -ne $requiredTrack -and $track -match $_ }).Count -gt 0)
    })
    if ($badTracks.Count -gt 0) {
        throw "$label contains stale or non-target tracks"
    }
}

Run-Python "0 - THREE DAY MEETING CALENDAR" ".\scripts\build_edgeiq_vic_three_day_meeting_calendar_v1.py"
Run-Python "0A - THREE DAY MEETING UNIVERSE" ".\scripts\build_edgeiq_vic_three_day_meeting_universe.py"
Run-Python "0B - CURRENT DAY SOURCE INVENTORY AUDIT" ".\scripts\audit_edgeiq_current_day_source_inventory_v1.py"
$requiredTrack = Assert-SelectedMeetingAligned

Write-Host ""
Write-Host ("=" * 100)
Write-Host "0C - SELECTED MEETING"
Write-Host ("=" * 100)
Write-Host "today=$today"
Write-Host "selected_meeting=$requiredTrack"

if (Test-Path $meetingDiagnostics) {
    $todayDiag = Import-Csv $meetingDiagnostics |
        Where-Object { $_.record_type -eq "MEETING" -and $_.day_bucket -eq "TODAY" } |
        Select-Object -First 1
    if ($null -ne $todayDiag) {
        Write-Host "meeting_status=$($todayDiag.meeting_status)"
        Write-Host "dashboard_ready=$($todayDiag.dashboard_ready)"
        Write-Host "field_rows=$($todayDiag.field_rows)"
        Write-Host "field_races=$($todayDiag.field_races)"
    }
}

Run-Python "1 - TAB DIRECT API ALL ACTIVE RACES" ".\scripts\scrape_tab_all_active_races_v1.py"
Run-Python "2 - TODAY-ONLY TERMINAL FEED" ".\scripts\build_edgeiq_live_terminal_feed_v1_tab_only_today.py"

Write-Host ""
Write-Host ("=" * 100)
Write-Host "2B - SYNC LEGACY TERMINAL FEED ALIASES"
Write-Host ("=" * 100)
Sync-FeedAlias $terminalFeed $legacyVicTerminalFeed
Sync-FeedAlias $terminalFeed $legacyTerminalFeed
Write-Host "synced=$legacyVicTerminalFeed"
Write-Host "synced=$legacyTerminalFeed"

Run-Python "2C - CURRENT RACE CLASS CORRECTION V5.1" ".\scripts\build_edgeiq_current_race_class_correction_v5_1.py"
Run-Python "3A - CURRENT FIELD PROJECTION V5.2" ".\scripts\build_edgeiq_current_field_projection_v5_2.py"
Run-Python "3B - CURRENT FAIR PRICES REVIEW V5.2" ".\scripts\build_edgeiq_current_fair_prices_review_v5_2.py"

Run-Python "3C - HISTORICAL PERFORMANCE RATING V6.1 RESEARCH" ".\scripts\build_edgeiq_historical_performance_rating_v6_1_research.py"
Run-Python "3D - CURRENT FIELD PROJECTION V6.1 RESEARCH REPLAY" ".\scripts\build_edgeiq_current_field_projection_v6_1_research_replay.py"
Run-Python "3E - CURRENT FAIR PRICES V6.1 RESEARCH REPLAY" ".\scripts\build_edgeiq_current_fair_prices_v6_1_research_replay.py"
Run-Python "3F - V6.1 TAB-ONLY COMPARISON" ".\scripts\build_edgeiq_live_v6_1_research_vs_production_comparison_v1_TAB_ONLY_TODAY.py"
Run-Python "3G - LIVE RUNNER BOARD TODAY-ONLY" ".\scripts\build_edgeiq_live_runner_board_from_terminal_v1.py"
Run-Python "3H - NO PROJECTION FALLBACK ADJUSTMENT V1" ".\scripts\apply_edgeiq_no_projection_fallback_adjustment_v1.py"
Run-Python "3I - RUNNER INTELLIGENCE V1" ".\scripts\build_edgeiq_runner_intelligence_v1.py"

Run-Python "4 - MODEL TRACKING CANDIDATES" ".\scripts\build_edgeiq_model_tracking_candidates_v1.py"
Run-Python "5 - MODEL TRACKING DASHBOARD" ".\scripts\build_edgeiq_model_tracking_dashboard_v1.py"
Run-Python "6 - ACTIVE RACE SELECTOR TODAY-ONLY" ".\scripts\build_edgeiq_active_race_selector.py"
Run-Python "7 - LIVE RUNNER STYLE V1" ".\scripts\build_edgeiq_live_runner_style_v1.py"
Run-Python "8 - LIVE TRACK INTELLIGENCE V1" ".\scripts\build_edgeiq_live_track_intelligence_v1.py"
Run-Python "9 - TRACK INTELLIGENCE CARD V1" ".\scripts\build_edgeiq_track_intelligence_card_v1.py"
Run-Python "10 - REAL SPEED MAP POSITIONS" ".\scripts\build_edgeiq_real_speed_map_engine.py"
Run-Python "11 - LIVE SECTIONAL INTELLIGENCE V1" ".\scripts\build_edgeiq_live_sectional_intelligence_v1.py"
Run-Python "12 - RUNNER INTELLIGENCE V1 REFRESH" ".\scripts\build_edgeiq_runner_intelligence_v1.py"
Run-Python "13 - RACE INTELLIGENCE CARDS V1" ".\scripts\build_edgeiq_race_intelligence_cards_v1.py"
Run-Python "14 - INTELLIGENCE TERMINAL V1" ".\scripts\build_edgeiq_intelligence_terminal_v1.py"
Run-Python "15 - HORSE INTELLIGENCE DRAWER V1" ".\scripts\build_edgeiq_horse_intelligence_drawer_v1.py"

Assert-TodayOnlyFile $terminalFeed "race_date" "track" "TERMINAL FEED"
Assert-TodayOnlyFile $legacyVicTerminalFeed "race_date" "track" "LEGACY VIC TERMINAL FEED"
Assert-TodayOnlyFile $legacyTerminalFeed "race_date" "track" "LEGACY TERMINAL FEED"
Assert-TodayOnlyFile $runnerBoard "race_date" "track" "RUNNER BOARD"
Assert-TodayOnlyFile $activeSelector "race_date" "track" "ACTIVE SELECTOR"
Assert-OptionalTodayOnlyFile $trackingDashboard "race_date" "track" "TRACKING DASHBOARD"
Assert-TodayOnlyFile $liveRunnerStyle "race_date" "track" "LIVE RUNNER STYLE"
Assert-TodayOnlyFile $liveTrackIntel "race_date" "track" "LIVE TRACK INTELLIGENCE"
Assert-TodayOnlyFile $trackIntel "race_date" "track" "TRACK INTELLIGENCE CARD"
Assert-TodayOnlyFile $speedMap "race_date" "track" "REAL SPEED MAP"
Assert-TodayOnlyFile $runnerIntel "race_date" "track" "RUNNER INTELLIGENCE"
Assert-TodayOnlyFile $raceCards "race_date" "track" "RACE INTELLIGENCE CARDS"
Assert-TodayOnlyFile $raceBriefing "race_date" "track" "RACE BRIEFING"
Assert-TodayOnlyFile $raceVerdict "race_date" "track" "RACE VERDICT"
Assert-TodayOnlyFile $marketIntel "race_date" "track" "MARKET INTELLIGENCE"
Assert-TodayOnlyFile $horseDrawer "race_date" "track" "HORSE INTELLIGENCE DRAWER"

$terminalGroups = Import-Csv $terminalFeed | Group-Object race_date,track | Select-Object Count,Name
$runnerGroups = Import-Csv $runnerBoard | Group-Object race_date,track | Select-Object Count,Name
$selectorGroups = Import-Csv $activeSelector | Group-Object race_date,track | Select-Object Count,Name
$cardsGroups = Import-Csv $raceCards | Group-Object race_date,track | Select-Object Count,Name
$trackIntelGroups = Import-Csv $trackIntel | Group-Object race_date,track | Select-Object Count,Name
$trackingRows = @(Import-Csv $trackingDashboard)
$trackingPending = @($trackingRows | Where-Object { $_.status -eq "PENDING" -and $_.race_date -eq $today })
$activeRunnerStatuses = Import-Csv $runnerBoard | Where-Object { $_.runner_status -eq "ACTIVE" } | Group-Object V6_1_RESEARCH_price_status | Select-Object Count,Name
$runnerIntelDiagRows = @(Import-Csv $runnerIntelDiag)

Write-Host ""
Write-Host ("=" * 100)
Write-Host "FINAL AUDIT"
Write-Host ("=" * 100)
Write-Host "MEETING CALENDAR"
Import-Csv $meetingCalendar | Format-Table -AutoSize
Write-Host "MEETING DIAGNOSTICS"
Import-Csv $meetingDiagnostics | Where-Object { $_.record_type -eq "MEETING" -or $_.message -like "calendar_meetings_*" } | Format-Table -AutoSize
Write-Host "TERMINAL FEED"
$terminalGroups | Format-Table -AutoSize
Write-Host "RUNNER BOARD"
$runnerGroups | Format-Table -AutoSize
Write-Host "ACTIVE SELECTOR"
$selectorGroups | Format-Table -AutoSize
Write-Host "RACE INTELLIGENCE CARDS"
$cardsGroups | Format-Table -AutoSize
Write-Host "TRACK INTELLIGENCE CARD"
$trackIntelGroups | Format-Table -AutoSize
Write-Host "ACTIVE V6.1 STATUS"
$activeRunnerStatuses | Format-Table -AutoSize
Write-Host "TRACKING PENDING CANDIDATES TODAY: $($trackingPending.Count)"

if (@($terminalGroups | Where-Object { $_.Name -ne "$today, $requiredTrack" }).Count -gt 0) {
    throw "Terminal feed audit mismatch"
}
if (@($runnerGroups | Where-Object { $_.Name -ne "$today, $requiredTrack" }).Count -gt 0) {
    throw "Runner board audit mismatch"
}
if (@($selectorGroups | Where-Object { $_.Name -ne "$today, $requiredTrack" }).Count -gt 0) {
    throw "Active selector audit mismatch"
}
if (@($cardsGroups | Where-Object { $_.Name -ne "$today, $requiredTrack" }).Count -gt 0) {
    throw "Race intelligence card audit mismatch"
}
if (@($trackIntelGroups | Where-Object { $_.Name -ne "$today, $requiredTrack" }).Count -gt 0) {
    throw "Track intelligence card audit mismatch"
}

Write-Host ""
Write-Host "[EDGEIQ_TODAY_TAB_ONLY_DASHBOARD_REFRESH_V1] COMPLETE"
Write-Host "today=$today"
Write-Host "target_track=$requiredTrack"
Write-Host "terminal_rows=$((Import-Csv $terminalFeed).Count)"
Write-Host "runner_board_rows=$((Import-Csv $runnerBoard).Count)"
Write-Host "active_selector_rows=$((Import-Csv $activeSelector).Count)"
Write-Host "race_intelligence_rows=$((Import-Csv $raceCards).Count)"
Write-Host "track_intelligence_rows=$((Import-Csv $trackIntel).Count)"
Write-Host "horse_drawer_rows=$((Import-Csv $horseDrawer).Count)"
Write-Host "tracking_pending_today=$($trackingPending.Count)"

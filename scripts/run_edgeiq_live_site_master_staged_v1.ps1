param(
    [int]$RefreshSeconds = 300,
    [switch]$Loop
)

$ErrorActionPreference = "Stop"

function Stage($Name, $Command) {
    Write-Host ""
    Write-Host "================================================================================"
    Write-Host "STAGE: $Name"
    Write-Host "================================================================================"
    Invoke-Expression $Command
    if ($LASTEXITCODE -ne 0 -and $LASTEXITCODE -ne $null) {
        throw "FAILED: $Name"
    }
}

function Run-IfExists($Name, $ScriptPath) {
    if (Test-Path $ScriptPath) {
        Stage $Name "python `"$ScriptPath`""
    } else {
        Write-Host ""
        Write-Host "SKIPPED: $Name"
        Write-Host "MISSING: $ScriptPath"
    }
}

function Build-SiteLiveFeed {
    Write-Host ""
    Write-Host "================================================================================"
    Write-Host "STAGE: SITE LIVE FEED FILTER"
    Write-Host "================================================================================"

    $today = (Get-Date).ToString("yyyy-MM-dd")
    $tomorrow = (Get-Date).AddDays(1).ToString("yyyy-MM-dd")
    $nowTime = (Get-Date).AddMinutes(-10).ToString("HH:mm")

    $source = ".\public\data\edgeiq_live_runner_board_v1.csv"

    if (!(Test-Path $source)) {
        throw "Missing $source"
    }

    $rows = Import-Csv $source

    $live = $rows | Where-Object {
        ($_.race_date -eq $tomorrow) -or
        ($_.race_date -eq $today -and $_.race_time -ge $nowTime)
    }

    $resultsQueue = $rows | Where-Object {
        ($_.race_date -lt $today) -or
        ($_.race_date -eq $today -and $_.race_time -lt $nowTime)
    }

    $live | Export-Csv ".\public\data\edgeiq_site_live_today_tomorrow_v1.csv" -NoTypeInformation
    $resultsQueue | Export-Csv ".\public\data\edgeiq_site_results_queue_v1.csv" -NoTypeInformation

    Copy-Item ".\public\data\edgeiq_site_live_today_tomorrow_v1.csv" ".\public\data\edgeiq_live_terminal_feed_v1.csv" -Force
    Copy-Item ".\public\data\edgeiq_site_live_today_tomorrow_v1.csv" ".\public\data\edgeiq_vic_live_terminal_feed_v1.csv" -Force

    Write-Host "LIVE_ROWS:" @($live).Count
    Write-Host "RESULTS_QUEUE_ROWS:" @($resultsQueue).Count
}

function Coverage {
    Write-Host ""
    Write-Host "================================================================================"
    Write-Host "STAGE: COVERAGE"
    Write-Host "================================================================================"

    $board = Import-Csv ".\public\data\edgeiq_live_runner_board_v1.csv"
    $site = Import-Csv ".\public\data\edgeiq_site_live_today_tomorrow_v1.csv"

    [PSCustomObject]@{
        file = "edgeiq_live_runner_board_v1.csv"
        rows = @($board).Count
        with_live_price = @($board | Where-Object { $_.live_price -ne "" -and $_.live_price -ne $null }).Count
        missing_live_price = @($board | Where-Object { $_.live_price -eq "" -or $_.live_price -eq $null }).Count
    } | Format-Table -AutoSize

    [PSCustomObject]@{
        file = "edgeiq_site_live_today_tomorrow_v1.csv"
        rows = @($site).Count
        with_live_price = @($site | Where-Object { $_.live_price -ne "" -and $_.live_price -ne $null }).Count
        missing_live_price = @($site | Where-Object { $_.live_price -eq "" -or $_.live_price -eq $null }).Count
    } | Format-Table -AutoSize

    Write-Host ""
    Write-Host "LIVE PRICE SOURCES:"
    $board | Group-Object live_price_source | Sort-Object Count -Descending | Format-Table Name,Count -AutoSize
}

function Run-Cycle {
    Write-Host ""
    Write-Host "################################################################################"
    Write-Host "EDGEIQ LIVE REFRESH START:" (Get-Date)
    Write-Host "################################################################################"

    Run-IfExists "1 - VIC MEETING UNIVERSE" ".\scripts\build_edgeiq_vic_three_day_meeting_universe.py"

    Run-IfExists "2 - SPORTSBET LIVE MARKET" ".\scripts\capture_sportsbet_live_market_v1.py"

    Run-IfExists "3 - SPORTSBET FULL DAY MARKET" ".\scripts\build_sportsbet_full_day_racecard_capture_v5_2.py"

    Run-IfExists "4 - TAB URL DISCOVERY" ".\scripts\find_tab_vic_thoroughbred_urls_v1.py"

    Run-IfExists "5 - TAB RACECARDS" ".\scripts\scrape_tab_vic_racecards_v1.py"

    Run-IfExists "6 - TAB MARKET" ".\scripts\build_edgeiq_tab_market_v1.py"

    Run-IfExists "7 - FAIR PRICES REVIEW V5.2" ".\scripts\build_edgeiq_current_fair_prices_review_v5_2.py"

    Run-IfExists "8 - PROBABILITY ENGINE V3" ".\scripts\build_edgeiq_probability_engine_v3.py"

    Run-IfExists "9 - LIVE TERMINAL FEED" ".\scripts\build_edgeiq_live_terminal_feed_v1.py"

    Run-IfExists "10 - LIVE RUNNER BOARD" ".\scripts\build_edgeiq_live_runner_board_v1.py"

    Run-IfExists "11 - TAB PRICE PATCH" ".\scripts\patch_edgeiq_live_runner_board_tab_prices_v1.py"

    Run-IfExists "12 - NO HISTORY GOVERNANCE" ".\scripts\build_edgeiq_no_history_governance_v1.py"

    Run-IfExists "13 - LIVE RUNNER BOARD GOVERNED" ".\scripts\build_edgeiq_live_runner_board_governed_v1.py"

    Run-IfExists "14 - FIRST STARTER INTELLIGENCE" ".\scripts\build_edgeiq_first_starter_intelligence_v1.py"

    Run-IfExists "15 - LIVE TRACK INTELLIGENCE" ".\scripts\build_edgeiq_live_track_intelligence_v1.py"

    Run-IfExists "16 - TRACK INTELLIGENCE CARD" ".\scripts\build_edgeiq_track_intelligence_card_v1.py"

    Run-IfExists "17 - HORSE INTELLIGENCE DRAWER" ".\scripts\build_edgeiq_horse_intelligence_drawer_v1.py"

    Build-SiteLiveFeed

    Coverage

    Write-Host ""
    Write-Host "################################################################################"
    Write-Host "EDGEIQ LIVE REFRESH COMPLETE:" (Get-Date)
    Write-Host "################################################################################"
}

if ($Loop) {
    while ($true) {
        Run-Cycle
        Start-Sleep -Seconds $RefreshSeconds
    }
} else {
    Run-Cycle
}

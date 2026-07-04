param(
    [int]$RefreshSeconds = 300
)

$ErrorActionPreference = "Stop"

function Stage($Name, $ScriptPath) {
    Write-Host ""
    Write-Host "================================================================================"
    Write-Host "STAGE: $Name"
    Write-Host "SCRIPT: $ScriptPath"
    Write-Host "================================================================================"

    if (Test-Path $ScriptPath) {
        python $ScriptPath
        if ($LASTEXITCODE -ne 0) {
            throw "FAILED: $Name"
        }
    } else {
        Write-Host "SKIPPED - missing script"
    }
}

function Copy-IfExists($From, $To) {
    if (Test-Path $From) {
        Copy-Item $From $To -Force
    }
}

function Build-LiveSiteFeed {
    Write-Host ""
    Write-Host "================================================================================"
    Write-Host "STAGE: BUILD SITE LIVE FEED - TODAY/TOMORROW ONLY, REMOVE COMPLETED"
    Write-Host "================================================================================"

    $today = (Get-Date).ToString("yyyy-MM-dd")
    $tomorrow = (Get-Date).AddDays(1).ToString("yyyy-MM-dd")
    $nowTime = (Get-Date).AddMinutes(-10).ToString("HH:mm")

    $source = ".\public\data\edgeiq_live_runner_board_v1.csv"

    if (!(Test-Path $source)) {
        throw "Missing live runner board: $source"
    }

    $rows = Import-Csv $source

    $live = $rows | Where-Object {
        (
            $_.race_date -eq $tomorrow
        ) -or (
            $_.race_date -eq $today -and
            $_.race_time -ge $nowTime
        )
    }

    $completed = $rows | Where-Object {
        $_.race_date -lt $today -or
        (
            $_.race_date -eq $today -and
            $_.race_time -lt $nowTime
        )
    }

    $live | Export-Csv ".\public\data\edgeiq_site_live_today_tomorrow_v1.csv" -NoTypeInformation
    $completed | Export-Csv ".\public\data\edgeiq_site_results_queue_v1.csv" -NoTypeInformation

    Copy-Item ".\public\data\edgeiq_site_live_today_tomorrow_v1.csv" ".\public\data\edgeiq_live_terminal_feed_v1.csv" -Force
    Copy-Item ".\public\data\edgeiq_site_live_today_tomorrow_v1.csv" ".\public\data\edgeiq_vic_live_terminal_feed_v1.csv" -Force

    Write-Host "LIVE ROWS:" @($live).Count
    Write-Host "RESULTS QUEUE ROWS:" @($completed).Count
}

function Build-PriceCoverageSummary {
    Write-Host ""
    Write-Host "================================================================================"
    Write-Host "STAGE: LIVE PRICE COVERAGE SUMMARY"
    Write-Host "================================================================================"

    $f = ".\public\data\edgeiq_live_runner_board_v1.csv"

    if (Test-Path $f) {
        $rows = Import-Csv $f
        $total = @($rows).Count
        $priced = @($rows | Where-Object {
            $_.live_price -ne "" -and $_.live_price -ne $null
        }).Count

        [PSCustomObject]@{
            file = $f
            rows = $total
            with_live_price = $priced
            missing_live_price = $total - $priced
        } | Format-Table -AutoSize
    }
}

function Run-OneCycle {
    Write-Host ""
    Write-Host "################################################################################"
    Write-Host "EDGEIQ LIVE SITE REFRESH START:" (Get-Date)
    Write-Host "################################################################################"

    Stage "1 - VIC MEETING UNIVERSE" ".\scripts\build_edgeiq_vic_three_day_meeting_universe.py"

    Stage "2 - SPORTSBet LIVE MARKET CAPTURE" ".\scripts\capture_sportsbet_live_market_v1.py"

    Stage "3 - SPORTSBET FULL DAY RACECARD CAPTURE V5.2" ".\scripts\build_sportsbet_full_day_racecard_capture_v5_2.py"

    Stage "4 - FAIR PRICES REVIEW V5.2" ".\scripts\build_edgeiq_current_fair_prices_review_v5_2.py"

    Stage "5 - PROBABILITY ENGINE V3" ".\scripts\build_edgeiq_probability_engine_v3.py"

    Stage "6 - LIVE TERMINAL FEED V1" ".\scripts\build_edgeiq_live_terminal_feed_v1.py"

    Stage "7 - LIVE RUNNER BOARD V1" ".\scripts\build_edgeiq_live_runner_board_v1.py"

    Stage "8 - NO HISTORY GOVERNANCE" ".\scripts\build_edgeiq_no_history_governance_v1.py"

    Stage "9 - LIVE RUNNER BOARD GOVERNED" ".\scripts\build_edgeiq_live_runner_board_governed_v1.py"

    Stage "10 - FIRST STARTER INTELLIGENCE" ".\scripts\build_edgeiq_first_starter_intelligence_v1.py"

    Stage "11 - LIVE TRACK INTELLIGENCE" ".\scripts\build_edgeiq_live_track_intelligence_v1.py"

    Stage "12 - TRACK INTELLIGENCE CARD" ".\scripts\build_edgeiq_track_intelligence_card_v1.py"

    Stage "13 - HORSE INTELLIGENCE DRAWER" ".\scripts\build_edgeiq_horse_intelligence_drawer_v1.py"

    Build-LiveSiteFeed

    Build-PriceCoverageSummary

    Write-Host ""
    Write-Host "################################################################################"
    Write-Host "EDGEIQ LIVE SITE REFRESH COMPLETE:" (Get-Date)
    Write-Host "################################################################################"
}

Run-OneCycle

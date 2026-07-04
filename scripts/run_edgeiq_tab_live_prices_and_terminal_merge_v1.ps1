param(
    [int]$DefaultRefreshSeconds = 60
)

$ErrorActionPreference = "Continue"

$tabScraper      = ".\scripts\scrape_tab_single_race_v1.py"
$tabOutput       = ".\public\data\edgeiq_tab_live_prices_direct_v1.csv"
$tabUrlsCsv      = ".\public\data\edgeiq_tab_vic_thoroughbred_urls_v1.csv"
$singleRaceCsv   = ".\public\data\edgeiq_tab_single_race_v1.csv"
$terminalFeed    = ".\public\data\edgeiq_live_terminal_feed_v1.csv"
$mergedTerminal  = ".\public\data\edgeiq_live_terminal_feed_v1_updated.csv"

function Canon($x) {
    if ($null -eq $x) { return "" }
    return (($x.ToString().ToUpper()) -replace "\([^)]*\)", "" -replace "[^A-Z0-9]", "")
}

function Get-TabUrls {
    $today = (Get-Date).ToString("yyyy-MM-dd")
    $tomorrow = (Get-Date).AddDays(1).ToString("yyyy-MM-dd")

    if (!(Test-Path $tabUrlsCsv)) {
        Write-Host "MISSING TAB URL CSV: $tabUrlsCsv"
        return @()
    }

    return @(
        Import-Csv $tabUrlsCsv |
        Where-Object { $_.meeting_date -eq $today -or $_.meeting_date -eq $tomorrow } |
        ForEach-Object {
            if ($_.href -ne $null -and $_.href -ne "") { $_.href }
            elseif ($_.tab_frontend_url -ne $null -and $_.tab_frontend_url -ne "") { $_.tab_frontend_url }
            elseif ($_.tab_url -ne $null -and $_.tab_url -ne "") { $_.tab_url }
        } |
        Where-Object { $_ -ne $null -and $_ -ne "" } |
        Sort-Object -Unique
    )
}

function Merge-Tab-Into-Terminal {
    if (!(Test-Path $terminalFeed)) {
        Write-Host "MISSING TERMINAL FEED: $terminalFeed"
        return
    }

    if (!(Test-Path $tabOutput)) {
        Write-Host "MISSING TAB OUTPUT: $tabOutput"
        return
    }

    $terminal = Import-Csv $terminalFeed
    $tabData = Import-Csv $tabOutput

    $tabLookup = @{}
    foreach ($t in $tabData) {
        $key = "$(Canon $t.meeting_date)|$(Canon $t.meeting_name)|$($t.race_no)|$(Canon $t.horse)"
        if (!$tabLookup.ContainsKey($key)) {
            $tabLookup[$key] = $t
        }
    }

    $merged = foreach ($row in $terminal) {
        $key = "$(Canon $row.race_date)|$(Canon $row.track)|$($row.race_no)|$(Canon $row.horse)"

        if ($tabLookup.ContainsKey($key)) {
            $t = $tabLookup[$key]

            $row | Add-Member -NotePropertyName tab_fixed_win -NotePropertyValue $t.tab_fixed_win -Force
            $row | Add-Member -NotePropertyName tab_fixed_place -NotePropertyValue $t.tab_fixed_place -Force
            $row | Add-Member -NotePropertyName tab_fixed_betting_status -NotePropertyValue $t.tab_fixed_betting_status -Force
            $row | Add-Member -NotePropertyName tab_live_price_source -NotePropertyValue "TAB_SINGLE_RACE_API" -Force

            if (
                ($row.live_price -eq $null -or $row.live_price -eq "" -or $row.live_price -eq "-") -and
                ($t.tab_fixed_win -ne $null -and $t.tab_fixed_win -ne "" -and $t.tab_fixed_win -ne "0")
            ) {
                $row | Add-Member -NotePropertyName live_price -NotePropertyValue $t.tab_fixed_win -Force
                $row | Add-Member -NotePropertyName live_price_source -NotePropertyValue "TAB_FIXED_WIN" -Force
            }
        }

        $row
    }

    $merged | Export-Csv $mergedTerminal -NoTypeInformation

    Write-Host "MERGED TERMINAL WRITTEN: $mergedTerminal"
    Import-Csv $mergedTerminal |
    Where-Object { $_.tab_fixed_win -ne "" -and $_.tab_fixed_win -ne $null } |
    Measure-Object
}

function Run-Tab-Cycle {
    Write-Host ""
    Write-Host "============================================================"
    Write-Host "TAB LIVE PRICE CYCLE: $(Get-Date)"
    Write-Host "============================================================"

    $tabUrls = Get-TabUrls

    Write-Host "TAB URLS FOUND:" $tabUrls.Count

    if ($tabUrls.Count -eq 0) {
        return
    }

    $allRaceData = @()

    foreach ($url in $tabUrls) {
        Write-Host "FETCH:" $url

        try {
            python $tabScraper --url $url

            if (Test-Path $singleRaceCsv) {
                $rows = @(Import-Csv $singleRaceCsv)
                Write-Host "ROWS:" $rows.Count
                if ($rows.Count -gt 0) {
                    $allRaceData += $rows
                }
            } else {
                Write-Host "NO SINGLE RACE CSV WRITTEN"
            }
        }
        catch {
            Write-Host ("ERROR FETCHING " + $url + " :: " + $_.Exception.Message)
        }
    }

    if ($allRaceData.Count -gt 0) {
        $allRaceData |
        Sort-Object meeting_date,meeting_name,race_no,runner_no,horse -Unique |
        Export-Csv $tabOutput -NoTypeInformation

        Write-Host "TAB LIVE OUTPUT WRITTEN:" $tabOutput
        Write-Host "TAB LIVE ROWS:" $allRaceData.Count
    } else {
        Write-Host "NO TAB DATA FETCHED"
    }

    Merge-Tab-Into-Terminal
}

Run-Tab-Cycle

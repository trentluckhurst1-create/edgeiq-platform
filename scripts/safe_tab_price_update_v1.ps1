$ErrorActionPreference = "Continue"

Write-Host "`n=== SAFE TAB PRICE UPDATE ==="

$tabFile = ".\public\data\edgeiq_tab_live_prices_direct_v1.csv"
$backup = ".\public\data\edgeiq_tab_live_prices_direct_v1_LAST_GOOD.csv"

if ((Test-Path $tabFile) -and ((Import-Csv $tabFile -ErrorAction SilentlyContinue | Measure-Object).Count -gt 0)) {
    Copy-Item $tabFile $backup -Force
    Write-Host "Backed up current TAB file."
}

python ".\scripts\scrape_tab_all_active_races_v1.py"

$newRows = 0
if (Test-Path $tabFile) {
    $newRows = (Import-Csv $tabFile -ErrorAction SilentlyContinue | Measure-Object).Count
}

if ($newRows -eq 0 -and (Test-Path $backup)) {
    Write-Host "Scrape returned zero rows. Restoring last good TAB prices."
    Copy-Item $backup $tabFile -Force
}

powershell -ExecutionPolicy Bypass -File ".\scripts\merge_edgeiq_tab_prices_into_terminal_v2.ps1"
powershell -ExecutionPolicy Bypass -File ".\scripts\run_edgeiq_live_intelligence_full_rebuild_v1.ps1"
powershell -ExecutionPolicy Bypass -File ".\scripts\mark_no_live_races_clean_v1.ps1"

Write-Host "`n=== FINAL LIVE COVERAGE ==="
Import-Csv ".\public\data\edgeiq_live_runner_board_governed_v1.csv" |
Group-Object track,race_no |
ForEach-Object {
    $g = $_.Group
    [PSCustomObject]@{
        track = $g[0].track
        race_no = $g[0].race_no
        runners = $g.Count
        live = ($g | Where-Object { $_.live_price }).Count
        no_live = ($g | Where-Object { $_.execution_action -eq "NO_LIVE" }).Count
    }
} |
Sort-Object track,{[int]$_.race_no} |
Format-Table -AutoSize

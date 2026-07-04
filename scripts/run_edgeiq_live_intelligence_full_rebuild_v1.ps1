$ErrorActionPreference = "Stop"

Write-Host "`n=== EDGEIQ LIVE INTELLIGENCE FULL REBUILD ==="

python ".\scripts\build_edgeiq_live_runner_board_from_terminal_v1.py"
python ".\scripts\build_edgeiq_live_runner_board_governed_v1.py"
python ".\scripts\build_edgeiq_limited_data_market_adjusted_v1.py"
python ".\scripts\promote_limited_data_price_to_runner_board_v1.py"

# Rebuild governed again after price promotion
python ".\scripts\build_edgeiq_live_runner_board_governed_v1.py"
python ".\scripts\promote_limited_data_price_to_runner_board_v1.py"

Write-Host "`n=== VERIFY EVERY RACE HAS RUNNERS / LIVE / EDGEIQ PRICE ==="

$rows = Import-Csv ".\public\data\edgeiq_live_runner_board_governed_v1.csv"

$summary =
$rows |
Group-Object track,race_no |
ForEach-Object {
    $g = $_.Group
    [PSCustomObject]@{
        track = $g[0].track
        race_no = $g[0].race_no
        runners = $g.Count
        live_prices = ($g | Where-Object { $_.live_price -ne "" }).Count
        edgeiq_prices = ($g | Where-Object { $_.fair_price -ne "" }).Count
        limited_scores = ($g | Where-Object { $_.limited_data_factor_score_v1 -ne "" }).Count
        decisions = ($g | Where-Object { $_.execution_action -ne "" }).Count
    }
}

$summary |
Sort-Object track,{[int]$_.race_no} |
Format-Table -AutoSize

$summary |
Export-Csv ".\public\data\edgeiq_live_intelligence_full_rebuild_check_v1.csv" -NoTypeInformation

Write-Host "`n=== ANY BROKEN RACES ==="

$summary |
Where-Object {
    $_.runners -eq 0 -or
    $_.live_prices -eq 0 -or
    $_.edgeiq_prices -eq 0 -or
    $_.limited_scores -eq 0
} |
Format-Table -AutoSize

Write-Host "`n=== RESTART VITE ==="

Get-Process node -ErrorAction SilentlyContinue | Stop-Process -Force
Get-Process esbuild -ErrorAction SilentlyContinue | Stop-Process -Force

npm run dev

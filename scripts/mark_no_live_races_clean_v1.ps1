$ErrorActionPreference = "Stop"

$files = @(
  ".\public\data\edgeiq_live_runner_board_v1.csv",
  ".\public\data\edgeiq_live_runner_board_governed_v1.csv"
)

foreach ($f in $files) {
    $rows = Import-Csv $f

    foreach ($r in $rows) {
        if ([string]::IsNullOrWhiteSpace($r.live_price)) {
            $r.limited_data_factor_score_v1 = "NO LIVE"
            $r.limited_data_decision_v1 = "NO LIVE"
            $r.edgeiq_price_source_v1 = "WAITING MARKET"
            $r.execution_action = "NO_LIVE"
            if ($r.PSObject.Properties.Name -contains "execution_action_governed") {
                $r.execution_action_governed = "NO_LIVE"
            }
        }
    }

    $rows | Export-Csv $f -NoTypeInformation
}

Write-Host "`n=== VERIFY STATUS BY RACE ==="
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
        source = (($g | Select-Object -ExpandProperty edgeiq_price_source_v1 -Unique) -join ", ")
    }
} |
Sort-Object track,{[int]$_.race_no} |
Format-Table -AutoSize

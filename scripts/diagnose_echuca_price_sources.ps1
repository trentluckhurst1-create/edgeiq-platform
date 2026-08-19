$ErrorActionPreference = "SilentlyContinue"

$results = @()

Get-ChildItem ".\public\data" -File -Filter "*.csv" | ForEach-Object {
    $path = $_.FullName
    $rows = Import-Csv $path

    if ($null -eq $rows -or $rows.Count -eq 0) {
        return
    }

    $headers = ($rows[0].PSObject.Properties.Name -join "|")

    $hasEchuca = $false

    foreach ($r in $rows) {
        $names = $r.PSObject.Properties.Name

        if (
            (($names -contains "track") -and ($r.track -match "ECHUCA")) -or
            (($names -contains "meeting_name") -and ($r.meeting_name -match "ECHUCA")) -or
            (($names -contains "race_key") -and ($r.race_key -match "ECHUCA"))
        ) {
            $hasEchuca = $true
            break
        }
    }

    if (
        $hasEchuca -and
        ($headers -match "prob|rated_probability|edgeiq_probability|sportsbet_price|live_price|market_price|ui_price|price_win")
    ) {
        $results += [PSCustomObject]@{
            File    = $_.Name
            Rows    = $rows.Count
            HasProb = ($headers -match "prob|rated_probability|edgeiq_probability")
            HasLive = ($headers -match "sportsbet_price|live_price|market_price|ui_price|price_win")
        }
    }
}

$results | Sort-Object File | Format-Table -AutoSize

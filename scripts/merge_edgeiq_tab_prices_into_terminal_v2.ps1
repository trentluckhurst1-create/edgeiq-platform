$terminalFeed   = ".\public\data\edgeiq_live_terminal_feed_v1.csv"
$tabOutput      = ".\public\data\edgeiq_tab_live_prices_direct_v1.csv"
$mergedTerminal = ".\public\data\edgeiq_live_terminal_feed_v1_updated.csv"

function Canon($x) {
    if ($null -eq $x) { return "" }
    $s = (($x.ToString().ToUpper()) -replace "\([^)]*\)", "" -replace "[^A-Z0-9]", "")
    if ($s -eq "SANDOWNHILLSIDE") { return "SANDOWN" }
    return $s
}

$terminal = Import-Csv $terminalFeed
$tabData = Import-Csv $tabOutput

$tabLookup = @{}
foreach ($t in $tabData) {
    $key = "$(Canon $t.meeting_date)|$(Canon $t.meeting_name)|$($t.race_no)|$(Canon $t.horse)"
    $tabLookup[$key] = $t
}

$matched = 0

$merged = foreach ($row in $terminal) {
    $key = "$(Canon $row.race_date)|$(Canon $row.track)|$($row.race_no)|$(Canon $row.horse)"

    if ($tabLookup.ContainsKey($key)) {
        $matched++
        $t = $tabLookup[$key]

        $row | Add-Member -NotePropertyName tab_fixed_win -NotePropertyValue $t.tab_fixed_win -Force
        $row | Add-Member -NotePropertyName tab_fixed_place -NotePropertyValue $t.tab_fixed_place -Force
        $row | Add-Member -NotePropertyName tab_fixed_betting_status -NotePropertyValue $t.tab_fixed_betting_status -Force
        $row | Add-Member -NotePropertyName tab_live_price_source -NotePropertyValue "TAB_SINGLE_RACE_API" -Force

        if ($t.tab_fixed_win -ne "" -and $t.tab_fixed_win -ne "0") {
            $row | Add-Member -NotePropertyName live_price -NotePropertyValue $t.tab_fixed_win -Force
            $row | Add-Member -NotePropertyName live_price_source -NotePropertyValue "TAB_FIXED_WIN" -Force
        }
    }

    $row
}

$merged | Export-Csv $mergedTerminal -NoTypeInformation
Copy-Item $mergedTerminal $terminalFeed -Force

Write-Host "MATCHED TAB ROWS:" $matched
Write-Host "UPDATED SITE FEED:" $terminalFeed

Import-Csv $terminalFeed |
Where-Object { $_.tab_fixed_win -ne "" -and $_.tab_fixed_win -ne $null } |
Select-Object track,race_no,horse,live_price,tab_fixed_win,live_price_source |
Format-Table -AutoSize

$ErrorActionPreference = "Continue"

$Root = "C:\Users\trent\OneDrive\Documents\horse_racing_model\dashboard\racing-dashboard"
Set-Location $Root

$RunStamp = Get-Date -Format "yyyyMMdd_HHmmss"
$LogDir = Join-Path $Root "logs"
$MainLog = Join-Path $LogDir "edgeiq_graphql_2026_jan_jun_harvest_$RunStamp.log"

$Months = @("JAN2026","FEB2026","MAR2026","APR2026","MAY2026","JUN2026")

function Log {
    param([string]$Message)
    $line = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') | $Message"
    Add-Content -Path $MainLog -Value $line
    Write-Host $line
}

Log "EDGEIQ GRAPHQL 2026 JAN-JUN HARVEST STARTED"

foreach ($Code in $Months) {
    $MonthLog = Join-Path $LogDir "edgeiq_graphql_${Code}_harvest_$RunStamp.log"
    Log "START $Code"
    node ".\outputs\tmp\edgeiq_graphql_month_harvester_v1.cjs" $Code *> $MonthLog

    if ($LASTEXITCODE -ne 0) {
        Log "FAILED $Code exit_code=$LASTEXITCODE"
    } else {
        Log "DONE $Code"
    }
}

Log "EDGEIQ GRAPHQL 2026 JAN-JUN HARVEST COMPLETE"

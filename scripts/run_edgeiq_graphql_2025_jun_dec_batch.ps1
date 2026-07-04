$ErrorActionPreference = "Continue"

$Root = "C:\Users\trent\OneDrive\Documents\horse_racing_model\dashboard\racing-dashboard"
Set-Location $Root

$RunStamp = Get-Date -Format "yyyyMMdd_HHmmss"
$LogDir = Join-Path $Root "logs"
$MainLog = Join-Path $LogDir "edgeiq_graphql_2025_jun_dec_batch_$RunStamp.log"

$Months = @(
    "JUN2025",
    "JUL2025",
    "AUG2025",
    "SEP2025",
    "OCT2025",
    "NOV2025",
    "DEC2025"
)

function Write-EdgeLog {
    param([string]$Message)
    $line = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') | $Message"
    Add-Content -Path $MainLog -Value $line
    Write-Host $line
}

Write-EdgeLog "EDGEIQ GRAPHQL 2025 JUN-DEC BATCH STARTED"
Write-EdgeLog "MODE=DATA_ACQUISITION_ONLY"
Write-EdgeLog "NO_SCORING=TRUE"
Write-EdgeLog "NO_DNA=TRUE"
Write-EdgeLog "NO_PRICING=TRUE"

foreach ($MonthCode in $Months) {
    Write-EdgeLog "-----"
    Write-EdgeLog "MONTH START: $MonthCode"

    $MonthLog = Join-Path $LogDir "edgeiq_graphql_${MonthCode}_harvest_$RunStamp.log"

    try {
        node ".\outputs\tmp\edgeiq_graphql_month_harvester_v1.cjs" $MonthCode *> $MonthLog

        if ($LASTEXITCODE -ne 0) {
            Write-EdgeLog "FAILED: $MonthCode exit_code=$LASTEXITCODE"
            Write-EdgeLog "CHECK LOG: $MonthLog"
            continue
        }

        Write-EdgeLog "HARVEST COMPLETE: $MonthCode"
        Write-EdgeLog "LOG: $MonthLog"
    }
    catch {
        Write-EdgeLog "ERROR: $MonthCode"
        Write-EdgeLog $_.Exception.Message
        continue
    }
}

Write-EdgeLog "EDGEIQ GRAPHQL 2025 JUN-DEC BATCH COMPLETE"

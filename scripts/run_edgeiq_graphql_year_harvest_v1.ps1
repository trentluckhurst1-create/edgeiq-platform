param(
    [Parameter(Mandatory=$true)]
    [int]$Year
)

$ErrorActionPreference = "Continue"

$Root = "C:\Users\trent\OneDrive\Documents\horse_racing_model\dashboard\racing-dashboard"
Set-Location $Root

$LogDir = Join-Path $Root "logs"
New-Item -ItemType Directory -Force $LogDir | Out-Null

$RunStamp = Get-Date -Format "yyyyMMdd_HHmmss"
$MainLog = Join-Path $LogDir "edgeiq_graphql_year_${Year}_harvest_$RunStamp.log"

$Months = @(
    @{ Code="JAN$Year"; Month="january" },
    @{ Code="FEB$Year"; Month="february" },
    @{ Code="MAR$Year"; Month="march" },
    @{ Code="APR$Year"; Month="april" },
    @{ Code="MAY$Year"; Month="may" },
    @{ Code="JUN$Year"; Month="june" },
    @{ Code="JUL$Year"; Month="july" },
    @{ Code="AUG$Year"; Month="august" },
    @{ Code="SEP$Year"; Month="september" },
    @{ Code="OCT$Year"; Month="october" },
    @{ Code="NOV$Year"; Month="november" },
    @{ Code="DEC$Year"; Month="december" }
)

function Log {
    param([string]$Message)
    $line = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') | $Message"
    Add-Content -Path $MainLog -Value $line
    Write-Host $line
}

Log "EDGEIQ GRAPHQL YEAR HARVEST STARTED: $Year"
Log "MODE=DATA_ACQUISITION_ONLY"
Log "NO_SCORING=TRUE"
Log "NO_DNA=TRUE"
Log "NO_PRICING=TRUE"

foreach ($m in $Months) {
    $Code = $m.Code
    $MonthName = $m.Month

    $Manifest = ".\public\data\edgeiq_manifest_$Code.json"
    $Output = ".\public\data\edgeiq_graphql_${MonthName}_${Year}_results_v1.csv"

    if (!(Test-Path $Manifest)) {
        Log "SKIP $Code missing manifest"
        continue
    }

    if (Test-Path $Output) {
        Log "SKIP $Code output already exists: $Output"
        continue
    }

    $MonthLog = Join-Path $LogDir "edgeiq_graphql_${Code}_harvest_$RunStamp.log"

    Log "START $Code"

    node ".\outputs\tmp\edgeiq_graphql_month_harvester_v1.cjs" $Code *> $MonthLog

    if ($LASTEXITCODE -ne 0) {
        Log "FAILED $Code exit_code=$LASTEXITCODE"
        Log "CHECK $MonthLog"
    } else {
        Log "DONE $Code"
    }
}

Log "EDGEIQ GRAPHQL YEAR HARVEST COMPLETE: $Year"

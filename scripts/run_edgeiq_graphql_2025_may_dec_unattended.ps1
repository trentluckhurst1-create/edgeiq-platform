$ErrorActionPreference = "Continue"

$Root = "C:\Users\trent\OneDrive\Documents\horse_racing_model\dashboard\racing-dashboard"
Set-Location $Root

$LogDir = Join-Path $Root "logs"
New-Item -ItemType Directory -Force $LogDir | Out-Null

$RunStamp = Get-Date -Format "yyyyMMdd_HHmmss"
$MainLog = Join-Path $LogDir "edgeiq_graphql_2025_may_dec_unattended_$RunStamp.log"

function Write-EdgeLog {
    param([string]$Message)
    $line = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') | $Message"
    Add-Content -Path $MainLog -Value $line
    Write-Host $line
}

Write-EdgeLog "EDGEIQ GRAPHQL 2025 MAY-DEC UNATTENDED ORCHESTRATOR STARTED"
Write-EdgeLog "ROOT=$Root"
Write-EdgeLog "MODE=DATA_ACQUISITION_ONLY"
Write-EdgeLog "NO_SCORING=TRUE"
Write-EdgeLog "NO_DNA=TRUE"
Write-EdgeLog "NO_PRICING=TRUE"

$Months = @(
    @{ Code="MAY2025"; Name="May 2025" },
    @{ Code="JUN2025"; Name="June 2025" },
    @{ Code="JUL2025"; Name="July 2025" },
    @{ Code="AUG2025"; Name="August 2025" },
    @{ Code="SEP2025"; Name="September 2025" },
    @{ Code="OCT2025"; Name="October 2025" },
    @{ Code="NOV2025"; Name="November 2025" },
    @{ Code="DEC2025"; Name="December 2025" }
)

foreach ($m in $Months) {
    $code = $m.Code
    $name = $m.Name

    Write-EdgeLog "-----"
    Write-EdgeLog "MONTH START: $name"

    $harvester = Join-Path $Root "scripts\edgeiq_graphql_${code}_harvester.cjs"
    $manifest = Join-Path $Root "public\data\edgeiq_manifest_${code}.json"
    $expectedCsv = Join-Path $Root "public\data\edgeiq_graphql_$($code.ToLower())_results_v1.csv"

    if (!(Test-Path $harvester)) {
        Write-EdgeLog "MISSING HARVESTER: $harvester"
        Write-EdgeLog "SKIPPED: $name"
        continue
    }

    if (!(Test-Path $manifest)) {
        Write-EdgeLog "WARNING: Manifest not found: $manifest"
        Write-EdgeLog "Harvester may create it or fail depending on script design."
    }

    $MonthLog = Join-Path $LogDir "edgeiq_graphql_${code}_harvest_$RunStamp.log"

    Write-EdgeLog "RUNNING HARVESTER: $harvester"
    Write-EdgeLog "MONTH LOG: $MonthLog"

    try {
        node $harvester *> $MonthLog

        if ($LASTEXITCODE -ne 0) {
            Write-EdgeLog "FAILED: $name exit_code=$LASTEXITCODE"
            continue
        }

        Write-EdgeLog "HARVESTER COMPLETE: $name"

        if (Test-Path $expectedCsv) {
            $rowCount = (Import-Csv $expectedCsv | Measure-Object).Count
            Write-EdgeLog "OUTPUT FOUND: $expectedCsv rows=$rowCount"
        } else {
            Write-EdgeLog "WARNING: Expected CSV not found after harvest: $expectedCsv"
        }
    }
    catch {
        Write-EdgeLog "ERROR: $name"
        Write-EdgeLog $_.Exception.Message
        continue
    }

    Write-EdgeLog "MONTH END: $name"
}

Write-EdgeLog "EDGEIQ GRAPHQL 2025 MAY-DEC UNATTENDED ORCHESTRATOR COMPLETE"

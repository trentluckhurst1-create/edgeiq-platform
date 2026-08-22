$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$Bucket = if ($env:EDGEIQ_R2_BUCKET) { $env:EDGEIQ_R2_BUCKET } else { 'edgeiq-runtime-data' }

$RequiredEnv = @(
    'CLOUDFLARE_ACCOUNT_ID',
    'CLOUDFLARE_R2_API_TOKEN'
)

foreach ($Name in $RequiredEnv) {
    $Item = Get-Item "Env:$Name" -ErrorAction SilentlyContinue
    if ($null -eq $Item -or [string]::IsNullOrWhiteSpace($Item.Value)) {
        throw "MISSING_ENV=$Name"
    }
}

# Wrangler reads CLOUDFLARE_API_TOKEN. For R2 publication we deliberately
# map the dedicated, bucket-scoped R2 token into that process variable.
$PreviousCloudflareApiToken = $env:CLOUDFLARE_API_TOKEN
$env:CLOUDFLARE_API_TOKEN = $env:CLOUDFLARE_R2_API_TOKEN

try {
    $ConfigFiles = @(
        (Join-Path $Root 'src\config\edgeiqFiles.ts')
        (Join-Path $Root 'src\config\edgeiqLiveFeeds.ts')
    )

    foreach ($Config in $ConfigFiles) {
        if (-not (Test-Path -LiteralPath $Config)) {
            throw "MISSING_CONFIG=$Config"
        }
    }

    $Pattern = '/data/([^"'']+)'
    $Names = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)

    foreach ($Config in $ConfigFiles) {
        $Text = Get-Content -LiteralPath $Config -Raw
        foreach ($Match in [regex]::Matches($Text, $Pattern)) {
            [void]$Names.Add($Match.Groups[1].Value)
        }
    }

    $RequiredCurrentRaceFeeds = @(
        'edgeiq_epi_current_rating_v1.json',
        'edgeiq_epi_current_rating_v1.csv',
        'edgeiq_fair_price_epr_v1.csv',
        'edgeiq_form_guide_enriched_v2.json',
        'edgeiq_form_guide_enriched_v2.csv',
        'edgeiq_market_terminal_feed_v1.csv'
    )

    foreach ($Name in $RequiredCurrentRaceFeeds) {
        [void]$Names.Add($Name)
    }

    $FeedNames = @($Names | Sort-Object)
    Write-Host "RUNTIME_FEEDS_DISCOVERED=$($FeedNames.Count)"

    if ($FeedNames.Count -eq 0) {
        throw 'NO_RUNTIME_FEEDS_DISCOVERED'
    }

    $Missing = @()
    foreach ($Name in $FeedNames) {
        $Path = Join-Path $Root (Join-Path 'public\data' $Name)
        if (-not (Test-Path -LiteralPath $Path)) {
            $Missing += $Name
        }
    }

    Write-Host "RUNTIME_FEEDS_MISSING=$($Missing.Count)"
    foreach ($Name in $Missing) {
        Write-Host "MISSING=$Name"
    }

    if ($Missing.Count -ne 0) {
        throw 'RUNTIME_FEED_SET_INCOMPLETE'
    }

    $Uploaded = 0
    foreach ($Name in $FeedNames) {
        $Path = Join-Path $Root (Join-Path 'public\data' $Name)
        $Object = "$Bucket/data/$Name"

        Write-Host "UPLOAD=$Object"
        & npx.cmd --yes wrangler@latest r2 object put $Object --file $Path --remote

        if ($LASTEXITCODE -ne 0) {
            throw "R2_UPLOAD_FAILED=$Name"
        }

        $Uploaded++
    }

    Write-Host ''
    Write-Host '======================================================================'
    Write-Host 'EDGEiQ R2 RUNTIME FEED PUBLISH = PASS'
    Write-Host '======================================================================'
    Write-Host "BUCKET=$Bucket"
    Write-Host "UPLOADED=$Uploaded"
    Write-Host 'WAREHOUSE_UPLOADS=0'
    Write-Host 'MODEL_MATH_CHANGED=NO'
    Write-Host 'R2_TOKEN_SCOPE=DEDICATED'
    Write-Host '======================================================================'
}
finally {
    if ($null -eq $PreviousCloudflareApiToken) {
        Remove-Item Env:CLOUDFLARE_API_TOKEN -ErrorAction SilentlyContinue
    }
    else {
        $env:CLOUDFLARE_API_TOKEN = $PreviousCloudflareApiToken
    }
}

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$Python = Get-Command python.exe -ErrorAction Stop
$DailyScript = Join-Path $Root 'scripts\run_edgeiq_daily_product_refresh_v1.py'
$Publisher = Join-Path $Root 'scripts\publish_edgeiq_runtime_feeds_to_r2.ps1'
$AuditPath = Join-Path $Root 'docs\operations-readiness\daily-refresh\edgeiq_daily_product_refresh_v1_audit.json'
$SentinelPath = Join-Path $Root 'public\data\edgeiq_runtime_freshness_v1.json'
$Bucket = if ($env:EDGEIQ_R2_BUCKET) { $env:EDGEIQ_R2_BUCKET } else { 'edgeiq-runtime-data' }

foreach ($Path in @($DailyScript, $Publisher)) {
    if (-not (Test-Path -LiteralPath $Path)) {
        throw "MISSING_REQUIRED_FILE=$Path"
    }
}

$MelbourneZone = [System.TimeZoneInfo]::FindSystemTimeZoneById('AUS Eastern Standard Time')
$MelbourneNow = [System.TimeZoneInfo]::ConvertTimeFromUtc([DateTime]::UtcNow, $MelbourneZone)
$ExpectedDate = $MelbourneNow.ToString('yyyy-MM-dd')

Write-Host '======================================================================'
Write-Host 'EDGEiQ GOVERNED DAILY REFRESH + R2 PUBLICATION'
Write-Host '======================================================================'
Write-Host "EXPECTED_MELBOURNE_DATE=$ExpectedDate"
Write-Host "ROOT=$Root"

& $Python.Source $DailyScript
$RefreshExit = $LASTEXITCODE
Write-Host "DAILY_REFRESH_EXIT=$RefreshExit"
if ($RefreshExit -ne 0) {
    throw "DAILY_REFRESH_FAILED=$RefreshExit"
}

if (-not (Test-Path -LiteralPath $AuditPath)) {
    throw "MISSING_DAILY_AUDIT=$AuditPath"
}

$Audit = Get-Content -LiteralPath $AuditPath -Raw | ConvertFrom-Json
$OperatingDate = [string]$Audit.operating_date
$AuditStatus = [string]$Audit.audit_status

Write-Host "AUDIT_OPERATING_DATE=$OperatingDate"
Write-Host "AUDIT_STATUS=$AuditStatus"

if ($OperatingDate -ne $ExpectedDate) {
    throw "OPERATING_DATE_MISMATCH=EXPECTED_$ExpectedDate`_ACTUAL_$OperatingDate"
}

if ($AuditStatus -ne 'PASS') {
    throw "DAILY_AUDIT_NOT_PASS=$AuditStatus"
}

$Sentinel = [ordered]@{
    schema_version = 'edgeiq_runtime_freshness_v1'
    operating_date = $OperatingDate
    timezone = 'Australia/Melbourne'
    published_at_utc = [DateTime]::UtcNow.ToString('yyyy-MM-ddTHH:mm:ssZ')
    audit_status = $AuditStatus
    meetings_built = $Audit.meetings_built
    races_built = $Audit.races_built
    runners_built = $Audit.runners_built
    source = 'run_edgeiq_daily_refresh_and_r2_publish_v1.ps1'
}

$Sentinel | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $SentinelPath -Encoding UTF8

& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $Publisher
$PublishExit = $LASTEXITCODE
Write-Host "R2_RUNTIME_PUBLISH_EXIT=$PublishExit"
if ($PublishExit -ne 0) {
    throw "R2_RUNTIME_PUBLISH_FAILED=$PublishExit"
}

if (-not $env:CLOUDFLARE_R2_API_TOKEN) {
    throw 'MISSING_ENV=CLOUDFLARE_R2_API_TOKEN'
}

$PreviousCloudflareApiToken = $env:CLOUDFLARE_API_TOKEN
$env:CLOUDFLARE_API_TOKEN = $env:CLOUDFLARE_R2_API_TOKEN
try {
    $SentinelObject = "$Bucket/data/edgeiq_runtime_freshness_v1.json"
    & npx.cmd --yes wrangler@latest r2 object put $SentinelObject --file $SentinelPath --remote
    if ($LASTEXITCODE -ne 0) {
        throw 'R2_FRESHNESS_SENTINEL_UPLOAD_FAILED'
    }
}
finally {
    if ($null -eq $PreviousCloudflareApiToken) {
        Remove-Item Env:CLOUDFLARE_API_TOKEN -ErrorAction SilentlyContinue
    }
    else {
        $env:CLOUDFLARE_API_TOKEN = $PreviousCloudflareApiToken
    }
}

Write-Host '======================================================================'
Write-Host 'EDGEiQ DAILY PRODUCTION PUBLICATION = PASS'
Write-Host '======================================================================'
Write-Host "OPERATING_DATE=$OperatingDate"
Write-Host 'DATE_GATE=PASS'
Write-Host 'DAILY_AUDIT=PASS'
Write-Host 'R2_RUNTIME_PUBLISH=PASS'
Write-Host 'FRESHNESS_SENTINEL=PASS'
Write-Host 'MODEL_MATH_CHANGED=NO'
Write-Host '======================================================================'

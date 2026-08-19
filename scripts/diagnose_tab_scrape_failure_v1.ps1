$ErrorActionPreference = "Continue"

Write-Host "`n=== TAB SCRAPE DIAGNOSTIC V1 ==="

$urls = @(
  "https://api.beta.tab.com.au/v1/tab-info-service/racing/dates/2026-06-13/meetings/R/SAN/races/1",
  "https://www.tab.com.au/racing/2026-06-13/Sandown/SAN/R/1"
)

foreach ($url in $urls) {
    Write-Host "`n--- TEST URL ---"
    Write-Host $url

    try {
        $sw = [System.Diagnostics.Stopwatch]::StartNew()
        $r = Invoke-WebRequest `
            -Uri $url `
            -Headers @{
                "User-Agent"="Mozilla/5.0"
                "Accept"="application/json,text/plain,*/*"
                "Origin"="https://www.tab.com.au"
                "Referer"="https://www.tab.com.au/"
            } `
            -TimeoutSec 20 `
            -UseBasicParsing
        $sw.Stop()

        Write-Host "STATUS:" $r.StatusCode
        Write-Host "MS:" $sw.ElapsedMilliseconds
        Write-Host "CONTENT TYPE:" $r.Headers["Content-Type"]
        Write-Host "FIRST 500:"
        $r.Content.Substring(0, [Math]::Min(500, $r.Content.Length))
    }
    catch {
        Write-Host "FAILED:"
        Write-Host $_.Exception.Message
        if ($_.Exception.Response) {
            Write-Host "HTTP STATUS:" $_.Exception.Response.StatusCode.value__
        }
    }
}

Write-Host "`n=== CHECK SCRAPER FILE SHAPE ==="
Select-String -Path ".\scripts\scrape_tab_single_race_v1.py" -Pattern "FRONTEND_RE|expect_response|headless|timeout|goto|api.beta|Bad TAB" -Context 2,3

Write-Host "`n=== CHECK LAST RAW CAPTURES ==="
Get-ChildItem ".\public\data\tab_single_race_raw_v1" -ErrorAction SilentlyContinue |
Sort-Object LastWriteTime -Descending |
Select-Object -First 10 Name,Length,LastWriteTime |
Format-Table -AutoSize

Write-Host "`n=== CHECK CURRENT TAB OUTPUT ==="
if (Test-Path ".\public\data\edgeiq_tab_live_prices_direct_v1.csv") {
    Import-Csv ".\public\data\edgeiq_tab_live_prices_direct_v1.csv" |
    Select-Object -First 20 |
    Format-Table -AutoSize
} else {
    Write-Host "No tab direct file found."
}

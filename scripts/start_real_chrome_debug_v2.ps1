$chrome = @(
  "C:\Program Files\Google\Chrome\Application\chrome.exe",
  "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
) | Where-Object { Test-Path $_ } | Select-Object -First 1

if (-not $chrome) {
  throw "Chrome not found"
}

$userData = "$env:LOCALAPPDATA\Google\Chrome\User Data"

Start-Process $chrome -ArgumentList @(
  "--remote-debugging-port=9222",
  "--profile-directory=Default",
  "https://www.racing.com/form/2026-05-01/ladbrokes-geelong/race/1/speed-data"
)

Write-Host "REAL CHROME DEBUG READY: http://127.0.0.1:9222"

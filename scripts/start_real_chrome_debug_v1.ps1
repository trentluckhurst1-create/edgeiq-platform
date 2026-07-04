$chrome = @(
  "C:\Program Files\Google\Chrome\Application\chrome.exe",
  "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
) | Where-Object { Test-Path $_ } | Select-Object -First 1

if (-not $chrome) {
  throw "Chrome not found"
}

Stop-Process -Name chrome -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

$userData = "$env:LOCALAPPDATA\Google\Chrome\User Data"

Start-Process $chrome -ArgumentList @(
  "--remote-debugging-port=9222",
  "--user-data-dir=$userData",
  "--profile-directory=Default",
  "--disable-blink-features=AutomationControlled",
  "https://www.racing.com/calendar"
)

Write-Host "CHROME DEBUG STARTED ON http://127.0.0.1:9222"

# Define paths
$src = "C:\Users\trent\OneDrive\Documents\horse_racing_model\outputs"
$dest = "C:\Users\trent\OneDrive\Documents\horse_racing_model\dashboard\racing-dashboard\public\data"

# Ensure destination exists
New-Item -ItemType Directory -Force -Path $dest | Out-Null

# Copy required files
Copy-Item "$src\forecasts\race_card_report.csv" $dest -Force
Copy-Item "$src\form\form_card_summary.csv" $dest -Force
Copy-Item "$src\form\form_card_runs.csv" $dest -Force
Copy-Item "$src\markets\market_odds_report.csv" $dest -Force

Write-Host "✅ Data synced to dashboard"
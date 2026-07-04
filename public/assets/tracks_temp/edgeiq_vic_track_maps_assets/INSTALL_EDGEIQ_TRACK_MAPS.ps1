$ErrorActionPreference = "Stop"
$projectRoot = "C:\Users\trent\OneDrive\Documents\horse_racing_model\dashboard\racing-dashboard"
$assetRoot = Join-Path $projectRoot "public\assets\tracks\edgeiq"
New-Item -ItemType Directory -Force -Path $assetRoot | Out-Null
Copy-Item ".\edgeiq_style_exact_dimensions\*.png" $assetRoot -Force
Copy-Item ".\manifest.json" $assetRoot -Force
Write-Host "EDGEiQ track maps installed to $assetRoot"

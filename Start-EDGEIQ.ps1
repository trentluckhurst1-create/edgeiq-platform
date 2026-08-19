Set-Location "C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM"
python -u .\scripts\run_edgeiq_daily_product_refresh_v1.py
if ($LASTEXITCODE -ne 0) { Write-Host "EDGEIQ refresh failed. React startup blocked." -ForegroundColor Red; exit $LASTEXITCODE }
npm run dev

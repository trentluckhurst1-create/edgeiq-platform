param(
    [ValidateSet("preview", "dev")]
    [string]$Mode = "preview",
    [string]$BindHost = "127.0.0.1",
    [int]$Port = 4173,
    [switch]$Foreground
)

$ErrorActionPreference = "Stop"

function Get-ProjectRoot {
    return [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
}

function Assert-ProjectRoot {
    param([string]$ProjectRoot)

    if (-not (Test-Path (Join-Path $ProjectRoot "package.json"))) {
        throw "package.json not found under $ProjectRoot"
    }
}

function Assert-NpmAvailable {
    if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
        throw "npm was not found on PATH."
    }
}

function Invoke-Npm {
    param(
        [string]$ProjectRoot,
        [string[]]$Arguments
    )

    Push-Location $ProjectRoot
    try {
        & npm @Arguments
        if ($LASTEXITCODE -ne 0) {
            throw "npm $($Arguments -join ' ') failed with exit code $LASTEXITCODE"
        }
    }
    finally {
        Pop-Location
    }
}

function Get-Listener {
    param([int]$Port)

    return Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
        Select-Object -First 1
}

function Wait-ForPort {
    param(
        [int]$Port,
        [int]$TimeoutSeconds = 15
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        if (Get-Listener -Port $Port) {
            return $true
        }
        Start-Sleep -Milliseconds 500
    }

    return $false
}

function Write-PreviewSummary {
    param(
        [string]$Mode,
        [string]$BindHost,
        [int]$Port,
        [string]$PreviewUrl,
        [string]$NormalUrl,
        [string]$LogPath,
        [string]$Status
    )

    Write-Output "[EDGEIQ_DEV_PREVIEW] $Status"
    Write-Output "mode=$Mode"
    Write-Output "normal_url=$NormalUrl"
    Write-Output "preview_url=$PreviewUrl"
    Write-Output "log=$LogPath"
    Write-Output "note=Use the preview URL for local visual QA. The normal URL should still follow Clerk sign-in."
}

$projectRoot = Get-ProjectRoot
Assert-ProjectRoot -ProjectRoot $projectRoot
Assert-NpmAvailable

$previewUrl = "http://{0}:{1}/?dev-bypass=1" -f $BindHost, $Port
$normalUrl = "http://{0}:{1}/" -f $BindHost, $Port
$logDir = Join-Path $projectRoot "tmp"
$logPath = Join-Path $logDir ("edgeiq_dev_preview_{0}_{1}.log" -f $Mode, $Port)

New-Item -ItemType Directory -Path $logDir -Force | Out-Null

if ($Mode -eq "preview") {
    $env:VITE_EDGEIQ_DEV_PREVIEW = "true"
    Invoke-Npm -ProjectRoot $projectRoot -Arguments @("run", "build")
}

$existingListener = Get-Listener -Port $Port
if ($existingListener) {
    Write-PreviewSummary `
        -Mode $Mode `
        -BindHost $BindHost `
        -Port $Port `
        -PreviewUrl $previewUrl `
        -NormalUrl $normalUrl `
        -LogPath $logPath `
        -Status "REUSING_EXISTING_SERVER"
    return
}

if ($Foreground) {
    $env:VITE_EDGEIQ_DEV_PREVIEW = "true"
    Write-PreviewSummary `
        -Mode $Mode `
        -BindHost $BindHost `
        -Port $Port `
        -PreviewUrl $previewUrl `
        -NormalUrl $normalUrl `
        -LogPath $logPath `
        -Status "STARTING_FOREGROUND"

    Push-Location $projectRoot
    try {
        if ($Mode -eq "preview") {
            & npm run preview -- --host $BindHost --port $Port
        }
        else {
            & npm run dev -- --host $BindHost --port $Port
        }

        if ($LASTEXITCODE -ne 0) {
            throw "npm run $Mode failed with exit code $LASTEXITCODE"
        }
    }
    finally {
        Pop-Location
    }

    return
}

$launchCommand = if ($Mode -eq "preview") {
    "$env:VITE_EDGEIQ_DEV_PREVIEW='true'; Set-Location '$projectRoot'; npm run preview -- --host $BindHost --port $Port *> '$logPath'"
}
else {
    "$env:VITE_EDGEIQ_DEV_PREVIEW='true'; Set-Location '$projectRoot'; npm run dev -- --host $BindHost --port $Port *> '$logPath'"
}

Start-Process `
    -FilePath "powershell" `
    -ArgumentList "-NoLogo", "-NoProfile", "-Command", $launchCommand `
    -WindowStyle Hidden | Out-Null

$serverReady = Wait-ForPort -Port $Port -TimeoutSeconds 15

if (-not $serverReady) {
    throw "Developer preview server did not start on port $Port. Check $logPath"
}

Write-PreviewSummary `
    -Mode $Mode `
    -BindHost $BindHost `
    -Port $Port `
    -PreviewUrl $previewUrl `
    -NormalUrl $normalUrl `
    -LogPath $logPath `
    -Status "STARTED"

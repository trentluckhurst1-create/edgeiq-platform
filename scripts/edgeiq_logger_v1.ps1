[CmdletBinding()]
param(
    [string]$LoggerProjectRoot = "",
    [string]$LoggerTaskName = "EDGEIQ_AUTOMATION",
    [ValidateSet("INFO", "WARN", "ERROR")]
    [string]$LoggerLevel = "INFO",
    [string]$LoggerMessage = "",
    [string]$LoggerLogsFolderRelativePath = "logs"
)

function Resolve-EdgeIQLoggerProjectRoot {
    param([string]$CandidateRoot)

    if (![string]::IsNullOrWhiteSpace($CandidateRoot)) {
        if (!(Test-Path $CandidateRoot)) {
            throw "Project root does not exist: $CandidateRoot"
        }
        return (Resolve-Path $CandidateRoot).Path
    }

    $defaultRoot = Split-Path -Parent $PSScriptRoot
    if ((Test-Path (Join-Path $defaultRoot "scripts")) -and (Test-Path (Join-Path $defaultRoot "public"))) {
        return (Resolve-Path $defaultRoot).Path
    }

    throw "Unable to resolve EDGEIQ project root from logger script location."
}

function Get-EdgeIQLogDirectory {
    param(
        [string]$ProjectRoot,
        [string]$LogsFolderRelativePath = "logs"
    )

    $resolvedRoot = Resolve-EdgeIQLoggerProjectRoot -CandidateRoot $ProjectRoot
    $logDirectory = Join-Path $resolvedRoot $LogsFolderRelativePath
    if (!(Test-Path $logDirectory)) {
        New-Item -ItemType Directory -Path $logDirectory -Force | Out-Null
    }
    return $logDirectory
}

function New-EdgeIQLogContext {
    param(
        [string]$ProjectRoot,
        [string]$TaskName = "EDGEIQ_AUTOMATION",
        [string]$LogsFolderRelativePath = "logs"
    )

    $resolvedRoot = Resolve-EdgeIQLoggerProjectRoot -CandidateRoot $ProjectRoot
    $logDirectory = Get-EdgeIQLogDirectory -ProjectRoot $resolvedRoot -LogsFolderRelativePath $LogsFolderRelativePath
    $safeTaskName = (($TaskName.ToUpper()) -replace "[^A-Z0-9]+", "_").Trim("_")
    if ([string]::IsNullOrWhiteSpace($safeTaskName)) {
        $safeTaskName = "EDGEIQ_AUTOMATION"
    }
    $dateStamp = (Get-Date).ToString("yyyy-MM-dd")
    $logPath = Join-Path $logDirectory ("{0}_{1}.log" -f $safeTaskName, $dateStamp)

    return [PSCustomObject]@{
        ProjectRoot = $resolvedRoot
        TaskName = $safeTaskName
        LogsFolderRelativePath = $LogsFolderRelativePath
        LogDirectory = $logDirectory
        LogPath = $logPath
    }
}

function Write-EdgeIQLog {
    param(
        [Parameter(Mandatory = $true)]
        [psobject]$Context,
        [ValidateSet("INFO", "WARN", "ERROR")]
        [string]$Level = "INFO",
        [Parameter(Mandatory = $true)]
        [string]$Message
    )

    $timestamp = (Get-Date).ToString("yyyy-MM-ddTHH:mm:ssK")
    $line = "{0} [{1}] [{2}] {3}" -f $timestamp, $Level, $Context.TaskName, $Message

    if (!(Test-Path $Context.LogDirectory)) {
        New-Item -ItemType Directory -Path $Context.LogDirectory -Force | Out-Null
    }

    Add-Content -Path $Context.LogPath -Value $line -Encoding UTF8

    switch ($Level) {
        "ERROR" { Write-Host $line -ForegroundColor Red }
        "WARN" { Write-Host $line -ForegroundColor Yellow }
        default { Write-Host $line }
    }

    return $line
}

function Write-EdgeIQLogSeparator {
    param(
        [Parameter(Mandatory = $true)]
        [psobject]$Context,
        [string]$Character = "=",
        [int]$Count = 100
    )

    $separator = $Character * $Count
    Write-EdgeIQLog -Context $Context -Level "INFO" -Message $separator | Out-Null
}

if ($MyInvocation.InvocationName -ne ".") {
    try {
        if ([string]::IsNullOrWhiteSpace($LoggerMessage)) {
            throw "LoggerMessage is required when invoking edgeiq_logger_v1.ps1 directly."
        }

        $context = New-EdgeIQLogContext -ProjectRoot $LoggerProjectRoot -TaskName $LoggerTaskName -LogsFolderRelativePath $LoggerLogsFolderRelativePath
        Write-EdgeIQLog -Context $context -Level $LoggerLevel -Message $LoggerMessage | Out-Null
        Write-Host "log_path=$($context.LogPath)"
        exit 0
    } catch {
        Write-Error $_
        exit 1
    }
}

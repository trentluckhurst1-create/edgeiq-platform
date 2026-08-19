[CmdletBinding()]
param(
    [string]$PreflightProjectRoot = "",
    [string[]]$PreflightRequiredDirectories = @("scripts", "public", "public\\data"),
    [string[]]$PreflightRequiredCsvPaths = @(),
    [string]$PreflightLogsFolderRelativePath = "logs"
)

function Resolve-EdgeIQPreflightProjectRoot {
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

    throw "Unable to resolve EDGEIQ project root from preflight script location."
}

function Resolve-EdgeIQPreflightPath {
    param(
        [string]$ProjectRoot,
        [string]$RelativeOrAbsolutePath
    )

    if ([string]::IsNullOrWhiteSpace($RelativeOrAbsolutePath)) {
        return ""
    }

    if ([System.IO.Path]::IsPathRooted($RelativeOrAbsolutePath)) {
        return $RelativeOrAbsolutePath
    }

    return Join-Path $ProjectRoot $RelativeOrAbsolutePath
}

function Expand-EdgeIQPreflightList {
    param([string[]]$Items)

    $expanded = New-Object System.Collections.Generic.List[string]

    foreach ($item in $Items) {
        if ([string]::IsNullOrWhiteSpace($item)) {
            continue
        }

        $itemParts = $item.Split(",", [System.StringSplitOptions]::RemoveEmptyEntries)
        foreach ($part in $itemParts) {
            $trimmed = $part.Trim()
            if (![string]::IsNullOrWhiteSpace($trimmed)) {
                $expanded.Add($trimmed)
            }
        }
    }

    return @($expanded)
}

function Invoke-EdgeIQPreflight {
    param(
        [string]$ProjectRoot,
        [string[]]$RequiredDirectories = @("scripts", "public", "public\\data"),
        [string[]]$RequiredCsvPaths = @(),
        [string]$LogsFolderRelativePath = "logs"
    )

    $resolvedRoot = Resolve-EdgeIQPreflightProjectRoot -CandidateRoot $ProjectRoot
    $expandedDirectories = Expand-EdgeIQPreflightList -Items $RequiredDirectories
    $expandedCsvPaths = Expand-EdgeIQPreflightList -Items $RequiredCsvPaths
    $failures = New-Object System.Collections.Generic.List[string]
    $validatedDirectories = New-Object System.Collections.Generic.List[string]
    $validatedCsvs = New-Object System.Collections.Generic.List[string]

    try {
        $pythonCommand = Get-Command python -ErrorAction Stop
        $pythonVersionOutput = (& python --version) 2>&1
        $pythonVersion = (($pythonVersionOutput | Select-Object -First 1) -as [string]).Trim()
        if ([string]::IsNullOrWhiteSpace($pythonVersion)) {
            $pythonVersion = "UNKNOWN"
        }
    } catch {
        $failures.Add("Python is not available on PATH.")
        $pythonCommand = $null
        $pythonVersion = ""
    }

    if (!(Test-Path (Join-Path $resolvedRoot "scripts"))) {
        $failures.Add("Project root does not contain scripts folder: $resolvedRoot")
    }
    if (!(Test-Path (Join-Path $resolvedRoot "public"))) {
        $failures.Add("Project root does not contain public folder: $resolvedRoot")
    }

    foreach ($directory in $expandedDirectories) {
        $resolvedDirectory = Resolve-EdgeIQPreflightPath -ProjectRoot $resolvedRoot -RelativeOrAbsolutePath $directory
        if (!(Test-Path $resolvedDirectory -PathType Container)) {
            $failures.Add("Missing required directory: $resolvedDirectory")
        } else {
            $validatedDirectories.Add($resolvedDirectory)
        }
    }

    $logsDirectory = Resolve-EdgeIQPreflightPath -ProjectRoot $resolvedRoot -RelativeOrAbsolutePath $LogsFolderRelativePath
    if (!(Test-Path $logsDirectory)) {
        New-Item -ItemType Directory -Path $logsDirectory -Force | Out-Null
    }

    foreach ($csvPath in $expandedCsvPaths) {
        $resolvedCsv = Resolve-EdgeIQPreflightPath -ProjectRoot $resolvedRoot -RelativeOrAbsolutePath $csvPath
        if (!(Test-Path $resolvedCsv -PathType Leaf)) {
            $failures.Add("Missing required CSV file: $resolvedCsv")
            continue
        }

        if ([System.IO.Path]::GetExtension($resolvedCsv).ToLowerInvariant() -ne ".csv") {
            $failures.Add("Required file is not a CSV: $resolvedCsv")
            continue
        }

        $fileInfo = Get-Item $resolvedCsv
        if ($fileInfo.Length -le 0) {
            $failures.Add("Required CSV file is empty: $resolvedCsv")
            continue
        }

        $validatedCsvs.Add($resolvedCsv)
    }

    $status = if ($failures.Count -eq 0) { "PASS" } else { "FAIL" }

    $result = [PSCustomObject]@{
        Status = $status
        ProjectRoot = $resolvedRoot
        PythonCommand = if ($pythonCommand) { $pythonCommand.Source } else { "" }
        PythonVersion = $pythonVersion
        LogsDirectory = $logsDirectory
        RequiredDirectoriesChecked = $expandedDirectories.Count
        RequiredDirectoriesPassed = $validatedDirectories.Count
        RequiredCsvsChecked = $expandedCsvPaths.Count
        RequiredCsvsPassed = $validatedCsvs.Count
        Failures = @($failures)
    }

    if ($failures.Count -gt 0) {
        $failureMessage = ($failures -join " | ")
        throw "EDGEIQ preflight failed. $failureMessage"
    }

    return $result
}

if ($MyInvocation.InvocationName -ne ".") {
    try {
        $result = Invoke-EdgeIQPreflight -ProjectRoot $PreflightProjectRoot -RequiredDirectories $PreflightRequiredDirectories -RequiredCsvPaths $PreflightRequiredCsvPaths -LogsFolderRelativePath $PreflightLogsFolderRelativePath
        $result | Format-List
        exit 0
    } catch {
        Write-Error $_
        exit 1
    }
}

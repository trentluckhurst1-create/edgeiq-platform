[CmdletBinding()]
param(
    [ValidateSet("Acquire", "Release", "Test")]
    [string]$LockManagerAction = "",
    [string]$LockManagerProjectRoot = "",
    [string]$LockManagerLockName = "EDGEIQ_AUTOMATION",
    [string]$LockManagerLogsFolderRelativePath = "logs",
    [switch]$LockManagerForce
)

function Resolve-EdgeIQLockProjectRoot {
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

    throw "Unable to resolve EDGEIQ project root from lock manager script location."
}

function Get-EdgeIQLockDirectory {
    param(
        [string]$ProjectRoot,
        [string]$LogsFolderRelativePath = "logs"
    )

    $resolvedRoot = Resolve-EdgeIQLockProjectRoot -CandidateRoot $ProjectRoot
    $locksDirectory = Join-Path (Join-Path $resolvedRoot $LogsFolderRelativePath) "locks"
    if (!(Test-Path $locksDirectory)) {
        New-Item -ItemType Directory -Path $locksDirectory -Force | Out-Null
    }
    return $locksDirectory
}

function Get-EdgeIQLockPath {
    param(
        [string]$ProjectRoot,
        [string]$LockName,
        [string]$LogsFolderRelativePath = "logs"
    )

    $locksDirectory = Get-EdgeIQLockDirectory -ProjectRoot $ProjectRoot -LogsFolderRelativePath $LogsFolderRelativePath
    $safeLockName = (($LockName.ToUpper()) -replace "[^A-Z0-9]+", "_").Trim("_")
    if ([string]::IsNullOrWhiteSpace($safeLockName)) {
        $safeLockName = "EDGEIQ_AUTOMATION"
    }
    return Join-Path $locksDirectory ("{0}.lock.json" -f $safeLockName)
}

function Get-EdgeIQLockMetadata {
    param([string]$LockPath)

    if (!(Test-Path $LockPath)) {
        return $null
    }

    try {
        return Get-Content $LockPath -Raw -Encoding UTF8 | ConvertFrom-Json
    } catch {
        return $null
    }
}

function Test-EdgeIQLockProcess {
    param([int]$ProcessId)

    if ($ProcessId -le 0) {
        return $false
    }

    try {
        Get-Process -Id $ProcessId -ErrorAction Stop | Out-Null
        return $true
    } catch {
        return $false
    }
}

function Clear-EdgeIQStaleLock {
    param([string]$LockPath)

    if (Test-Path $LockPath) {
        Remove-Item $LockPath -Force
    }
}

function Test-EdgeIQLock {
    param(
        [string]$ProjectRoot,
        [string]$LockName,
        [string]$LogsFolderRelativePath = "logs"
    )

    $resolvedRoot = Resolve-EdgeIQLockProjectRoot -CandidateRoot $ProjectRoot
    $lockPath = Get-EdgeIQLockPath -ProjectRoot $resolvedRoot -LockName $LockName -LogsFolderRelativePath $LogsFolderRelativePath
    $metadata = Get-EdgeIQLockMetadata -LockPath $lockPath
    $lockExists = Test-Path $lockPath
    $ownerAlive = $false

    if ($metadata -and $metadata.process_id) {
        $ownerAlive = Test-EdgeIQLockProcess -ProcessId ([int]$metadata.process_id)
    }

    return [PSCustomObject]@{
        LockName = $LockName
        LockPath = $lockPath
        LockExists = $lockExists
        OwnerAlive = $ownerAlive
        Metadata = $metadata
        Status = if (!$lockExists) { "UNLOCKED" } elseif ($ownerAlive) { "LOCKED" } else { "STALE" }
    }
}

function Acquire-EdgeIQLock {
    param(
        [string]$ProjectRoot,
        [string]$LockName,
        [string]$LogsFolderRelativePath = "logs"
    )

    $resolvedRoot = Resolve-EdgeIQLockProjectRoot -CandidateRoot $ProjectRoot
    $lockPath = Get-EdgeIQLockPath -ProjectRoot $resolvedRoot -LockName $LockName -LogsFolderRelativePath $LogsFolderRelativePath
    $status = Test-EdgeIQLock -ProjectRoot $resolvedRoot -LockName $LockName -LogsFolderRelativePath $LogsFolderRelativePath

    if ($status.LockExists -and $status.OwnerAlive) {
        $ownerMessage = ""
        if ($status.Metadata) {
            $ownerMessage = " Existing lock owner PID=$($status.Metadata.process_id) acquired_at=$($status.Metadata.acquired_at) task=$($status.Metadata.lock_name)."
        }
        throw "Lock already held: $lockPath.$ownerMessage"
    }

    if ($status.LockExists -and !$status.OwnerAlive) {
        Clear-EdgeIQStaleLock -LockPath $lockPath
    }

    $metadata = [ordered]@{
        lock_name = $LockName
        acquired_at = (Get-Date).ToString("yyyy-MM-ddTHH:mm:ssK")
        process_id = $PID
        host = $env:COMPUTERNAME
        user = $env:USERNAME
        script = $PSCommandPath
        project_root = $resolvedRoot
        lock_path = $lockPath
    }

    $json = $metadata | ConvertTo-Json -Depth 4
    $fileStream = $null
    $streamWriter = $null

    try {
        $fileStream = [System.IO.File]::Open($lockPath, [System.IO.FileMode]::CreateNew, [System.IO.FileAccess]::Write, [System.IO.FileShare]::None)
        $streamWriter = New-Object System.IO.StreamWriter($fileStream)
        $streamWriter.Write($json)
        $streamWriter.Flush()
    } catch {
        throw "Failed to acquire lock: $lockPath. $($_.Exception.Message)"
    } finally {
        if ($streamWriter) {
            $streamWriter.Dispose()
        }
        if ($fileStream) {
            $fileStream.Dispose()
        }
    }

    return [PSCustomObject]@{
        Acquired = $true
        LockName = $LockName
        LockPath = $lockPath
        Metadata = [PSCustomObject]$metadata
    }
}

function Release-EdgeIQLock {
    param(
        [string]$ProjectRoot,
        [string]$LockName,
        [string]$LogsFolderRelativePath = "logs",
        [switch]$Force
    )

    $resolvedRoot = Resolve-EdgeIQLockProjectRoot -CandidateRoot $ProjectRoot
    $lockPath = Get-EdgeIQLockPath -ProjectRoot $resolvedRoot -LockName $LockName -LogsFolderRelativePath $LogsFolderRelativePath
    $metadata = Get-EdgeIQLockMetadata -LockPath $lockPath

    if (!(Test-Path $lockPath)) {
        return [PSCustomObject]@{
            Released = $false
            LockName = $LockName
            LockPath = $lockPath
            Status = "ALREADY_RELEASED"
        }
    }

    if (!$Force -and $metadata -and $metadata.process_id -and ([int]$metadata.process_id -ne $PID)) {
        throw "Cannot release lock owned by another process without -Force. LockPath=$lockPath OwnerPID=$($metadata.process_id)"
    }

    Remove-Item $lockPath -Force

    return [PSCustomObject]@{
        Released = $true
        LockName = $LockName
        LockPath = $lockPath
        Status = "RELEASED"
    }
}

if ($MyInvocation.InvocationName -ne ".") {
    try {
        if ([string]::IsNullOrWhiteSpace($LockManagerAction)) {
            throw "LockManagerAction is required when invoking edgeiq_lock_manager_v1.ps1 directly."
        }

        switch ($LockManagerAction) {
            "Acquire" {
                $result = Acquire-EdgeIQLock -ProjectRoot $LockManagerProjectRoot -LockName $LockManagerLockName -LogsFolderRelativePath $LockManagerLogsFolderRelativePath
                $result | Format-List
            }
            "Release" {
                $result = Release-EdgeIQLock -ProjectRoot $LockManagerProjectRoot -LockName $LockManagerLockName -LogsFolderRelativePath $LockManagerLogsFolderRelativePath -Force:$LockManagerForce
                $result | Format-List
            }
            "Test" {
                $result = Test-EdgeIQLock -ProjectRoot $LockManagerProjectRoot -LockName $LockManagerLockName -LogsFolderRelativePath $LockManagerLogsFolderRelativePath
                $result | Format-List
            }
        }
        exit 0
    } catch {
        Write-Error $_
        exit 1
    }
}

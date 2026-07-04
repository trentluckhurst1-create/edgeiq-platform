$ErrorActionPreference = "Stop"

$TaskName = "EDGEIQ_ECOLOGY_MEMORY_STACK_V2"
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$PythonExe = "python"
$ScriptPath = Join-Path $ProjectRoot "scripts\run_edgeiq_ecology_master_memory_orchestrator_v2.py"

if (-not (Test-Path -LiteralPath $ScriptPath)) {
    throw "Cannot find orchestrator script: $ScriptPath"
}

$ExistingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($ExistingTask) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

$StartAt = (Get-Date).AddMinutes(5)
$Action = New-ScheduledTaskAction `
    -Execute $PythonExe `
    -Argument "scripts\run_edgeiq_ecology_master_memory_orchestrator_v2.py" `
    -WorkingDirectory $ProjectRoot

$Trigger = New-ScheduledTaskTrigger `
    -Once `
    -At $StartAt `
    -RepetitionInterval (New-TimeSpan -Hours 1) `
    -RepetitionDuration (New-TimeSpan -Days 3650)

$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -MultipleInstances IgnoreNew

$Principal = New-ScheduledTaskPrincipal `
    -UserId $env:USERNAME `
    -LogonType Interactive `
    -RunLevel Limited

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -Principal $Principal `
    -Description "Runs the EDGEiQ offline ecology memory stack hourly. Research boundary remains OFFLINE_RESEARCH_ONLY."

$CreatedTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction Stop
if (-not $CreatedTask) {
    throw "Scheduled task was not created: $TaskName"
}

$CreatedInfo = Get-ScheduledTaskInfo -TaskName $TaskName -ErrorAction Stop

Write-Host "Created scheduled task: $TaskName"
Write-Host "Project root: $ProjectRoot"
Write-Host "Command: python scripts\run_edgeiq_ecology_master_memory_orchestrator_v2.py"
Write-Host "Schedule: hourly for 3650 days"
Write-Host "State: $($CreatedTask.State)"
Write-Host "Next run: $($CreatedInfo.NextRunTime)"

$CreatedTask | Format-List TaskName,TaskPath,State
$CreatedInfo | Format-List LastRunTime,NextRunTime,LastTaskResult,NumberOfMissedRuns

[CmdletBinding()]
param(
    [string]$ProjectRoot = ""
)

function Resolve-EdgeIQTaskTemplateProjectRoot {
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

    throw "Unable to resolve EDGEIQ project root from scheduled task template script location."
}

function New-EdgeIQScheduledTaskTemplate {
    param(
        [string]$TaskName,
        [string]$ScheduleLabel,
        [string]$WrapperRelativePath,
        [string]$Purpose,
        [string]$ProjectRoot
    )

    $resolvedRoot = Resolve-EdgeIQTaskTemplateProjectRoot -CandidateRoot $ProjectRoot
    $normalizedWrapperRelativePath = $WrapperRelativePath -replace "\\\\", "\"
    $wrapperPath = Join-Path $resolvedRoot $normalizedWrapperRelativePath
    $wrapperExists = Test-Path $wrapperPath -PathType Leaf
    $arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$wrapperPath`""
    $registerPreview = "Register-ScheduledTask -TaskName '{0}' -Action (New-ScheduledTaskAction -Execute 'powershell.exe' -Argument '{1}' -WorkingDirectory '{2}') -Trigger <DEFINE_TRIGGER_HERE> -Description '{3}'" -f $TaskName, $arguments, $resolvedRoot, $Purpose

    return [PSCustomObject]@{
        TaskName = $TaskName
        Schedule = $ScheduleLabel
        WrapperPath = $wrapperPath
        WrapperExists = if ($wrapperExists) { "YES" } else { "NO" }
        TemplateReadiness = if ($wrapperExists) { "READY_TEMPLATE" } else { "MISSING_WRAPPER" }
        WorkingDirectory = $resolvedRoot
        Execute = "powershell.exe"
        Arguments = $arguments
        Purpose = $Purpose
        RegistrationStatus = "TEMPLATE_ONLY"
        RegisterCommandTemplate = $registerPreview
    }
}

function Get-EdgeIQScheduledTaskTemplates {
    param([string]$ProjectRoot)

    $resolvedRoot = Resolve-EdgeIQTaskTemplateProjectRoot -CandidateRoot $ProjectRoot

    return @(
        (New-EdgeIQScheduledTaskTemplate -TaskName "EDGEIQ_BUILD_TOMORROW_V1" -ScheduleLabel "Daily 23:00" -WrapperRelativePath "scripts\run_edgeiq_build_tomorrow_universe_v1.ps1" -Purpose "Build tomorrow and day+2 calendar/universe surfaces before midnight rollover." -ProjectRoot $resolvedRoot),
        (New-EdgeIQScheduledTaskTemplate -TaskName "EDGEIQ_MIDNIGHT_PROMOTION_V1" -ScheduleLabel "Daily 23:55" -WrapperRelativePath "scripts\run_edgeiq_midnight_promotion_chain_v1.ps1" -Purpose "Promote the next day into TODAY, rebuild calendar/universe, and refresh live dashboard feeds only when current fields are ready." -ProjectRoot $resolvedRoot),
        (New-EdgeIQScheduledTaskTemplate -TaskName "EDGEIQ_MORNING_FULL_REFRESH_V1" -ScheduleLabel "Daily 05:00" -WrapperRelativePath "scripts\run_edgeiq_live_refresh_scheduled_v1.ps1" -Purpose "Scheduler-safe morning full refresh for the promoted TODAY meeting." -ProjectRoot $resolvedRoot),
        (New-EdgeIQScheduledTaskTemplate -TaskName "EDGEIQ_LIVE_MARKET_REFRESH_V1" -ScheduleLabel "Every 5 minutes" -WrapperRelativePath "scripts\run_edgeiq_live_refresh_scheduled_v1.ps1" -Purpose "Scheduler-safe live market and dashboard refresh wrapper." -ProjectRoot $resolvedRoot),
        (New-EdgeIQScheduledTaskTemplate -TaskName "EDGEIQ_RESULTS_SCAN_V1" -ScheduleLabel "Every 30 minutes" -WrapperRelativePath "scripts\run_edgeiq_results_scan_v1.ps1" -Purpose "Results truth, summary, and accountability refresh." -ProjectRoot $resolvedRoot),
        (New-EdgeIQScheduledTaskTemplate -TaskName "EDGEIQ_SECTIONALS_SCAN_V1" -ScheduleLabel "Every 3 hours" -WrapperRelativePath "scripts\run_edgeiq_sectionals_scan_v1.ps1" -Purpose "Sectionals processing scan wrapper." -ProjectRoot $resolvedRoot)
    )
}

if ($MyInvocation.InvocationName -ne ".") {
    try {
        $templates = Get-EdgeIQScheduledTaskTemplates -ProjectRoot $ProjectRoot
        Write-Host "[EDGEIQ_SCHEDULED_TASK_TEMPLATES_V1] TEMPLATE ONLY"
        $templates | Select-Object TaskName, Schedule, WrapperPath, WrapperExists, TemplateReadiness, Purpose, RegistrationStatus | Format-Table -Wrap -AutoSize
        Write-Host ""
        Write-Host "Preview register commands:"
        foreach ($template in $templates) {
            Write-Host ""
            Write-Host $template.RegisterCommandTemplate
        }
        exit 0
    } catch {
        Write-Error $_
        exit 1
    }
}

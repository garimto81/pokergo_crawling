# NAMS Scheduler Registration Script
# PRD-0010: Register 3 tasks to Windows Task Scheduler
#
# Usage:
#   .\scripts\register_scheduler.ps1              # Register all
#   .\scripts\register_scheduler.ps1 -TaskId 1   # Register task 1 only
#   .\scripts\register_scheduler.ps1 -Unregister # Unregister all
#
# Note: Requires Administrator privileges

param(
    [int]$TaskId = 0,
    [switch]$Unregister,
    [switch]$Force
)

$ErrorActionPreference = "Stop"

# Project root
$ProjectRoot = "D:\AI\claude01\pokergo_crawling"
$SchedulerDir = "$ProjectRoot\scripts\scheduler"

# Python path
$PythonPath = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $PythonPath) {
    $PythonPath = "C:\Python311\python.exe"
}

Write-Host ""
Write-Host "======================================"
Write-Host "NAMS Scheduler Registration"
Write-Host "======================================"
Write-Host ""
Write-Host "Project: $ProjectRoot"
Write-Host "Python: $PythonPath"
Write-Host ""

# Task definitions
$Tasks = @(
    @{
        Id = 1
        Name = "NAMS_Task1_NAS_Scan"
        Description = "NAMS NAS Scan - Daily 08:00"
        Time = "08:00"
        Script = "task_nas_scan.py"
    },
    @{
        Id = 2
        Name = "NAMS_Task2_Iconik_Export"
        Description = "NAMS Iconik Export - Daily 08:30"
        Time = "08:30"
        Script = "task_iconik_to_sheet.py"
    },
    @{
        Id = 3
        Name = "NAMS_Task3_Iconik_Import"
        Description = "NAMS Iconik Import - Daily 09:00"
        Time = "09:00"
        Script = "task_sheet_to_iconik.py"
    }
)

# Filter specific task
if ($TaskId -gt 0) {
    $Tasks = $Tasks | Where-Object { $_.Id -eq $TaskId }
    if ($Tasks.Count -eq 0) {
        Write-Error "Task ID $TaskId not found."
        exit 1
    }
}

# Unregister mode
if ($Unregister) {
    Write-Host "Unregister mode"
    Write-Host ""
    foreach ($task in $Tasks) {
        $existingTask = Get-ScheduledTask -TaskName $task.Name -ErrorAction SilentlyContinue
        if ($existingTask) {
            Unregister-ScheduledTask -TaskName $task.Name -Confirm:$false
            Write-Host "[X] $($task.Name) - Removed"
        } else {
            Write-Host "[-] $($task.Name) - Not found (skip)"
        }
    }
    Write-Host ""
    Write-Host "Done!"
    exit 0
}

# Register mode
Write-Host "Register mode"
Write-Host ""

foreach ($task in $Tasks) {
    Write-Host "[$($task.Id)] $($task.Name)"
    Write-Host "    Time: $($task.Time)"
    Write-Host "    Script: $($task.Script)"

    # Check existing task
    $existingTask = Get-ScheduledTask -TaskName $task.Name -ErrorAction SilentlyContinue
    if ($existingTask) {
        if ($Force) {
            Write-Host "    [!] Removing existing task..."
            Unregister-ScheduledTask -TaskName $task.Name -Confirm:$false
        } else {
            Write-Host "    [SKIP] Already exists (use -Force to overwrite)"
            continue
        }
    }

    # Create task
    $scriptPath = "$SchedulerDir\$($task.Script)"

    $action = New-ScheduledTaskAction `
        -Execute $PythonPath `
        -Argument $scriptPath `
        -WorkingDirectory $ProjectRoot

    $trigger = New-ScheduledTaskTrigger -Daily -At $task.Time

    $settings = New-ScheduledTaskSettingsSet `
        -StartWhenAvailable `
        -DontStopOnIdleEnd `
        -AllowStartIfOnBatteries `
        -DontStopIfGoingOnBatteries `
        -ExecutionTimeLimit (New-TimeSpan -Hours 2)

    try {
        Register-ScheduledTask `
            -TaskName $task.Name `
            -Action $action `
            -Trigger $trigger `
            -Settings $settings `
            -Description $task.Description `
            -Force | Out-Null

        Write-Host "    [OK] Registered"
    } catch {
        Write-Host "    [ERROR] Registration failed: $_"
    }

    Write-Host ""
}

# Show results
Write-Host "======================================"
Write-Host "Registered NAMS Tasks"
Write-Host "======================================"
Write-Host ""

Get-ScheduledTask | Where-Object { $_.TaskName -like "NAMS_*" } | ForEach-Object {
    $info = $_ | Get-ScheduledTaskInfo
    Write-Host "$($_.TaskName)"
    Write-Host "  State: $($_.State)"
    Write-Host "  Last Run: $($info.LastRunTime)"
    Write-Host "  Next Run: $($info.NextRunTime)"
    Write-Host ""
}

Write-Host "Done!"

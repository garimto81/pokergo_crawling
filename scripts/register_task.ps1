$action = New-ScheduledTaskAction `
    -Execute "python" `
    -Argument "D:\AI\claude01\pokergo_crawling\scripts\daily_scan.py --mode daily --sync-sheets" `
    -WorkingDirectory "D:\AI\claude01\pokergo_crawling"

$trigger = New-ScheduledTaskTrigger -Daily -At 8:00AM

$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -DontStopOnIdleEnd `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries

Register-ScheduledTask `
    -TaskName "NAMS_Daily_Scan" `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Description "NAMS NAS Daily Scan - 매일 08:00 실행"

Write-Host "NAMS_Daily_Scan 작업이 등록되었습니다."

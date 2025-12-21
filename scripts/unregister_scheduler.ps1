# NAMS 스케줄러 삭제 스크립트
# PRD-0010: Windows Task Scheduler에서 NAMS 작업 삭제
#
# 사용법:
#   .\scripts\unregister_scheduler.ps1             # 전체 삭제
#   .\scripts\unregister_scheduler.ps1 -TaskId 1  # 작업 1만 삭제
#
# 주의: 관리자 권한 필요

param(
    [int]$TaskId = 0        # 특정 작업만 삭제 (0 = 전체)
)

$ErrorActionPreference = "Stop"

Write-Host "`n======================================"
Write-Host "NAMS 스케줄러 삭제 스크립트"
Write-Host "======================================`n"

# 작업 정의
$Tasks = @(
    @{ Id = 1; Name = "NAMS_Task1_NAS_Scan" },
    @{ Id = 2; Name = "NAMS_Task2_Iconik_Export" },
    @{ Id = 3; Name = "NAMS_Task3_Iconik_Import" }
)

# 특정 작업만 필터링
if ($TaskId -gt 0) {
    $Tasks = $Tasks | Where-Object { $_.Id -eq $TaskId }
    if ($Tasks.Count -eq 0) {
        Write-Error "작업 ID $TaskId 를 찾을 수 없습니다."
        exit 1
    }
}

Write-Host "삭제할 작업:"
foreach ($task in $Tasks) {
    Write-Host "  - $($task.Name)"
}
Write-Host ""

$confirm = Read-Host "계속하시겠습니까? (y/N)"
if ($confirm -ne "y" -and $confirm -ne "Y") {
    Write-Host "취소됨"
    exit 0
}

Write-Host ""

foreach ($task in $Tasks) {
    $existingTask = Get-ScheduledTask -TaskName $task.Name -ErrorAction SilentlyContinue

    if ($existingTask) {
        try {
            # 실행 중이면 중지
            if ($existingTask.State -eq "Running") {
                Stop-ScheduledTask -TaskName $task.Name
                Write-Host "[$($task.Id)] $($task.Name) - 실행 중지됨"
            }

            # 삭제
            Unregister-ScheduledTask -TaskName $task.Name -Confirm:$false
            Write-Host "[$($task.Id)] $($task.Name) - 삭제됨"
        } catch {
            Write-Host "[$($task.Id)] $($task.Name) - 삭제 실패: $_"
        }
    } else {
        Write-Host "[$($task.Id)] $($task.Name) - 없음 (스킵)"
    }
}

Write-Host ""

# 남은 작업 확인
$remaining = Get-ScheduledTask | Where-Object { $_.TaskName -like "NAMS_*" }
if ($remaining) {
    Write-Host "남은 NAMS 작업:"
    foreach ($t in $remaining) {
        Write-Host "  - $($t.TaskName) ($($t.State))"
    }
} else {
    Write-Host "모든 NAMS 작업이 삭제되었습니다."
}

Write-Host "`n완료!"

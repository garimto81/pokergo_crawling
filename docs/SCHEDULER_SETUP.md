# Windows Task Scheduler 설정 가이드

NAMS 일일 스캔 자동화를 위한 Windows Task Scheduler 설정 가이드.

**Version**: 1.0 | **Date**: 2025-12-19

---

## 개요

| 작업 | 스크립트 | 실행 시간 | 설명 |
|------|----------|-----------|------|
| 일일 스캔 | `daily_scan.py` | 03:00 AM | NAS 드라이브 스캔, 변경 감지 |
| Sheets 동기화 | `sync_sheets.py` | 04:00 AM | Google Sheets 업데이트 |

---

## 1. 일일 스캔 작업 등록

### PowerShell 명령 (관리자 권한)

```powershell
# Task Scheduler에 일일 스캔 작업 등록
$action = New-ScheduledTaskAction `
    -Execute "python" `
    -Argument "D:\AI\claude01\pokergo_crawling\scripts\daily_scan.py --mode daily --sync-sheets" `
    -WorkingDirectory "D:\AI\claude01\pokergo_crawling"

$trigger = New-ScheduledTaskTrigger -Daily -At 3:00AM

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
    -Description "NAMS NAS Daily Scan - 매일 03:00 실행"
```

### GUI 방식

1. **시작 메뉴** → `작업 스케줄러` 검색 → 실행
2. **작업 만들기** 클릭

#### 일반 탭
- 이름: `NAMS_Daily_Scan`
- 설명: `NAMS NAS Daily Scan`
- "가장 높은 권한으로 실행" 체크

#### 트리거 탭
- 새로 만들기 → 매일, 오전 3:00

#### 동작 탭
- 새로 만들기
- 프로그램/스크립트: `python`
- 인수 추가: `D:\AI\claude01\pokergo_crawling\scripts\daily_scan.py --mode daily --sync-sheets`
- 시작 위치: `D:\AI\claude01\pokergo_crawling`

#### 조건 탭
- "컴퓨터의 AC 전원을 사용하는 경우에만..." 체크 해제

#### 설정 탭
- "예약된 시작 시간을 놓친 경우 가능한 빨리..." 체크

---

## 2. 수동 실행

### 일일 스캔

```powershell
# 기본 실행 (incremental)
python D:\AI\claude01\pokergo_crawling\scripts\daily_scan.py --mode daily

# 전체 재스캔
python D:\AI\claude01\pokergo_crawling\scripts\daily_scan.py --mode full

# 특정 드라이브만
python D:\AI\claude01\pokergo_crawling\scripts\daily_scan.py --mode daily --drives Y:,Z:

# Sheets 동기화 포함
python D:\AI\claude01\pokergo_crawling\scripts\daily_scan.py --mode daily --sync-sheets
```

### Sheets 동기화

```powershell
# 상태 확인
python D:\AI\claude01\pokergo_crawling\scripts\sync_sheets.py --status

# 증분 동기화
python D:\AI\claude01\pokergo_crawling\scripts\sync_sheets.py

# 전체 재동기화
python D:\AI\claude01\pokergo_crawling\scripts\sync_sheets.py --full

# 특정 시트
python D:\AI\claude01\pokergo_crawling\scripts\sync_sheets.py --sheet "Master_Catalog"
```

---

## 3. 로그 확인

### 스캔 이력 (DB)

```python
from src.nams.api.database import get_db_context, ScanHistory

with get_db_context() as db:
    scans = db.query(ScanHistory).order_by(
        ScanHistory.started_at.desc()
    ).limit(10).all()

    for scan in scans:
        print(f"{scan.started_at} | {scan.status} | new={scan.new_files}")
```

### Task Scheduler 로그

```powershell
# 마지막 실행 결과 확인
Get-ScheduledTask -TaskName "NAMS_Daily_Scan" | Get-ScheduledTaskInfo
```

---

## 4. 트러블슈팅

### 작업이 실행되지 않음

```powershell
# 작업 상태 확인
Get-ScheduledTask -TaskName "NAMS_Daily_Scan" | Select-Object State, LastRunTime, LastTaskResult

# 수동 실행 테스트
Start-ScheduledTask -TaskName "NAMS_Daily_Scan"
```

### Python 경로 문제

```powershell
# Python 전체 경로 사용
$action = New-ScheduledTaskAction `
    -Execute "C:\Python311\python.exe" `
    -Argument "D:\AI\claude01\pokergo_crawling\scripts\daily_scan.py --mode daily"
```

### NAS 드라이브 접근 오류

- 작업 속성 → "사용자가 로그온할 때만 실행" → "사용자 로그온 여부에 관계없이 실행"으로 변경
- 네트워크 드라이브 대신 UNC 경로 사용: `\\NAS\share` 형식

### 권한 문제

```powershell
# 관리자 권한으로 실행 설정
$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
Set-ScheduledTask -TaskName "NAMS_Daily_Scan" -Principal $principal
```

---

## 5. 작업 관리

### 작업 비활성화

```powershell
Disable-ScheduledTask -TaskName "NAMS_Daily_Scan"
```

### 작업 삭제

```powershell
Unregister-ScheduledTask -TaskName "NAMS_Daily_Scan" -Confirm:$false
```

### 작업 목록

```powershell
Get-ScheduledTask | Where-Object { $_.TaskName -like "NAMS*" }
```

---

## 6. 환경 변수 설정 (선택)

```powershell
# 시스템 환경 변수에 프로젝트 경로 추가
[Environment]::SetEnvironmentVariable(
    "NAMS_PROJECT_ROOT",
    "D:\AI\claude01\pokergo_crawling",
    "Machine"
)
```

---

## 참고

- [daily_scan.py](../scripts/daily_scan.py) - 일일 스캔 스크립트
- [sync_sheets.py](../scripts/sync_sheets.py) - Sheets 동기화 스크립트
- [AUTOMATION_PIPELINE.md](AUTOMATION_PIPELINE.md) - 파이프라인 가이드

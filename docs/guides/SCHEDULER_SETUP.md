# Windows Task Scheduler 설정 가이드

NAMS 일일 스케줄러 통합 자동화 시스템 설정 가이드.

**Version**: 2.0 | **Date**: 2025-12-21 | **PRD**: PRD-0010

---

## 개요

매일 오전 8시부터 시작하는 3개의 자동화 작업을 관리합니다.

| # | 작업명 | 시간 | 설명 |
|---|--------|------|------|
| 1 | `NAMS_Task1_NAS_Scan` | 08:00 | Y:/Z:/X: 드라이브 스캔 → NAMS 시트 |
| 2 | `NAMS_Task2_Iconik_Export` | 08:30 | Iconik API → Iconik_Full_Metadata 시트 |
| 3 | `NAMS_Task3_Iconik_Import` | 09:00 | Iconik_Full_Metadata 시트 → Iconik API |

---

## 1. 빠른 시작

### 자동 등록 (권장)

```powershell
# 관리자 권한으로 PowerShell 실행

# 전체 작업 등록
.\scripts\register_scheduler.ps1

# 특정 작업만 등록
.\scripts\register_scheduler.ps1 -TaskId 1

# 기존 작업 덮어쓰기
.\scripts\register_scheduler.ps1 -Force
```

### 자동 삭제

```powershell
# 전체 삭제
.\scripts\unregister_scheduler.ps1

# 특정 작업만 삭제
.\scripts\unregister_scheduler.ps1 -TaskId 1
```

---

## 2. 수동 실행

### 개별 작업 실행

```powershell
# 작업 1: NAS 스캔
python D:\AI\claude01\pokergo_crawling\scripts\scheduler\task_nas_scan.py

# 작업 2: Iconik → Sheets
python D:\AI\claude01\pokergo_crawling\scripts\scheduler\task_iconik_to_sheet.py

# 작업 3: Sheets → Iconik
python D:\AI\claude01\pokergo_crawling\scripts\scheduler\task_sheet_to_iconik.py
```

### 통합 실행

```powershell
# 전체 실행
python D:\AI\claude01\pokergo_crawling\scripts\scheduler\run_all_tasks.py

# 특정 작업만 실행
python D:\AI\claude01\pokergo_crawling\scripts\scheduler\run_all_tasks.py --task 1,2

# Dry run (계획만 확인)
python D:\AI\claude01\pokergo_crawling\scripts\scheduler\run_all_tasks.py --dry-run
```

### 기존 스크립트 직접 실행

```powershell
# NAS 스캔 (daily_scan.py 직접)
python D:\AI\claude01\pokergo_crawling\scripts\daily_scan.py --mode daily --sync-sheets

# Iconik → Sheets (run_full_metadata.py 직접)
cd D:\AI\claude01\pokergo_crawling\src\migrations\iconik2sheet
python -m scripts.run_full_metadata

# Sheets → Iconik (reverse_sync.py 직접)
cd D:\AI\claude01\pokergo_crawling\src\migrations\iconik2sheet
python -m scripts.reverse_sync --metadata-only
```

---

## 3. 알림 설정

### Slack Webhook 설정

1. Slack App 생성: https://api.slack.com/apps
2. Incoming Webhooks 활성화
3. 환경 변수 설정:

```powershell
# .env 파일에 추가
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/T.../B.../...
```

### 알림 메시지 예시

```
NAMS_Task1_NAS_Scan - SUCCESS
   Duration: 12분 34초
   New Files: 15
   Updated: 8
   Missing: 0

NAMS_Task2_Iconik_Export - FAILED
   Duration: 5분 12초
   Error: Connection timeout
```

---

## 4. 로그 확인

### 로그 파일 위치

```
logs/scheduler/
├── 2025-12-21_task1.log     # 작업 1 로그
├── 2025-12-21_task2.log     # 작업 2 로그
├── 2025-12-21_task3.log     # 작업 3 로그
└── 2025-12-21_all_tasks.log # 통합 실행 로그
```

### Task Scheduler 로그

```powershell
# 작업 상태 확인
Get-ScheduledTask | Where-Object { $_.TaskName -like "NAMS_*" }

# 마지막 실행 정보
Get-ScheduledTask -TaskName "NAMS_Task1_NAS_Scan" | Get-ScheduledTaskInfo

# 수동 실행 테스트
Start-ScheduledTask -TaskName "NAMS_Task1_NAS_Scan"
```

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

---

## 5. 파일 구조

```
scripts/
├── scheduler/
│   ├── __init__.py             # 모듈 정의
│   ├── notifier.py             # Slack/Teams 알림
│   ├── run_all_tasks.py        # 통합 실행 스크립트
│   ├── task_nas_scan.py        # 작업 1 래퍼
│   ├── task_iconik_to_sheet.py # 작업 2 래퍼
│   └── task_sheet_to_iconik.py # 작업 3 래퍼
├── register_scheduler.ps1       # Task Scheduler 등록
├── unregister_scheduler.ps1     # Task Scheduler 삭제
└── daily_scan.py               # 기존 NAS 스캔 스크립트

logs/
└── scheduler/
    └── YYYY-MM-DD_task{N}.log  # 일별 로그
```

---

## 6. 트러블슈팅

### 작업이 실행되지 않음

```powershell
# 작업 상태 확인
Get-ScheduledTask -TaskName "NAMS_Task1_NAS_Scan" | Select-Object State, LastRunTime, LastTaskResult

# 수동 실행 테스트
Start-ScheduledTask -TaskName "NAMS_Task1_NAS_Scan"
```

### Python 경로 문제

```powershell
# register_scheduler.ps1의 $PythonPath 확인
$PythonPath = (Get-Command python).Source
Write-Host $PythonPath

# 또는 전체 경로 직접 지정
$PythonPath = "C:\Python311\python.exe"
```

### NAS 드라이브 접근 오류

- "사용자가 로그온할 때만 실행" → "사용자 로그온 여부에 관계없이 실행"으로 변경
- 네트워크 드라이브 대신 UNC 경로 사용: `\\NAS\share`

### 락 파일 문제

```powershell
# 락 파일 수동 삭제
Remove-Item D:\AI\claude01\pokergo_crawling\logs\scheduler\*.lock -Force
```

### 권한 문제

```powershell
# 관리자 권한으로 실행 설정
$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
Set-ScheduledTask -TaskName "NAMS_Task1_NAS_Scan" -Principal $principal
```

---

## 7. 작업 관리

### 작업 비활성화

```powershell
Disable-ScheduledTask -TaskName "NAMS_Task1_NAS_Scan"
```

### 작업 활성화

```powershell
Enable-ScheduledTask -TaskName "NAMS_Task1_NAS_Scan"
```

### 작업 목록

```powershell
Get-ScheduledTask | Where-Object { $_.TaskName -like "NAMS*" } | Format-Table TaskName, State
```

---

## 참고

- [PRD-0010: 일일 스케줄러 통합](prds/PRD-0010-DAILY-SCHEDULER.md)
- [daily_scan.py](../scripts/daily_scan.py) - 일일 스캔 스크립트
- [iconik2sheet/CLAUDE.md](../src/migrations/iconik2sheet/CLAUDE.md) - Iconik 연동 가이드

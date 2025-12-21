# PRD: 일일 스케줄러 통합 자동화 시스템

**Version**: 1.0
**Date**: 2025-12-21
**Status**: Draft
**PRD Number**: PRD-0010

---

## 1. 개요

매일 오전 8시에 시작하는 통합 스케줄러 시스템을 구축하여 3개의 독립적인 데이터 동기화 작업을 자동으로 수행합니다.

### 1.1 작업 요약

| # | 작업 | 시간 | 소스 | 대상 시트 |
|---|------|------|------|----------|
| 1 | NAS 스캔 → 시트 | 08:00 | Y:/Z:/X: 드라이브 | `1h27Ha7pR...` (NAMS) |
| 2 | Iconik → 시트 | 08:30 | Iconik API | `1pUMPKe...` (Iconik Export) |
| 3 | 시트 → Iconik | 09:00 | `1pUMPKe...` 시트 | Iconik API |

---

## 2. 대상 Google Spreadsheets

### 2.1 시트 정보

| 시트 | Spreadsheet ID | 용도 |
|------|----------------|------|
| **NAMS** | `1h27Ha7pR-iYK_Gik8F4FfSvsk4s89sxk49CsU3XP_m4` | NAS 파일 목록, 매칭 결과 |
| **Iconik Export** | `1pUMPKe-OsKc-Xd8lH1cP9ctJO4hj3keXY5RwNFp2Mtk` | Iconik 메타데이터 (35컬럼) |

---

## 3. 상세 작업 정의

### 3.1 작업 1: NAS 스캔 → 시트 (08:00)

**스크립트**: `scripts/daily_scan.py`

```powershell
python D:\AI\claude01\pokergo_crawling\scripts\daily_scan.py --mode daily --sync-sheets
```

**기능**:
- Y:/Z:/X: 드라이브 스캔
- 신규/변경/누락 파일 감지
- NAMS 시트에 결과 업데이트
- 예상 소요: 10-20분

### 3.2 작업 2: Iconik → 시트 (08:30)

**스크립트**: `src/migrations/iconik2sheet/scripts/run_full_metadata.py`

```powershell
cd D:\AI\claude01\pokergo_crawling\src\migrations\iconik2sheet
python -m scripts.run_full_metadata
```

**기능**:
- Iconik API에서 전체 Asset 조회
- 35컬럼 메타데이터 추출
- `Iconik_Full_Metadata` 시트에 저장
- 예상 소요: 15-30분 (2,840+ Assets)

### 3.3 작업 3: 시트 → Iconik (09:00)

**스크립트**: `src/migrations/iconik2sheet/scripts/reverse_sync.py`

```powershell
cd D:\AI\claude01\pokergo_crawling\src\migrations\iconik2sheet
python -m scripts.reverse_sync --metadata-only
```

**기능**:
- `Iconik_Full_Metadata` 시트에서 수정된 메타데이터 읽기
- Iconik API로 업데이트
- 예상 소요: 10-20분

---

## 4. 구현 계획

### 4.1 신규 생성 파일

```
scripts/
├── scheduler/
│   ├── __init__.py
│   ├── run_all_tasks.py          # 통합 실행 스크립트
│   ├── task_nas_scan.py          # 작업 1 래퍼
│   ├── task_iconik_to_sheet.py   # 작업 2 래퍼
│   ├── task_sheet_to_iconik.py   # 작업 3 래퍼
│   └── notifier.py               # Slack/Teams 알림
├── register_scheduler.ps1         # Task Scheduler 등록
└── unregister_scheduler.ps1       # Task Scheduler 삭제

logs/
└── scheduler/
    ├── 2025-12-21_task1.log
    ├── 2025-12-21_task2.log
    └── 2025-12-21_task3.log
```

### 4.2 수정 파일

| 파일 | 변경 내용 |
|------|----------|
| `docs/SCHEDULER_SETUP.md` | 통합 스케줄러 문서 추가 |
| `.env` (루트) | Slack Webhook URL 추가 |

---

## 5. Windows Task Scheduler 설정

### 5.1 작업 등록 (3개)

| 작업명 | 실행 시간 | 스크립트 |
|--------|----------|----------|
| `NAMS_Task1_NAS_Scan` | 08:00 | `task_nas_scan.py` |
| `NAMS_Task2_Iconik_Export` | 08:30 | `task_iconik_to_sheet.py` |
| `NAMS_Task3_Iconik_Import` | 09:00 | `task_sheet_to_iconik.py` |

### 5.2 등록 PowerShell 스크립트

```powershell
# scripts/register_scheduler.ps1
$tasks = @(
    @{Name="NAMS_Task1_NAS_Scan"; Time="08:00"; Script="task_nas_scan.py"},
    @{Name="NAMS_Task2_Iconik_Export"; Time="08:30"; Script="task_iconik_to_sheet.py"},
    @{Name="NAMS_Task3_Iconik_Import"; Time="09:00"; Script="task_sheet_to_iconik.py"}
)

foreach ($task in $tasks) {
    $action = New-ScheduledTaskAction `
        -Execute "python" `
        -Argument "D:\AI\claude01\pokergo_crawling\scripts\scheduler\$($task.Script)" `
        -WorkingDirectory "D:\AI\claude01\pokergo_crawling"

    $trigger = New-ScheduledTaskTrigger -Daily -At $task.Time

    Register-ScheduledTask -TaskName $task.Name -Action $action -Trigger $trigger
}
```

---

## 6. 알림 시스템

### 6.1 Slack/Teams Webhook

```python
# scripts/scheduler/notifier.py
import httpx

WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")

def send_notification(task_name: str, status: str, details: dict):
    """작업 완료/실패 알림 전송"""
    message = {
        "text": f"*{task_name}* - {status}",
        "attachments": [{
            "color": "good" if status == "SUCCESS" else "danger",
            "fields": [
                {"title": k, "value": str(v), "short": True}
                for k, v in details.items()
            ]
        }]
    }
    httpx.post(WEBHOOK_URL, json=message)
```

### 6.2 알림 예시

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

## 7. 구현 단계

### Phase 1: 스케줄러 인프라
- [ ] `scripts/scheduler/` 디렉토리 구조 생성
- [ ] `notifier.py` 알림 모듈 구현
- [ ] 환경 변수에 Webhook URL 추가

### Phase 2: 작업 래퍼 스크립트
- [ ] `task_nas_scan.py` 구현
- [ ] `task_iconik_to_sheet.py` 구현
- [ ] `task_sheet_to_iconik.py` 구현
- [ ] 각 스크립트에 로깅 및 알림 연동

### Phase 3: Task Scheduler 등록
- [ ] `register_scheduler.ps1` 작성
- [ ] `unregister_scheduler.ps1` 작성
- [ ] 테스트 실행

### Phase 4: 문서화
- [ ] `docs/SCHEDULER_SETUP.md` 업데이트
- [ ] PRD 최종 업데이트

---

## 8. 성공 지표

| 지표 | 목표 |
|------|------|
| 일일 작업 성공률 | > 95% |
| 평균 총 실행 시간 | < 60분 |
| 알림 지연 시간 | < 1분 |

---

## 9. 리스크 및 대응

| 리스크 | 대응 방안 |
|--------|----------|
| NAS 드라이브 미연결 | 시작 전 드라이브 연결 확인, 알림 |
| Iconik API 타임아웃 | 재시도 로직 (3회), 배치 크기 조절 |
| Sheets API 할당량 초과 | 요청 간격 조절 (100ms) |
| 이전 작업 미완료 | 락 파일로 중복 실행 방지 |

---

## 10. 핵심 파일 경로

### 기존 스크립트
- `D:\AI\claude01\pokergo_crawling\scripts\daily_scan.py`
- `D:\AI\claude01\pokergo_crawling\src\migrations\iconik2sheet\scripts\run_full_metadata.py`
- `D:\AI\claude01\pokergo_crawling\src\migrations\iconik2sheet\scripts\reverse_sync.py`

### 환경 설정
- `D:\AI\claude01\pokergo_crawling\.env`
- `D:\AI\claude01\pokergo_crawling\src\migrations\iconik2sheet\.env.local`

### 문서
- `D:\AI\claude01\pokergo_crawling\docs\SCHEDULER_SETUP.md`

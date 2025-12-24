# PRD-ICONIK-BACKUP-CLEANUP

Iconik에서 Backup 파일 삭제 - Primary만 유지

**Version**: 1.0 | **Date**: 2025-12-24 | **Status**: Draft

---

## 1. 개요

### 1.1 목적

Master_Catalog 시트에서 Role="Backup"으로 표시된 파일을 Iconik에서 삭제하여 스토리지를 최적화하고 중복 관리 비용을 절감합니다.

### 1.2 배경

| 항목 | 내용 |
|------|------|
| 문제 | Iconik에 Primary와 Backup 파일 모두 존재하여 스토리지 낭비 |
| 현황 | Iconik: ~2,854 assets (General: ~1,042, Subclips: ~1,812) |
| 해결 | Master_Catalog에서 Backup 파일 식별 → Iconik에서 삭제 |
| 결과 | Backup 파일은 NAS(Y: Origin)에만 유지, Iconik에는 Primary만 보관 |

### 1.3 데이터 소스

| 항목 | 내용 |
|------|------|
| 시트 | UDM metadata (`1h27Ha7pR-iYK_Gik8F4FfSvsk4s89sxk49CsU3XP_m4`) |
| 탭 | Master_Catalog (gid=683974539) |
| E열 | Role (Primary/Backup) - 이미 채워져 있음 |
| Q열 | Filename |
| R열 | Full Path |

---

## 2. 아키텍처

```
┌─────────────────────────────┐      ┌─────────────────────────────┐
│  Master_Catalog (Sheet)     │      │  Iconik MAM System          │
│                             │      │                             │
│  Role = "Backup"            │      │  DELETE /assets/v1/assets/  │
│  Filename (Q열)             │─────▶│  {asset_id}/                │
│  Full Path (R열)            │      │                             │
└─────────────────────────────┘      └─────────────────────────────┘
            │                                    ▲
            │    ┌──────────────────────────┐    │
            └───▶│  BackupCleanupService    │────┘
                 │                          │
                 │  1. Load Backup files    │
                 │  2. Match to Iconik      │
                 │  3. Dry-run / Execute    │
                 │  4. Generate report      │
                 └──────────────────────────┘
```

### 2.1 데이터 흐름

```
1. Master_Catalog 시트에서 Role="Backup" 행 조회
2. Filename 컬럼에서 파일명 추출 (확장자 제거)
3. Iconik에서 전체 Asset 목록 조회
4. Filename (stem) ↔ Asset title 매칭
5. 매칭된 Asset 중 type="ASSET"만 삭제 대상 (Subclip 제외)
6. Dry-run: 삭제 예정 목록 출력
7. Execute: Iconik API로 삭제 실행
8. 결과 리포트 생성
```

---

## 3. 매칭 전략

### 3.1 Filename → Asset Title 매핑

Master_Catalog의 Filename과 Iconik Asset title은 확장자 제외하고 동일합니다.

```python
# 예시
# Master_Catalog Filename: "2010 WSOP ME08.mov"
# Iconik Asset title: "2010 WSOP ME08"

from pathlib import Path
filename = "2010 WSOP ME08.mov"
stem = Path(filename).stem  # "2010 WSOP ME08"
# stem == iconik_asset.title → Match!
```

### 3.2 매칭 알고리즘

```python
def find_backup_assets(
    backup_filenames: set[str],
    iconik_assets: list[IconikAsset]
) -> list[str]:
    """Find Iconik asset IDs that match backup filenames.

    Args:
        backup_filenames: Set of backup file stems (without extension)
        iconik_assets: All Iconik assets

    Returns:
        List of asset IDs to delete
    """
    to_delete = []
    for asset in iconik_assets:
        # Subclip 제외: type == "ASSET"만 삭제
        if asset.title in backup_filenames and asset.type == "ASSET":
            to_delete.append(asset.id)
    return to_delete
```

### 3.3 Edge Cases

| 케이스 | 처리 방법 |
|--------|----------|
| Backup 파일이 Iconik에 없음 | Skip (이미 삭제됨) |
| 동일 filename에 여러 Asset | 모두 삭제 대상 (경고 로깅) |
| Subclip | 삭제 안 함 (type="ASSET"만 삭제) |

---

## 4. 안전 장치

### 4.1 Dry-Run Mode (Default)

```python
def run(self, dry_run: bool = True) -> CleanupResult:
    """
    dry_run=True (기본값): 삭제 대상만 출력, 실제 삭제 없음
    dry_run=False: 실제 삭제 실행
    """
```

### 4.2 Confirmation Prompt

```python
if not dry_run:
    print(f"\n⚠️  WARNING: About to delete {len(to_delete)} assets from Iconik!")
    print("This action is IRREVERSIBLE.")
    confirm = input("Type 'DELETE' to confirm: ")
    if confirm != "DELETE":
        print("Aborted.")
        return
```

### 4.3 Batch Processing with Delay

```python
BATCH_SIZE = 50
DELAY_BETWEEN_BATCHES = 2  # seconds

for i in range(0, len(to_delete), BATCH_SIZE):
    batch = to_delete[i:i+BATCH_SIZE]
    for asset_id in batch:
        client.delete_asset(asset_id)
    time.sleep(DELAY_BETWEEN_BATCHES)
```

### 4.4 Logging

```python
import logging
from datetime import datetime

# 로그 파일: data/cleanup_logs/backup_cleanup_YYYYMMDD_HHMMSS.log
log_file = f"data/cleanup_logs/backup_cleanup_{datetime.now():%Y%m%d_%H%M%S}.log"
```

---

## 5. 구현 파일

### 신규 생성 (4개)

| 파일 | 용도 |
|------|------|
| `sync/backup_loader.py` | Master_Catalog에서 Backup 파일 목록 로드 |
| `sync/backup_cleanup.py` | 핵심 삭제 로직 (BackupCleanupService) |
| `sync/cleanup_report.py` | 결과 리포트 생성 |
| `scripts/cleanup_backups.py` | CLI 엔트리포인트 |

### 참조 (기존)

| 파일 | 참조 내용 |
|------|----------|
| `sync/master_catalog.py` | 시트 읽기 패턴 |
| `iconik/client.py` | `delete_asset()` 메서드 |

---

## 6. CLI 사용법

```powershell
cd src/migrations/iconik2sheet

# Dry run (기본) - 삭제 대상만 출력
python -m scripts.cleanup_backups

# 실행 - 실제 삭제 (DELETE 타이핑 확인)
python -m scripts.cleanup_backups --execute

# CSV 리포트 저장
python -m scripts.cleanup_backups --output cleanup_report.csv
```

---

## 7. 성공 지표

| 지표 | 목표값 |
|------|--------|
| Backup 파일 식별률 | 100% |
| 매칭 정확도 | >= 99% |
| 삭제 성공률 | >= 95% |
| 처리 시간 | < 15분 |
| Dry-run 지원 | 필수 |

---

## 8. 리스크 및 대응

| 리스크 | 영향도 | 대응 방안 |
|--------|--------|----------|
| 잘못된 파일 삭제 | High | Dry-run 필수, 'DELETE' 타이핑 확인 |
| Subclip orphan | Medium | type="ASSET"만 삭제, Subclip 유지 |
| Rate Limit | Low | Batch 처리 (50개/배치, 2초 딜레이) |
| API 인증 만료 | Low | health_check() 선행 실행 |

---

## 9. 파일 구조

```
src/migrations/iconik2sheet/
├── sync/
│   ├── backup_loader.py      # 신규
│   ├── backup_cleanup.py     # 신규
│   ├── cleanup_report.py     # 신규
│   └── master_catalog.py     # 참조
├── iconik/
│   └── client.py             # delete_asset() 사용
└── scripts/
    └── cleanup_backups.py    # 신규 CLI
```

---

## 변경 이력

| 버전 | 날짜 | 변경 내용 |
|------|------|----------|
| 1.0 | 2025-12-24 | 초안 작성 |

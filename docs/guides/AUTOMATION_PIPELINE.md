# NAMS 자동화 파이프라인

NAS Asset Management System 자동화 파이프라인 설계 및 실행 가이드.

**버전**: 1.0
**날짜**: 2025-12-17

---

## 1. 파이프라인 개요

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        NAMS 자동화 파이프라인                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   [Phase 1]          [Phase 2]          [Phase 3]          [Phase 4]       │
│   NAS 스캔           패턴 매칭          PokerGO 매칭       시트 내보내기    │
│   ┌──────────┐      ┌──────────┐      ┌──────────┐      ┌──────────┐      │
│   │ scan_nas │  ──▶ │ pattern  │  ──▶ │ matching │  ──▶ │ export   │      │
│   │   .py    │      │ _engine  │      │   .py    │      │ _4sheets │      │
│   └──────────┘      └──────────┘      └──────────┘      └──────────┘      │
│        │                 │                 │                 │             │
│        ▼                 ▼                 ▼                 ▼             │
│   NasFile 생성      메타데이터 추출    AssetGroup 매칭   Google Sheets    │
│   (is_excluded)     (year, region,    (pokergo_episode   (5개 시트)       │
│                      event_type,       _id, score)                        │
│                      episode)                                              │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. 실행 명령어

### 2.1 전체 파이프라인 (원클릭)

```powershell
# 전체 파이프라인 실행
python scripts/run_pipeline.py --mode full

# 증분 업데이트 (신규 파일만)
python scripts/run_pipeline.py --mode incremental
```

### 2.2 단계별 실행

```powershell
# Phase 1: NAS 스캔
python scripts/scan_nas.py --mode full --folder all

# Phase 2: 패턴 매칭 (스캔 시 자동 실행됨)
# pattern_engine.py는 scanner.py 내부에서 호출

# Phase 3: PokerGO 매칭
python -c "
from src.nams.api.services.matching import run_matching, update_match_categories
from src.nams.api.database.session import get_db_context

result = run_matching(min_score=0.5)
print(f'Matching: {result}')

with get_db_context() as db:
    cat_result = update_match_categories(db)
    print(f'Categories: {cat_result}')
"

# Phase 4: Google Sheets 내보내기
python scripts/export_4sheets.py
```

---

## 3. 매칭 규칙 (v5.0)

> **상세 규칙**: [MATCHING_RULES.md](../core/MATCHING_RULES.md) 참조

### 핵심 규칙 요약

| 규칙 | 설명 |
|------|------|
| **Region 매칭** | EU/APAC/PARADISE 등 비-LV 그룹은 해당 지역 에피소드만 매칭 |
| **Episode 매칭** | Episode 불일치 시 스킵, Episode-less 그룹 제한 (2003년 이후) |
| **Event Type 매칭** | GM/HU → Main Event 매칭 방지, Event Type 없는 그룹 → BR 매칭 방지 |
| **DUPLICATE 감지** | 제외 파일 필터링 후 Group 기반 중복 감지 |

### v5.0 개선 결과

| 지표 | v4.2 | v5.0 | 변화 |
|------|------|------|------|
| DUPLICATE | 53 | 18 | -35 (66% 감소) |
| OK | 730 | 765 | +35 |

---

## 4. PokerGO 데이터 가용성

| 지역 | PokerGO 데이터 | 매칭 결과 |
|------|---------------|----------|
| **LV** (Las Vegas) | 있음 (1973-2025) | MATCHED |
| **EU** (Europe) | 일부 (2008-2021) | MATCHED / NAS_ONLY |
| **APAC** | 없음 | NAS_ONLY_MODERN |
| **PARADISE** | 없음 | NAS_ONLY_MODERN |
| **CYPRUS** | 없음 | NAS_ONLY_MODERN |
| **LONDON** | 없음 | NAS_ONLY_MODERN |
| **LA** (Circuit) | 없음 | NAS_ONLY_MODERN |

---

## 5. 제외 조건

| 조건 | 기준 | 플래그 |
|------|------|--------|
| 파일 크기 | < 1GB | `is_excluded=True` |
| 영상 길이 | < 30분 | `is_excluded=True` |
| 키워드 | `clip`, `highlight`, `circuit`, `paradise` | `is_excluded=True` |
| Hand Clip | `^\d+-wsop-`, `-hs-`, `hand_` | `is_excluded=True` |

**중요**: 제외 파일도 DB에 저장됨 (DUPLICATE 감지에서만 제외)

---

## 6. 파이프라인 스크립트

### run_pipeline.py (신규 생성)

```python
#!/usr/bin/env python
"""NAMS 자동화 파이프라인 실행 스크립트."""
import argparse
import subprocess
import sys

def run_phase(name: str, command: list) -> bool:
    """단일 phase 실행."""
    print(f"\n{'='*60}")
    print(f"[{name}] 실행 중...")
    print(f"{'='*60}")

    result = subprocess.run(command, capture_output=False)

    if result.returncode != 0:
        print(f"[ERROR] {name} 실패!")
        return False

    print(f"[OK] {name} 완료")
    return True


def main():
    parser = argparse.ArgumentParser(description='NAMS 자동화 파이프라인')
    parser.add_argument('--mode', choices=['full', 'incremental'], default='incremental',
                        help='스캔 모드 (full: 전체 재스캔, incremental: 증분)')
    parser.add_argument('--skip-scan', action='store_true', help='스캔 단계 건너뛰기')
    parser.add_argument('--skip-match', action='store_true', help='매칭 단계 건너뛰기')
    parser.add_argument('--skip-export', action='store_true', help='내보내기 단계 건너뛰기')
    args = parser.parse_args()

    print("="*60)
    print("NAMS 자동화 파이프라인")
    print(f"모드: {args.mode}")
    print("="*60)

    # Phase 1: NAS 스캔
    if not args.skip_scan:
        if not run_phase("Phase 1: NAS 스캔", [
            sys.executable, "scripts/scan_nas.py",
            "--mode", args.mode, "--folder", "all"
        ]):
            return 1

    # Phase 2: PokerGO 매칭
    if not args.skip_match:
        if not run_phase("Phase 2: PokerGO 매칭", [
            sys.executable, "-c", '''
from src.nams.api.database.session import get_db_context
from src.nams.api.database.models import AssetGroup
from src.nams.api.services.matching import run_matching, update_match_categories

# 기존 매칭 초기화
with get_db_context() as db:
    db.query(AssetGroup).update({
        AssetGroup.pokergo_episode_id: None,
        AssetGroup.pokergo_title: None,
        AssetGroup.pokergo_match_score: None,
        AssetGroup.match_category: None
    })
    db.commit()

# 매칭 실행
result = run_matching(min_score=0.5)
print(f"Matching: {result}")

# 카테고리 업데이트
with get_db_context() as db:
    cat_result = update_match_categories(db)
    print(f"Categories: {cat_result}")
'''
        ]):
            return 1

    # Phase 3: Google Sheets 내보내기
    if not args.skip_export:
        if not run_phase("Phase 3: Google Sheets 내보내기", [
            sys.executable, "scripts/export_4sheets.py"
        ]):
            return 1

    print("\n" + "="*60)
    print("[OK] 파이프라인 완료!")
    print("="*60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

---

## 7. 출력 시트 구조

### 7.1 5개 시트 시스템

| # | 시트명 | 용도 | 예상 행 수 |
|---|--------|------|-----------|
| 1 | NAS_Origin_Raw | Y: 드라이브 파일 | 0 (현재) |
| 2 | NAS_Archive_Raw | Z: 드라이브 파일 | ~1,300 |
| 3 | NAS_PokerGO_Raw | X: 드라이브 파일 | ~250 |
| 4 | PokerGO_Raw | PokerGO 메타데이터 | 828 |
| 5 | Matching_Integrated | 통합 매칭 결과 | ~1,900 |

### 7.2 Action 컬럼 로직

```python
# Action 결정 우선순위
if is_excluded:
    action = "Excluded"
elif filename in duplicate_files and not is_backup:
    action = "DUPLICATE"  # 백업본은 DUPLICATE 표시 안 함
elif has_origin and not has_archive:
    action = "-> Archive"
elif not has_nas and has_pokergo:
    action = "-> Find NAS"
else:
    action = ""  # OK
```

---

## 8. 모니터링 지표

### 8.1 핵심 KPI

| 지표 | 목표 | 현재 (v5.0) |
|------|------|-------------|
| DUPLICATE | < 20 | 18 |
| OK | > 700 | 765 |
| MATCHED Groups | > 350 | 365 |
| 제외 파일 | ~500 | 502 |

### 8.2 변경 추적

```powershell
# 매칭 통계 확인
python -c "
from src.nams.api.services.matching import get_matching_summary
from src.nams.api.database.session import get_db_context

with get_db_context() as db:
    summary = get_matching_summary(db)
    print(summary)
"
```

---

## 9. 트러블슈팅

### 9.1 DUPLICATE 증가 시

1. **Region 확인**: 새 파일의 region이 올바르게 추출되었는지 확인
2. **Episode 확인**: episode 번호가 제대로 추출되었는지 확인
3. **Event Type 확인**: event_type이 설정되었는지 확인

```python
# 특정 그룹 디버깅
from src.nams.api.database.session import get_db_context
from src.nams.api.database.models import AssetGroup, Region, EventType

with get_db_context() as db:
    group = db.query(AssetGroup).filter(AssetGroup.group_id == '2024_ME_01').first()
    region = db.query(Region).filter(Region.id == group.region_id).first()
    etype = db.query(EventType).filter(EventType.id == group.event_type_id).first()

    print(f"Group: {group.group_id}")
    print(f"Region: {region.code if region else None}")
    print(f"Event Type: {etype.code if etype else None}")
    print(f"Episode: {group.episode}")
    print(f"PokerGO: {group.pokergo_title}")
```

### 9.2 매칭률 저하 시

1. **패턴 확인**: 새 파일 형식에 맞는 패턴이 있는지 확인
2. **PokerGO 데이터 확인**: 해당 연도/지역 에피소드가 DB에 있는지 확인

---

## 10. 예정 작업

### 10.1 수작업 필요 항목

| 항목 | 건수 | 작업 |
|------|------|------|
| HU/GM 대전자 매칭 | 4 | 영상 확인 후 수동 지정 |
| 2007 ESPN Show 매핑 | 8 | Show 번호 → Day 매핑 테이블 |
| CLASSIC Era 그룹 통합 | 3 | 동일 연도 그룹 병합 |

### 10.2 자동화 개선

- [ ] 스케줄러 (일별 증분 스캔)
- [ ] 변경 알림 (Slack/Email)
- [ ] 대시보드 연동 (Grafana)

---

## 변경 이력

| 날짜 | 버전 | 변경 내용 |
|------|------|----------|
| 2025-12-17 | 1.0 | 초기 문서 작성, v5.0 매칭 규칙 반영 |

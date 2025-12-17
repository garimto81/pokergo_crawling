# PRD: NAMS 코드 리팩토링

**Version**: 1.0.0
**Date**: 2025-12-16
**Status**: Draft

---

## 1. 개요

### 1.1 배경
`/check --all` 실행 결과 다음 코드 품질 이슈가 발견됨:
- Long functions: 17개 (50줄 초과)
- Deep nesting: 3개 (4레벨 초과)
- Lint issues: 5개
- E2E 테스트: 미작성

### 1.2 목표
- 함수 분리로 가독성/유지보수성 향상
- 테스트 커버리지 확보 (E2E 80%+)
- 코드 품질 기준 충족

---

## 2. 현황 분석

### 2.1 Long Functions (17개)

| 파일 | 함수 | 줄 수 | 우선순위 |
|------|------|-------|----------|
| `init_db.py` | `seed_patterns` | 154 | HIGH |
| `export.py` | `get_full_matching_data` | 169 | HIGH |
| `export.py` | `export_full_matching_to_sheets` | 94 | HIGH |
| `export.py` | `get_google_sheets_data` | 80 | MEDIUM |
| `routers/files.py` | `list_files` | 80 | MEDIUM |
| `routers/groups.py` | `list_groups` | 77 | MEDIUM |
| `catalog_service.py` | `generate_catalog_title` | 72 | MEDIUM |
| `catalog_service.py` | `parse_group_id` | 71 | MEDIUM |
| `routers/process.py` | `export_data` | 66 | LOW |
| `export.py` | `get_unmatched_pokergo_data` | 66 | LOW |
| `routers/process.py` | `scan_nas` | 64 | LOW |
| `routers/process.py` | `run_full_pipeline` | 62 | LOW |
| `routers/process.py` | `migrate_json_data` | 61 | LOW |
| `routers/groups.py` | `get_group` | 59 | LOW |
| `routers/patterns.py` | `test_pattern` | 56 | LOW |
| `init_db.py` | `seed_exclusion_rules` | 53 | LOW |

### 2.2 Deep Nesting (3개)

| 파일 | 라인 | 레벨 |
|------|------|------|
| `routers/process.py` | 201 | 6 |
| `export.py` | 709 | 6 |
| `export.py` | 710 | 7 |

### 2.3 Lint Issues (5개)

| 파일 | 이슈 | 타입 |
|------|------|------|
| `add_match_category.py` | Import sorting | I001 |
| `add_match_category.py` | Unused import | F401 |
| `add_match_category.py` | Line too long | E501 |
| `add_match_category.py` | f-string no placeholder | F541 |
| `Patterns.tsx` | no-explicit-any | TS |

### 2.4 E2E 테스트 현황

| 컴포넌트 | 테스트 | 상태 |
|----------|--------|------|
| Dashboard | 없음 | TODO |
| Files | 없음 | TODO |
| Groups | 없음 | TODO |
| Patterns | 없음 | TODO |
| Settings | 없음 | TODO |

---

## 3. 리팩토링 계획

### 3.1 Phase 1: Critical Functions (HIGH)

#### 3.1.1 `init_db.py::seed_patterns` (154줄 → ~30줄)

**현재 문제:**
- 14개 패턴을 하드코딩
- 단일 함수에 모든 로직

**리팩토링:**
```python
# Before
def seed_patterns(db: Session):
    patterns = [
        Pattern(name="P0", regex="...", ...),
        Pattern(name="P1", regex="...", ...),
        # ... 14개
    ]
    for p in patterns:
        db.add(p)

# After
PATTERNS_CONFIG = [
    {"name": "P0", "priority": 1, "regex": "...", ...},
    # ...
]

def seed_patterns(db: Session):
    for config in PATTERNS_CONFIG:
        _create_pattern_if_not_exists(db, config)

def _create_pattern_if_not_exists(db: Session, config: dict):
    existing = db.query(Pattern).filter_by(name=config["name"]).first()
    if not existing:
        db.add(Pattern(**config))
```

#### 3.1.2 `export.py::get_full_matching_data` (169줄 → ~50줄)

**현재 문제:**
- 4개 시트 데이터를 단일 함수에서 생성
- 중복 쿼리 로직

**리팩토링:**
```python
# Before
def get_full_matching_data(db):
    # Sheet 1 로직 (40줄)
    # Sheet 2 로직 (40줄)
    # Sheet 3 로직 (40줄)
    # Sheet 4 로직 (40줄)
    return {...}

# After
def get_full_matching_data(db):
    return {
        "matched": _get_matched_data(db),
        "nas_only": _get_nas_only_data(db),
        "pokergo_only": _get_pokergo_only_data(db),
        "summary": _get_summary_data(db),
    }

def _get_matched_data(db): ...
def _get_nas_only_data(db): ...
def _get_pokergo_only_data(db): ...
def _get_summary_data(db): ...
```

### 3.2 Phase 2: Medium Priority Functions

| 함수 | 전략 |
|------|------|
| `list_files` | 쿼리 빌더 분리 |
| `list_groups` | 쿼리 빌더 분리 |
| `generate_catalog_title` | 타입별 생성기 분리 |
| `parse_group_id` | 파서 클래스 추출 |

### 3.3 Phase 3: Deep Nesting 해결

**패턴: Early Return**
```python
# Before
def process():
    if condition1:
        if condition2:
            if condition3:
                # deep logic

# After
def process():
    if not condition1:
        return
    if not condition2:
        return
    if not condition3:
        return
    # flat logic
```

### 3.4 Phase 4: E2E 테스트 작성

#### 4.1 테스트 시나리오

| 페이지 | 테스트 케이스 |
|--------|--------------|
| Dashboard | 통계 카드 표시, 차트 렌더링 |
| Files | 파일 목록 로드, 필터링, 페이지네이션 |
| Groups | 그룹 목록, 상세 보기, 매칭 상태 |
| Patterns | 패턴 목록, 테스트 실행 |
| Settings | 설정 저장/불러오기 |

#### 4.2 테스트 파일 구조

```
src/nams/ui/
└── e2e/
    ├── dashboard.spec.ts
    ├── files.spec.ts
    ├── groups.spec.ts
    ├── patterns.spec.ts
    └── settings.spec.ts
```

---

## 4. 작업 항목

### 4.1 Checklist

- [ ] Phase 1: Critical Functions (3개)
  - [ ] `seed_patterns` 리팩토링
  - [ ] `get_full_matching_data` 리팩토링
  - [ ] `export_full_matching_to_sheets` 리팩토링
- [ ] Phase 2: Medium Priority (4개)
  - [ ] `list_files` 리팩토링
  - [ ] `list_groups` 리팩토링
  - [ ] `generate_catalog_title` 리팩토링
  - [ ] `parse_group_id` 리팩토링
- [ ] Phase 3: Deep Nesting (3개)
  - [ ] `process.py:201` 수정
  - [ ] `export.py:709-710` 수정
- [ ] Phase 4: Lint Fix
  - [ ] `ruff check --fix scripts/`
  - [ ] `Patterns.tsx` any 타입 수정
- [ ] Phase 5: E2E Tests
  - [ ] Playwright 설정
  - [ ] Dashboard 테스트
  - [ ] Files 테스트
  - [ ] Groups 테스트
  - [ ] Patterns 테스트

### 4.2 예상 작업량

| Phase | 파일 수 | 예상 변경 |
|-------|---------|-----------|
| 1 | 2 | ~300줄 |
| 2 | 4 | ~200줄 |
| 3 | 2 | ~50줄 |
| 4 | 2 | ~10줄 |
| 5 | 5 | ~500줄 (신규) |

---

## 5. 성공 기준

| 항목 | 현재 | 목표 |
|------|------|------|
| Long functions | 17개 | 0개 |
| Deep nesting | 3개 | 0개 |
| Lint errors | 5개 | 0개 |
| E2E coverage | 0% | 80%+ |
| `/check --all` | WARN | PASS |

---

## 6. 참고

- 관련 파일: `src/nams/api/`
- 검사 명령: `/check --all`
- 린트 자동수정: `ruff check --fix src/ scripts/`

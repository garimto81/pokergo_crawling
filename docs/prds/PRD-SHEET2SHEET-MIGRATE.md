# PRD: Sheet-to-Sheet Migration Tool

## 개요

| 항목 | 내용 |
|------|------|
| **목적** | 외부 Google Sheets 데이터를 Iconik_Full_Metadata 시트로 통합 |
| **스코프** | 다중 탭 병합, 컬럼 매핑, 타임코드 변환, 검증 |
| **상태** | Implemented (v1.0.0) |

## 시트 정보

| 구분 | ID | 용도 |
|------|-----|------|
| **Source** | `1_RN_W_ZQclSZA0Iez6XniCXVtjkkd5HNZwiT6l-z6d4` | Archive Metadata (8개 탭, 339+ 행) |
| **Target** | `1pUMPKe-OsKc-Xd8lH1cP9ctJO4hj3keXY5RwNFp2Mtk` | Iconik_Full_Metadata (35컬럼) |

---

## 기능 요구사항

### FR-1: 소스 시트 분석

- 모든 탭 이름 조회
- 각 탭별 컬럼 헤더 추출
- 샘플 데이터 미리보기
- 타겟 컬럼 매핑 커버리지 분석

### FR-2: 다중 탭 병합

- 8개 탭 데이터를 단일 리스트로 병합
- 탭 이름에서 메타데이터 추출 (Year, Location, Tournament)
- 빈 탭 스킵

### FR-3: 컬럼 매핑

**직접 매핑**:

| 소스 컬럼 | 타겟 컬럼 |
|-----------|-----------|
| File No. | id |
| File Name | title |
| In | time_start_S, time_start_ms |
| Out | time_end_S, time_end_ms |
| Nas Folder Link | Source |
| Hand Grade | HandGrade |
| Hands | HANDTag |

**패턴 매핑**:

| 소스 패턴 | 타겟 컬럼 |
|-----------|-----------|
| Tag (Player) x3 | PlayersTags (쉼표 구분 병합) |
| Tag (Poker Play) x7 | PokerPlayTags (쉼표 구분 병합) |
| Tag (Emotion) x2 | Emotion (쉼표 구분 병합) |
| Winner | PlayersTags에 포함 |

**탭 유래 필드**:

| 추출 대상 | 타겟 컬럼 | 예시 |
|-----------|-----------|------|
| 연도 | Year_ | "2024 WSOPC LA" → "2024" |
| 위치 | Location | "2025 WSOP Las Vegas" → "Las Vegas" |
| 토너먼트 | Tournament | "WSOPE 2024" → "WSOP Europe" |
| 설명 | Description | "{탭이름}: {Hands}" |

### FR-4: Dry Run 미리보기

- 실제 쓰기 없이 매핑 결과 미리보기
- 소스/타겟 행 수 비교
- 샘플 출력 (처음 3행)

### FR-5: Append/Overwrite 모드

| 모드 | 동작 |
|------|------|
| **append** (기본) | 기존 데이터 유지, 신규 행 추가 |
| **overwrite** | 시트 초기화 후 전체 재작성 |

---

## 비기능 요구사항

### NFR-1: 배치 처리

- 100행 단위 배치 (설정 가능)

### NFR-2: 에러 로깅

- 연결 오류, 권한 오류 명확한 메시지
- 경고/에러 분리 리포트

### NFR-3: 롤백 불가

- Google Sheets API 특성상 롤백 불가
- Dry Run 필수 권장

---

## 데이터 모델

### 소스 구조 (Archive Metadata)

```
Row 1: (빈 행)
Row 2: (빈 행)
Row 3: 헤더 (File No., File Name, Nas Folder Link, In, Out, Hand Grade, Winner, Hands, Tag (Player) x3, Tag (Poker Play) x7, Tag (Emotion) x2)
Row 4+: 데이터
```

### 타겟 구조 (Iconik_Full_Metadata - 35컬럼)

```
[기본] id, title
[타임코드] time_start_ms, time_end_ms, time_start_S, time_end_S
[메타데이터] Description, ProjectName, ProjectNameTag, SearchTag, Year_, Location, Venue, EpisodeEvent, Source, Scene, GameType
[포커] PlayersTags, HandGrade, HANDTag, EPICHAND, Tournament, PokerPlayTags
[태그] Adjective, Emotion, AppearanceOutfit, SceneryObject, _gcvi_tags
[플래그] Badbeat, Bluff, Suckout, Cooler, RUNOUTTag, PostFlop, All-in
```

---

## 구현 세부사항

### 프로젝트 위치

`D:\AI\claude01\pokergo_crawling\src\migrations\sheet2sheet_migrate\`

### 의존성

- google-api-python-client>=2.0.0
- google-auth>=2.0.0
- pydantic>=2.0.0
- pydantic-settings>=2.0.0

### 환경 변수

```env
GOOGLE_SERVICE_ACCOUNT_PATH=path/to/service_account.json
SOURCE_SPREADSHEET_ID=1_RN_W_ZQclSZA0Iez6XniCXVtjkkd5HNZwiT6l-z6d4
TARGET_SPREADSHEET_ID=1pUMPKe-OsKc-Xd8lH1cP9ctJO4hj3keXY5RwNFp2Mtk
TARGET_SHEET_NAME=Iconik_Full_Metadata
```

---

## 사용법

```powershell
# 분석 스크립트
python scripts/analyze_source_sheet.py

# Dry Run (기본)
python scripts/run_sheet_migration.py

# 매핑 미리보기
python scripts/run_sheet_migration.py --show-mapping

# 실행 (append 모드)
python scripts/run_sheet_migration.py --execute

# 실행 (overwrite 모드)
python scripts/run_sheet_migration.py --execute --mode overwrite
```

---

## Iconik API 연동

### 개요

Archive_Metadata → Iconik MAM 직접 마이그레이션 지원

### Iconik 필드 호환성

Iconik 메타데이터 뷰의 **19개 필드가 dropdown 타입**으로, 사전 정의된 값만 허용합니다.

#### 마이그레이션 가능 필드 (자유 텍스트)

| 필드 | 타입 | 설명 |
|------|------|------|
| Description | text | 설명 |
| Year_ | text | 연도 |
| Location | text | 위치 |
| PlayersTags | multi-select | 플레이어 태그 |
| PokerPlayTags | multi-select | 포커 플레이 태그 |

#### 마이그레이션 제외 필드 (dropdown - 값 불일치)

| 필드 | Archive 값 | Iconik 허용 값 |
|------|-----------|---------------|
| HandGrade | `1`, `2`, `3` | `★`, `★★`, `★★★` |
| HANDTag | `88 vs JJ` | `AA vs KK` 등 정의된 패턴 |
| Tournament | `WSOP Circuit` | `bracelet`, `survive` 등 |
| Source | NAS 경로 | `Clean`, `PGM` 등 |

**전체 제외 목록**: HandGrade, HANDTag, Tournament, Source, Emotion, Venue, GameType, Scene, Adjective, EPICHAND, AppearanceOutfit, SceneryObject, Badbeat, Bluff, Suckout, Cooler, PostFlop, RUNOUTTag, All-in

### Iconik 마이그레이션 사용법

```powershell
# Dry Run
python scripts/test_iconik_migration.py

# 실행 (1번 행)
python scripts/test_iconik_migration.py --execute --row 1

# 특정 Asset ID 지정
python scripts/test_iconik_migration.py --execute --row 5 --asset-id <UUID>
```

### 관련 이슈

- [#19](https://github.com/garimto81/pokergo_crawling/issues/19) - Iconik 메타데이터 오류값 추출

---

## 검증 체크리스트

- [x] 소스 시트 분석 스크립트 실행 성공
- [x] 모든 탭 데이터 읽기 확인 (8개 탭, 339행)
- [x] 컬럼 매핑 정의 완료 (100% 커버리지)
- [x] Dry Run 출력 정상
- [x] Overwrite 모드 테스트 (Archive_Metadata 탭 생성)
- [x] Iconik API 연동 테스트
- [x] Iconik 필드 호환성 분석
- [x] PRD 문서 작성
- [x] CLAUDE.md 업데이트

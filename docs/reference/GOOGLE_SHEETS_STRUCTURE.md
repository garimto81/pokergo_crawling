# Google Sheets 구조 문서

**Version**: 1.0 | **Date**: 2025-12-23

---

## 개요

NAMS 프로젝트는 2개의 Google Spreadsheet를 사용합니다.

| 시트명 | ID | 용도 |
|--------|-----|------|
| **UDM metadata** | `1h27Ha7pR-iYK_Gik8F4FfSvsk4s89sxk49CsU3XP_m4` | 마스터 카탈로그 |
| **Iconik metadata** | `1pUMPKe-OsKc-Xd8lH1cP9ctJO4hj3keXY5RwNFp2Mtk` | Iconik 메타데이터 |

---

## 1. UDM metadata (GGP_UniversalDataModel)

**URL**: https://docs.google.com/spreadsheets/d/1h27Ha7pR-iYK_Gik8F4FfSvsk4s89sxk49CsU3XP_m4/edit

### 탭 목록 (3개)

| 탭명 | 컬럼 수 | 용도 |
|------|--------|------|
| Master_Catalog | 18 | 마스터 카탈로그 (메인) |
| HCL_Clips | 15 | HCL 클립 정보 |
| Summary | 1 | 요약 정보 |

### Master_Catalog 컬럼 (18개)

| # | 컬럼명 | 설명 |
|---|--------|------|
| 0 | No | 순번 |
| 1 | Origin | 원본 여부 |
| 2 | Entry Key | 엔트리 키 |
| 3 | Match Type | 매칭 유형 |
| 4 | Role | 역할 (Primary/Backup) |
| 5 | Backup Type | 백업 유형 |
| 6 | Category | 카테고리 |
| 7 | Title | 제목 |
| 8 | PokerGO Title | PokerGO 제목 |
| 9 | Region | 지역 (LV/EU/APAC 등) |
| 10 | Event Type | 이벤트 유형 (ME/BR/HR 등) |
| 11 | Event # | 이벤트 번호 |
| 12 | Day | Day 번호 |
| 13 | Part | Part 번호 |
| 14 | RAW | RAW 여부 |
| 15 | Size (GB) | 파일 크기 |
| 16 | Filename | 파일명 |
| 17 | Full Path | 전체 경로 |

### HCL_Clips 컬럼 (15개)

| # | 컬럼명 |
|---|--------|
| 0 | Video ID |
| 1 | Title |
| 2 | PublishedAt |
| 3 | 2025 clips |
| 4 | 2024 Clips |
| 5 | 2023 Clips |
| 6 | Countdown |
| 7 | Nik Airball's BEST POKER HANDS |
| 8 | Wesley's BEST POKER HANDS |
| 9 | Garrett Adelstein BEST POKER HANDS |
| 10-14 | (추가 컬럼) |

---

## 2. Iconik metadata (iconik Metadata with Timecode)

**URL**: https://docs.google.com/spreadsheets/d/1pUMPKe-OsKc-Xd8lH1cP9ctJO4hj3keXY5RwNFp2Mtk/edit

### 탭 목록 (3개)

| 탭명 | 컬럼 수 | 용도 |
|------|--------|------|
| GGmetadata_and_timestamps | 35 | 메타데이터 + 타임코드 |
| Iconik_Full_Metadata | 35 | 전체 메타데이터 |
| Sync_Log | 7 | 동기화 로그 |

### GGmetadata_and_timestamps / Iconik_Full_Metadata 컬럼 (35개)

#### 기본 정보 (0-5)
| # | 컬럼명 | 설명 |
|---|--------|------|
| 0 | id | Asset ID |
| 1 | title | 제목 |
| 2 | time_start_ms | 시작 시간 (ms) |
| 3 | time_end_ms | 종료 시간 (ms) |
| 4 | time_start_S | 시작 시간 (초) |
| 5 | time_end_S | 종료 시간 (초) |

#### 메타데이터 (6-16)
| # | 컬럼명 | 설명 |
|---|--------|------|
| 6 | Description | 설명 |
| 7 | ProjectName | 프로젝트명 |
| 8 | ProjectNameTag | 프로젝트 태그 |
| 9 | SearchTag | 검색 태그 |
| 10 | Year_ | 연도 |
| 11 | Location | 위치 |
| 12 | Venue | 장소 |
| 13 | EpisodeEvent | 에피소드/이벤트 |
| 14 | Source | 소스 |
| 15 | Scene | 씬 |
| 16 | GameType | 게임 유형 |

#### 포커 관련 (17-26)
| # | 컬럼명 | 설명 |
|---|--------|------|
| 17 | PlayersTags | 플레이어 태그 |
| 18 | HandGrade | 핸드 등급 |
| 19 | HANDTag | 핸드 태그 |
| 20 | EPICHAND | 에픽 핸드 |
| 21 | Tournament | 토너먼트 |
| 22 | PokerPlayTags | 포커 플레이 태그 |
| 23 | Adjective | 형용사 |
| 24 | Emotion | 감정 |
| 25 | AppearanceOutfit | 외모/의상 |
| 26 | SceneryObject | 배경/오브젝트 |

#### 태그 및 플래그 (27-34)
| # | 컬럼명 | 설명 |
|---|--------|------|
| 27 | _gcvi_tags | GCVI 태그 |
| 28 | Badbeat | 배드비트 |
| 29 | Bluff | 블러프 |
| 30 | Suckout | 석아웃 |
| 31 | Cooler | 쿨러 |
| 32 | RUNOUTTag | 런아웃 태그 |
| 33 | PostFlop | 포스트플랍 |
| 34 | All-in | 올인 |

### Sync_Log 컬럼 (7개)

| # | 컬럼명 | 설명 |
|---|--------|------|
| 0 | Sync_ID | 동기화 ID |
| 1 | Sync_Type | 동기화 유형 |
| 2 | Started_At | 시작 시간 |
| 3 | Completed_At | 완료 시간 |
| 4 | Assets_New | 신규 Asset 수 |
| 5 | Assets_Updated | 업데이트 Asset 수 |
| 6 | Status | 상태 |

---

## 스크립트 참조

| 스크립트 | 시트 | 용도 |
|---------|------|------|
| `create_master_catalog.py` | UDM metadata | Master_Catalog 생성 |
| `src/migrations/iconik2sheet/` | Iconik metadata | Iconik → Sheets 동기화 |
| `src/migrations/sheet2iconik/` | Iconik metadata | Sheets → Iconik 동기화 |

---

## 변경 이력

| 버전 | 날짜 | 변경 내용 |
|------|------|----------|
| 1.0 | 2025-12-23 | 초기 문서 작성, 연도별 Catalog 시트 삭제 반영 |

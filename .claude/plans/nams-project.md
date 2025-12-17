# NAMS Project Plan

> NAS Asset Management System - WSOP 52년 역사 DB 체계화 프로젝트

## 프로젝트 목표

3개의 NAS 드라이브(X:/Y:/Z:)와 PokerGO 메타데이터를 통합하여
**1973년부터 현재까지 52년간의 WSOP 콘텐츠 카탈로그**를 구축

---

## 핵심 목표 (4대 목표)

### 1. NAS 파일 통합 관리
- [x] X: 드라이브 (PokerGO Source) 스캔 - 828 files
- [x] Y: 드라이브 (WSOP Backup) 스캔 - 1,568 files
- [x] Z: 드라이브 (Archive) 스캔 - 1,405 files
- [x] 메타데이터 추출 (year, region, event_type, episode)

### 2. PokerGO 매칭
- [x] 828개 PokerGO 에피소드 로드
- [x] NAS 파일과 1:1 자동 매칭
- [ ] 매칭률 53.3% (440/826 그룹) → 목표 80%+
- [x] DUPLICATE 18건으로 감소 (v5.0)

### 3. Asset Grouping
- [x] 동일 콘텐츠 파일 그룹화
- [x] Primary/Backup 구분
- [x] Origin(Y:) ⊆ Archive(Z:) 관계 정립

### 4. 카탈로그 생성
- [x] Google Sheets 5시트 내보내기
- [ ] Netflix 스타일 표시 제목 생성
- [ ] Block F/G 카탈로그 포맷

---

## 데이터 소스

| 소스 | 역할 | 파일 수 |
|------|------|---------|
| **X:** (PokerGO Source) | PokerGO 원본 파일 | 828 |
| **Y:** (WSOP Backup) | Origin 백업 | 1,568 |
| **Z:** (Archive) | Primary 아카이브 | 1,405 |
| **PokerGO JSON** | 메타데이터 | 828 에피소드 |

---

## 산출물

- [x] SQLite DB (통합 매칭 결과)
- [x] Google Sheets 5시트
  - NAS_Origin_Raw
  - NAS_Archive_Raw
  - NAS_PokerGO_Raw
  - PokerGO_Raw
  - Matching_Integrated
- [ ] Catalog Titles (Netflix 스타일)

---

## 현재 상태

| 지표 | 값 |
|------|-----|
| 패턴 추출률 | 97.6% (1,371/1,405) |
| PokerGO 매칭률 | 53.3% (440/826) |
| Total Asset Groups | 826 |
| MATCHED Groups | 440 |
| NAS_ONLY Groups | 386 |
| Active Files | 858 |
| Excluded Files | 547 |
| 문서 버전 | v5.0 |

---

## 남은 작업

1. **수작업 매칭** (18건)
   - HU/GM episode-less: 4건
   - Day-based (2007): 8건
   - CLASSIC Era: 3건
   - Commentary: 3건

2. **카탈로그 제목 생성**
   - Block F/G 포맷 정의
   - Netflix 스타일 표시 제목

3. **자동화 개선**
   - 스케줄러 (일별 증분 스캔)
   - 변경 알림

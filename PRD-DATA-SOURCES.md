# PRD: PokerGO 데이터 소스 분리 관리

**Version**: 1.0.0
**Date**: 2025-12-12
**Status**: 설계 완료

---

## 1. 개요

### 1.1 목표
3가지 데이터 소스를 **분리하여** 수집, 저장, 분석할 수 있는 구조 구축.

### 1.2 데이터 소스

| # | 소스 | 설명 | 상태 |
|---|------|------|------|
| 1 | **YouTube** | youtube.com/@PokerGO 채널 메타데이터 | ✅ 구현 완료 |
| 2 | **PokerGO.com** | 공식 웹사이트 콘텐츠 목록 | 🔜 향후 진행 |
| 3 | **Archive** | 직접 받은 아카이브 파일 목록 | 🔜 다음 단계 |

---

## 2. 데이터 소스별 상세

### 2.1 YouTube (`youtube`)

| 항목 | 내용 |
|------|------|
| **URL** | `youtube.com/@PokerGO` |
| **수집 방식** | yt-dlp 메타데이터 추출 |
| **데이터 형식** | 영상 제목, 설명, 길이, 조회수, 업로드일 등 |
| **예상 규모** | ~3,000+ 영상 |
| **특징** | 무료 클립, 하이라이트, 일부 풀 에피소드 |

#### 수집 데이터 스키마
```json
{
  "video_id": "KQzI62NF7F0",
  "title": "PGT Rags to Riches Recap...",
  "description": "...",
  "url": "https://www.youtube.com/watch?v=...",
  "duration": 4779,
  "upload_date": "2025-12-10",
  "view_count": 12345,
  "like_count": 500,
  "thumbnail_url": "https://i.ytimg.com/vi/..."
}
```

---

### 2.2 PokerGO.com (`pokergo_web`)

| 항목 | 내용 |
|------|------|
| **URL** | `pokergo.com` |
| **수집 방식** | API 크롤링 / 웹 스크래핑 |
| **데이터 형식** | 시리즈, 시즌, 에피소드 구조 |
| **예상 규모** | ~50+ 시리즈, ~5,000+ 에피소드 |
| **특징** | 구독 필요, 풀 에피소드, 라이브 이벤트 |

#### 콘텐츠 구조
```
PokerGO.com
├── Shows (시리즈)
│   ├── High Stakes Poker
│   │   ├── Season 1
│   │   │   ├── Episode 1
│   │   │   ├── Episode 2
│   │   │   └── ...
│   │   └── Season 2
│   ├── Poker After Dark
│   └── ...
├── Events (토너먼트)
│   ├── WSOP 2024
│   └── PGT
└── Live (라이브)
```

#### 수집 데이터 스키마
```json
{
  "episode_id": "pgw-12345",
  "show_id": "high-stakes-poker",
  "show_title": "High Stakes Poker",
  "season": 14,
  "episode": 5,
  "title": "Episode 5 - The Big Game",
  "description": "...",
  "duration": 3600,
  "air_date": "2024-11-15",
  "thumbnail_url": "https://pokergo.com/...",
  "jwplayer_id": "abc123"
}
```

---

### 2.3 Archive (`archive`)

| 항목 | 내용 |
|------|------|
| **소스** | PokerGO로부터 직접 받은 파일 |
| **수집 방식** | 파일명/폴더 구조 파싱 |
| **데이터 형식** | 영상 파일 (.mp4, .mkv 등) |
| **예상 규모** | TBD (파일 목록 분석 후 확정) |
| **특징** | 원본 파일, 고화질, 완전한 아카이브 |

#### 파일 구조 예시
```
Archive/
├── High Stakes Poker/
│   ├── Season 01/
│   │   ├── HSP_S01E01_Pilot.mp4
│   │   ├── HSP_S01E02_The_Setup.mp4
│   │   └── ...
│   └── Season 02/
├── WSOP/
│   ├── 2023/
│   │   ├── Main Event/
│   │   │   ├── Day1A.mp4
│   │   │   └── ...
│   │   └── High Roller/
│   └── 2024/
└── Poker After Dark/
```

#### 파싱 후 데이터 스키마
```json
{
  "file_id": "archive-001",
  "file_path": "High Stakes Poker/Season 01/HSP_S01E01_Pilot.mp4",
  "file_name": "HSP_S01E01_Pilot.mp4",
  "file_size": 2147483648,
  "show_name": "High Stakes Poker",
  "season": 1,
  "episode": 1,
  "title": "Pilot",
  "duration": null,
  "parsed_from_filename": true
}
```

---

## 3. 분리 저장 구조

### 3.1 디렉토리 구조

```
data/
├── db/
│   └── pokergo.db              # 통합 SQLite DB
│
├── sources/                    # 소스별 분리 저장
│   ├── youtube/
│   │   ├── exports/
│   │   │   ├── index.json
│   │   │   ├── channel.json
│   │   │   └── videos/
│   │   │       └── videos_001.json
│   │   └── snapshots/
│   │
│   ├── pokergo_web/
│   │   ├── exports/
│   │   │   ├── index.json
│   │   │   ├── shows.json
│   │   │   └── episodes/
│   │   └── snapshots/
│   │
│   └── archive/
│       ├── exports/
│       │   ├── index.json
│       │   └── files/
│       │       └── files_001.json
│       ├── file_list.txt       # 원본 파일 목록
│       └── parsed/
│           └── metadata.json   # 파싱된 메타데이터
│
└── analysis/                   # 통합 분석 결과
    ├── comparison.json         # 소스 간 비교
    ├── coverage.json           # 커버리지 분석
    └── missing.json            # 누락 콘텐츠
```

### 3.2 데이터베이스 스키마

```sql
-- 통합 DB: 소스별 source 컬럼으로 구분

-- Source enum 확장
-- YOUTUBE, POKERGO_WEB, ARCHIVE

-- 기존 Video 테이블에 source 컬럼 활용
-- 아카이브 전용 필드 추가

CREATE TABLE archive_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id TEXT UNIQUE NOT NULL,
    file_path TEXT NOT NULL,
    file_name TEXT NOT NULL,
    file_size INTEGER,
    file_hash TEXT,                    -- MD5/SHA256 for dedup

    -- 파싱된 메타데이터
    parsed_show TEXT,
    parsed_season INTEGER,
    parsed_episode INTEGER,
    parsed_title TEXT,

    -- 매칭 정보 (다른 소스와 연결)
    matched_youtube_id TEXT,
    matched_pokergo_id TEXT,
    match_confidence REAL,             -- 0.0 ~ 1.0

    -- 상태
    status TEXT DEFAULT 'pending',     -- pending, parsed, matched, verified
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP
);

-- 소스 간 매칭 테이블
CREATE TABLE content_mapping (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    youtube_video_id TEXT,
    pokergo_episode_id TEXT,
    archive_file_id TEXT,
    match_type TEXT,                   -- exact, fuzzy, manual
    confidence REAL,
    verified BOOLEAN DEFAULT FALSE,
    notes TEXT
);
```

---

## 4. 분석 워크플로우

### Phase 1: YouTube 분석 (현재)

```bash
# 1. 전체 크롤링
pokergo crawl youtube --full --playlists

# 2. 내보내기
pokergo export --source youtube

# 3. 통계 확인
pokergo stats --source youtube
```

### Phase 2: Archive 분석 (다음 단계)

```bash
# 1. 파일 목록 가져오기
pokergo archive scan /path/to/archive

# 2. 파일명 파싱 (메타데이터 추출)
pokergo archive parse

# 3. YouTube와 매칭 시도
pokergo archive match --with youtube

# 4. 내보내기
pokergo export --source archive
```

### Phase 3: PokerGO.com 분석 (향후)

```bash
# 1. 웹 크롤링
pokergo crawl web --shows --episodes

# 2. 모든 소스와 매칭
pokergo match all

# 3. 커버리지 분석
pokergo analyze coverage
```

---

## 5. 분석 목표

### 5.1 소스별 분석

| 분석 항목 | YouTube | PokerGO.com | Archive |
|-----------|---------|-------------|---------|
| 총 콘텐츠 수 | ✅ | 🔜 | 🔜 |
| 시리즈/시즌 구조 | ✅ | 🔜 | 🔜 |
| 메타데이터 품질 | ✅ | 🔜 | 🔜 |
| 중복 검출 | ✅ | 🔜 | 🔜 |

### 5.2 소스 간 비교 분석

| 비교 항목 | 설명 |
|-----------|------|
| **커버리지** | 각 소스에 있는/없는 콘텐츠 |
| **중복** | 여러 소스에 존재하는 동일 콘텐츠 |
| **품질** | 화질, 메타데이터 완성도 비교 |
| **누락** | Archive에 있지만 YouTube에 없는 것 등 |

### 5.3 최종 출력

```json
// analysis/comparison.json
{
  "summary": {
    "youtube": {"total": 3000, "unique": 500},
    "pokergo_web": {"total": 5000, "unique": 2500},
    "archive": {"total": 4000, "unique": 1000}
  },
  "overlap": {
    "youtube_pokergo": 2000,
    "youtube_archive": 1500,
    "pokergo_archive": 3000,
    "all_three": 1000
  },
  "missing": {
    "in_archive_not_youtube": ["file1", "file2"],
    "in_youtube_not_archive": ["video1", "video2"]
  }
}
```

---

## 6. CLI 명령어 확장

### 기존 명령어

```bash
pokergo crawl youtube        # YouTube 크롤링
pokergo export               # 내보내기
pokergo stats                # 통계
```

### 새 명령어 (Archive)

```bash
# 아카이브 파일 스캔
pokergo archive scan <path>          # 파일 목록 생성
pokergo archive scan --recursive     # 하위 폴더 포함

# 파일명 파싱
pokergo archive parse                # 메타데이터 추출
pokergo archive parse --pattern "S{season}E{episode}"

# 매칭
pokergo archive match                # 자동 매칭
pokergo archive match --manual       # 수동 매칭 모드

# 조회
pokergo list archive                 # 아카이브 파일 목록
pokergo list archive --unmatched     # 매칭 안 된 파일만
```

### 새 명령어 (분석)

```bash
# 소스 간 비교
pokergo analyze compare              # 전체 비교
pokergo analyze coverage             # 커버리지 분석
pokergo analyze duplicates           # 중복 검출

# 리포트 생성
pokergo report full                  # 전체 리포트
pokergo report missing               # 누락 콘텐츠 리포트
```

---

## 7. 구현 우선순위

| Phase | 작업 | 우선순위 | 상태 |
|-------|------|----------|------|
| 1 | YouTube 크롤링 완성 | P0 | ✅ 완료 |
| 1 | 파일 분할 내보내기 | P0 | ✅ 완료 |
| 2 | Archive 스캔/파싱 | P0 | 🔜 다음 |
| 2 | 파일명 파싱 패턴 | P1 | 🔜 |
| 2 | YouTube-Archive 매칭 | P1 | 🔜 |
| 3 | PokerGO.com 크롤러 | P2 | 향후 |
| 3 | 3-way 매칭 | P2 | 향후 |
| 4 | 분석 리포트 | P2 | 향후 |

---

## 8. 다음 단계

### 즉시 실행 (Archive 분석 준비)

1. **파일 목록 확보**
   - 아카이브 파일 위치 확인
   - 파일 목록 텍스트 파일 생성

2. **파일명 패턴 분석**
   - 샘플 파일명 수집
   - 파싱 패턴 설계

3. **Archive 스캐너 구현**
   - `archive.py` 크롤러 모듈 생성
   - Source.ARCHIVE enum 추가

---

## 변경 이력

| 버전 | 날짜 | 변경 내용 |
|------|------|-----------|
| 1.0.0 | 2025-12-12 | 초기 버전 - 3가지 데이터 소스 분리 구조 설계 |

# PRD: PokerGO 콘텐츠 크롤러

**Version**: 3.0.0
**Date**: 2025-12-12
**Author**: Claude Code
**Status**: ✅ Phase 1 완료

---

## 1. 개요

### 1.1 프로젝트 목표
PokerGO 콘텐츠 메타데이터를 수집하여 로컬 데이터베이스로 관리.
**다운로드는 4K Downloader 등 외부 프로그램 사용.**

### 1.2 데이터 소스

| 소스 | URL | 상태 |
|------|-----|------|
| **YouTube** | youtube.com/@PokerGO | ✅ 크롤러 완료 |
| **PokerGO Web** | pokergo.com | 🔜 향후 추가 |

### 1.3 핵심 기능
- **메타데이터 크롤링**: YouTube 채널에서 영상 정보 수집
- **SQLite 데이터베이스**: 영상 메타데이터 영구 저장
- **URL 내보내기**: 4K Downloader용 URL 목록 생성
- **검색/필터링**: 제목으로 영상 검색

### 1.4 다운로드 방식
YouTube 정책 문제로 **직접 다운로드 기능은 제외**.
대신 URL 목록을 내보내서 **4K Downloader** 등 외부 프로그램 사용.

### 1.5 대상 사용자
- 포커 콘텐츠 아카이브 목적 사용자
- 데이터 분석/연구 목적 사용자

---

## 2. 기술 리서치 결과

### 2.1 PokerGO 기술 스택 분석

| 항목 | 세부 사항 |
|------|-----------|
| **프론트엔드** | Nuxt.js + Tailwind CSS |
| **영상 플레이어** | JWPlayer 기반 |
| **스트리밍 형식** | HLS (M3U8) |
| **스트리밍 서버** | `videos-fms.jwpsrv.com` |
| **인증 방식** | Bearer Token (구독 기반) |
| **API 엔드포인트** | `api.pokergo.com/v2/` |

### 2.2 yt-dlp PokerGO Extractor 분석

yt-dlp에 이미 PokerGO 지원이 구현되어 있음 (PR #2331, 2022년):

```python
# 핵심 API 구조
SIGN_IN_URL = "https://subscription.pokergo.com/properties/{property_id}/sign-in"
API_URL = "https://api.pokergo.com/v2/properties/{property_id}/videos/{video_id}"
PROPERTY_ID = "1dfb3940-7d53-4980-b0b0-f28b369a000d"
```

**인증 플로우**:
1. Basic Auth로 로그인 → Bearer Token 획득
2. API 요청 시 `Authorization: Bearer {token}` 헤더 사용
3. JWPlayer 미디어 ID로 실제 스트림 URL 획득

### 2.3 Make vs Buy 분석

| 접근 방식 | 장점 | 단점 | 권장도 |
|-----------|------|------|--------|
| **yt-dlp 활용** | 안정적, 유지보수됨, 검증됨 | 커스터마이징 제한 | ⭐⭐⭐⭐⭐ |
| **직접 구현** | 완전한 제어, DB 통합 유연 | 개발 시간, 유지보수 부담 | ⭐⭐⭐ |
| **Jaksta (상용)** | GUI 제공 | 비용, API 미지원 | ⭐⭐ |

**결론**: yt-dlp를 핵심 다운로드 엔진으로 사용하고, 메타데이터 관리 레이어를 직접 구현하는 하이브리드 접근 권장.

---

## 3. 시스템 아키텍처

### 3.1 전체 구조 (2단계 설계)

```
┌─────────────────────────────────────────────────────────────────┐
│                    PokerGO Downloader                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                  Phase 1: DB 파싱                        │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │   │
│  │  │   YouTube    │  │   PokerGO    │  │   Database   │   │   │
│  │  │   Crawler    │  │   Crawler    │  │   Manager    │   │   │
│  │  │  (yt-dlp)    │  │  (httpx)     │  │ (SQLAlchemy) │   │   │
│  │  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘   │   │
│  │         │                 │                  │           │   │
│  │         └─────────────────┼──────────────────┘           │   │
│  │                           ▼                              │   │
│  │                    ┌──────────────┐                      │   │
│  │                    │   SQLite     │                      │   │
│  │                    │   Database   │                      │   │
│  │                    └──────────────┘                      │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                  Phase 2: 영상 다운로드                   │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │   │
│  │  │  Download    │  │   yt-dlp     │  │   Progress   │   │   │
│  │  │   Queue      │──│    Core      │──│   Tracker    │   │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘   │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 데이터 소스

| 소스 | URL | 콘텐츠 | 인증 |
|------|-----|--------|------|
| **YouTube** | youtube.com/@PokerGO | 무료 클립, 하이라이트 | 불필요 |
| **PokerGO Web** | pokergo.com | 풀 에피소드, 라이브 | 구독 필요 |

### 3.2 모듈 구성

#### 3.2.1 Crawler Module
- **역할**: PokerGO API에서 콘텐츠 메타데이터 수집
- **기술**: Python + httpx (async HTTP)
- **기능**:
  - 시리즈/쇼 목록 수집
  - 에피소드 정보 수집
  - 증분 업데이트 지원

#### 3.2.2 Database Manager
- **역할**: 메타데이터 영구 저장 및 관리
- **기술**: SQLAlchemy + SQLite (기본) / PostgreSQL (옵션)
- **스키마**:
  ```sql
  -- 시리즈/쇼
  CREATE TABLE shows (
      id TEXT PRIMARY KEY,
      title TEXT NOT NULL,
      description TEXT,
      thumbnail_url TEXT,
      created_at TIMESTAMP,
      updated_at TIMESTAMP
  );

  -- 에피소드
  CREATE TABLE episodes (
      id TEXT PRIMARY KEY,
      show_id TEXT REFERENCES shows(id),
      title TEXT NOT NULL,
      description TEXT,
      duration INTEGER,  -- seconds
      season_number INTEGER,
      episode_number INTEGER,
      air_date DATE,
      thumbnail_url TEXT,
      jwplayer_id TEXT,
      download_status TEXT DEFAULT 'pending',
      file_path TEXT,
      created_at TIMESTAMP,
      updated_at TIMESTAMP
  );

  -- 다운로드 기록
  CREATE TABLE downloads (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      episode_id TEXT REFERENCES episodes(id),
      started_at TIMESTAMP,
      completed_at TIMESTAMP,
      file_size INTEGER,
      quality TEXT,
      status TEXT,
      error_message TEXT
  );
  ```

#### 3.2.3 Downloader Engine
- **역할**: 실제 영상 다운로드 처리
- **기술**: yt-dlp Python API
- **기능**:
  - 품질 선택 (1080p, 720p, 480p)
  - 재개 가능한 다운로드
  - 병렬 다운로드 지원
  - 진행 상황 콜백

---

## 4. 기능 요구사항

### 4.1 인증 (P0 - 필수)
| ID | 기능 | 설명 |
|----|------|------|
| AUTH-01 | 로그인 | PokerGO 계정으로 인증 |
| AUTH-02 | 토큰 관리 | Bearer 토큰 저장/갱신 |
| AUTH-03 | 세션 유지 | 자동 재인증 |

### 4.2 크롤링 (P0 - 필수)
| ID | 기능 | 설명 |
|----|------|------|
| CRAWL-01 | 전체 수집 | 모든 시리즈/에피소드 수집 |
| CRAWL-02 | 증분 수집 | 신규/변경 콘텐츠만 수집 |
| CRAWL-03 | 메타데이터 | 제목, 설명, 썸네일, 시즌/에피소드 번호 |

### 4.3 데이터베이스 (P0 - 필수)
| ID | 기능 | 설명 |
|----|------|------|
| DB-01 | CRUD | 기본 데이터 조작 |
| DB-02 | 검색 | 제목, 시리즈로 검색 |
| DB-03 | 상태 추적 | 다운로드 상태 관리 |

### 4.4 다운로드 (P0 - 필수)
| ID | 기능 | 설명 |
|----|------|------|
| DL-01 | 단일 다운로드 | 개별 에피소드 다운로드 |
| DL-02 | 배치 다운로드 | 시리즈 전체 다운로드 |
| DL-03 | 품질 선택 | 해상도 지정 |
| DL-04 | 재개 | 중단된 다운로드 재개 |

### 4.5 사용자 인터페이스 (P1 - 중요)
| ID | 기능 | 설명 |
|----|------|------|
| UI-01 | CLI | 커맨드라인 인터페이스 |
| UI-02 | TUI | 터미널 UI (Rich/Textual) |
| UI-03 | 진행 상황 | 다운로드 진행률 표시 |

### 4.6 고급 기능 (P2 - 선택)
| ID | 기능 | 설명 |
|----|------|------|
| ADV-01 | 스케줄링 | 자동 크롤링/다운로드 |
| ADV-02 | 알림 | 신규 콘텐츠 알림 |
| ADV-03 | 내보내기 | 메타데이터 JSON/CSV 내보내기 |

---

## 5. 기술 스택

### 5.1 핵심 기술

| 구분 | 기술 | 버전 | 선정 이유 |
|------|------|------|-----------|
| **언어** | Python | 3.12+ | yt-dlp 호환, 빠른 개발 |
| **패키지 관리** | uv | latest | 빠른 의존성 해결 |
| **HTTP 클라이언트** | httpx | 0.27+ | async 지원, 현대적 API |
| **ORM** | SQLAlchemy | 2.0+ | 타입 안전, 다양한 DB 지원 |
| **다운로더** | yt-dlp | latest | PokerGO 공식 지원 |
| **CLI** | typer | 0.12+ | 타입 힌트 기반 CLI |
| **TUI** | rich | 13+ | 진행률, 테이블 표시 |

### 5.2 개발 도구

| 구분 | 기술 |
|------|------|
| **린터** | ruff |
| **타입 체크** | mypy |
| **테스트** | pytest |
| **포매터** | ruff format |

---

## 6. 디렉토리 구조

```
pokergo_crawling/
├── pyproject.toml
├── README.md
├── src/
│   └── pokergo_downloader/
│       ├── __init__.py
│       ├── main.py              # CLI 엔트리포인트
│       ├── config.py            # 설정 관리
│       ├── auth/
│       │   ├── __init__.py
│       │   ├── client.py        # 인증 클라이언트
│       │   └── token.py         # 토큰 관리
│       ├── crawler/
│       │   ├── __init__.py
│       │   ├── api.py           # PokerGO API 클라이언트
│       │   ├── parser.py        # 응답 파싱
│       │   └── scheduler.py     # 크롤링 스케줄러
│       ├── database/
│       │   ├── __init__.py
│       │   ├── models.py        # SQLAlchemy 모델
│       │   ├── repository.py    # 데이터 접근 계층
│       │   └── migrations/      # DB 마이그레이션
│       ├── downloader/
│       │   ├── __init__.py
│       │   ├── engine.py        # yt-dlp 래퍼
│       │   ├── queue.py         # 다운로드 큐
│       │   └── progress.py      # 진행 상황 추적
│       └── ui/
│           ├── __init__.py
│           ├── cli.py           # Typer 커맨드
│           └── tui.py           # Rich TUI
├── tests/
│   ├── test_auth.py
│   ├── test_crawler.py
│   ├── test_database.py
│   └── test_downloader.py
└── data/
    ├── pokergo.db               # SQLite 데이터베이스
    └── downloads/               # 다운로드된 영상
```

---

## 7. API 설계

### 7.1 CLI 커맨드

```bash
# 인증
pokergo auth login --username EMAIL --password PASS
pokergo auth status
pokergo auth logout

# 크롤링
pokergo crawl all                    # 전체 수집
pokergo crawl update                 # 증분 수집
pokergo crawl show "High Stakes"     # 특정 쇼 수집

# 목록 조회
pokergo list shows                   # 모든 쇼 목록
pokergo list episodes --show "WSOP"  # 쇼의 에피소드 목록
pokergo list pending                 # 다운로드 대기 목록

# 다운로드
pokergo download EPISODE_ID          # 단일 다운로드
pokergo download --show "WSOP" --season 2023  # 시즌 전체
pokergo download --all-pending       # 대기 중인 모든 항목
pokergo download --quality 1080p     # 품질 지정

# 설정
pokergo config set download_path /path/to/videos
pokergo config set quality 720p
pokergo config show
```

### 7.2 Python API (프로그래매틱 사용)

```python
from pokergo_downloader import PokerGoClient

async with PokerGoClient() as client:
    # 인증
    await client.login("email@example.com", "password")

    # 크롤링
    shows = await client.get_shows()
    episodes = await client.get_episodes(show_id="xxx")

    # 다운로드
    await client.download(
        episode_id="yyy",
        quality="1080p",
        output_dir="/path/to/downloads"
    )
```

---

## 8. 구현 상태

### ✅ 완료된 기능

- [x] 프로젝트 초기화 (pyproject.toml, setuptools)
- [x] SQLAlchemy 2.0 데이터베이스 모델
  - Channel, Playlist, Video 엔티티
  - Source enum (YOUTUBE, POKERGO_WEB)
- [x] Repository 패턴 구현
- [x] YouTube 크롤러 (yt-dlp 메타데이터 추출)
- [x] CLI 인터페이스 (Typer + Rich)

### CLI 명령어

```bash
# 크롤링
pokergo crawl youtube              # YouTube 채널 전체 크롤링
pokergo crawl youtube -n 100       # 최근 100개만
pokergo crawl youtube --full       # 전체 메타데이터 포함

# 조회
pokergo list videos                # 영상 목록
pokergo list playlists             # 재생목록
pokergo stats                      # 통계
pokergo search "WSOP"              # 제목 검색

# 내보내기 (4K Downloader용)
pokergo export-urls                # URL 목록 생성
pokergo export                     # JSON 메타데이터 내보내기
```

### 🔜 향후 계획 (선택)

- [ ] PokerGO 웹 크롤러 (pokergo.com)
- [ ] 증분 크롤링 (신규 콘텐츠만)
- [ ] 재생목록 영상 연결

### ❌ 제외 (4K Downloader 사용)

- 직접 다운로드 기능
- 다운로드 큐/진행 상황
- 품질 선택

---

## 9. 법적 고려사항

### 9.1 사용 조건
- **개인 사용**: 유료 구독자의 개인 백업 목적만 허용
- **재배포 금지**: 다운로드된 콘텐츠 공유/배포 금지
- **TOS 준수**: PokerGO 서비스 약관 확인 필요

### 9.2 면책 조항
이 도구는 교육 및 개인 백업 목적으로만 제공됩니다. 사용자는 관련 법률 및 서비스 약관을 준수할 책임이 있습니다.

---

## 10. 참고 자료

### 10.1 관련 오픈소스
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) - 영상 다운로드 엔진
- [yt-dlp PokerGO Extractor](https://github.com/yt-dlp/yt-dlp/pull/2331) - 공식 지원 PR
- [m3u8downloader](https://pypi.org/project/m3u8downloader/) - HLS 다운로드 라이브러리

### 10.2 기술 문서
- [JWPlayer Documentation](https://developer.jwplayer.com/)
- [HLS Specification](https://datatracker.ietf.org/doc/html/rfc8216)

---

## 변경 이력

| 버전 | 날짜 | 변경 내용 |
|------|------|-----------|
| 3.0.0 | 2025-12-12 | 다운로드 기능 제외 (4K Downloader 사용), DB 파싱만 집중, URL 내보내기 추가 |
| 2.0.0 | 2025-12-12 | 2단계 설계, YouTube 크롤러 구현 |
| 1.0.0 | 2025-12-12 | 초기 PRD 작성 |

---

## 11. 현재 구현 상태

### 프로젝트 구조

```
pokergo_crawling/
├── pyproject.toml              # 프로젝트 설정
├── PRD-POKERGO-DOWNLOADER.md   # 이 문서
├── src/
│   └── pokergo_downloader/
│       ├── __init__.py
│       ├── main.py             # CLI 엔트리포인트
│       ├── config.py           # 설정 관리
│       ├── database/
│       │   ├── models.py       # SQLAlchemy 모델
│       │   └── repository.py   # Repository 패턴
│       ├── crawler/
│       │   └── youtube.py      # YouTube 크롤러
│       └── downloader/         # Phase 2
├── tests/
└── data/
    └── pokergo.db              # SQLite 데이터베이스
```

### CLI 사용법

```bash
# 의존성 설치
pip install -e .

# YouTube 채널 크롤링
pokergo crawl youtube              # 기본 (빠른 메타데이터)
pokergo crawl youtube --full       # 전체 메타데이터 (느림)
pokergo crawl youtube -n 100       # 최근 100개만

# 데이터 조회
pokergo list videos                # 영상 목록
pokergo list playlists             # 재생목록
pokergo stats                      # 통계

# 데이터 내보내기
pokergo export -o data/videos.json
```

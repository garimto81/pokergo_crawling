# PokerGO Crawler

YouTube PokerGO 채널 메타데이터 크롤러.
**다운로드는 4K Downloader 사용.**

## 설치

```bash
pip install -e .
```

## 사용법

### 1. YouTube 채널 크롤링

```bash
# 전체 채널 크롤링
pokergo crawl youtube

# 최근 100개만
pokergo crawl youtube -n 100

# 전체 메타데이터 포함 (느림)
pokergo crawl youtube --full
```

### 2. 데이터 조회

```bash
# 영상 목록
pokergo list videos

# 통계
pokergo stats

# 검색
pokergo search "WSOP"
```

### 3. URL 내보내기 (4K Downloader용)

```bash
# URL 목록 생성
pokergo export-urls

# 결과: data/youtube_urls.txt
```

### 4. 4K Downloader로 다운로드

1. 4K Downloader 실행
2. '링크 붙여넣기' 클릭
3. `data/youtube_urls.txt` 파일 내용 붙여넣기

## 데이터베이스

- 위치: `data/pokergo.db` (SQLite)
- 테이블: channels, playlists, videos

## 기술 스택

- Python 3.11+
- yt-dlp (메타데이터 추출)
- SQLAlchemy 2.0
- Typer + Rich (CLI)

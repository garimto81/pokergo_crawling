# PRD: PokerGO YouTube 전체 데이터 수집

**Version**: 1.0.0
**Date**: 2025-12-12
**Status**: 실행 대기

---

## 1. 목표

YouTube PokerGO 채널(@PokerGO)의 **모든 영상 메타데이터**를 수집하여 JSON 파일로 저장.

---

## 2. 수집 대상

| 항목 | URL | 예상 규모 |
|------|-----|-----------|
| **채널** | youtube.com/@PokerGO | 1개 |
| **영상** | 전체 업로드 | ~3,000+ 개 |
| **재생목록** | 채널 재생목록 | ~50+ 개 |

---

## 3. 수집 데이터 스키마

### 3.1 영상 (Video)

```json
{
  "video_id": "KQzI62NF7F0",
  "title": "PGT Rags to Riches Recap...",
  "description": "Full description...",
  "source": "youtube",
  "url": "https://www.youtube.com/watch?v=KQzI62NF7F0",
  "duration": 4779,
  "duration_formatted": "1:19:39",
  "upload_date": "2025-12-10",
  "view_count": 12345,
  "like_count": 500,
  "comment_count": 100,
  "thumbnail_url": "https://i.ytimg.com/vi/...",
  "tags": ["poker", "WSOP", "high stakes"],
  "channel_id": "UCOPw3R-TUUNqgN2bQyidW2w",
  "channel_name": "PokerGO"
}
```

### 3.2 채널 (Channel)

```json
{
  "channel_id": "UCOPw3R-TUUNqgN2bQyidW2w",
  "name": "PokerGO",
  "description": "Channel description...",
  "url": "https://www.youtube.com/@PokerGO",
  "subscriber_count": 500000,
  "video_count": 3000,
  "thumbnail_url": "https://..."
}
```

### 3.3 재생목록 (Playlist)

```json
{
  "playlist_id": "PLxxxxx",
  "title": "WSOP 2024",
  "description": "...",
  "video_count": 50,
  "thumbnail_url": "https://..."
}
```

---

## 4. 출력 파일 구조

```
data/
├── pokergo.db                    # SQLite (원본)
├── export/
│   ├── pokergo_youtube_full.json # 전체 데이터 (통합)
│   ├── videos.json               # 영상만
│   ├── playlists.json            # 재생목록만
│   ├── channel.json              # 채널 정보
│   └── youtube_urls.txt          # 4K Downloader용 URL
└── reports/
    └── crawl_report.json         # 크롤링 리포트
```

### 4.1 통합 JSON 형식 (pokergo_youtube_full.json)

```json
{
  "metadata": {
    "crawled_at": "2025-12-12T10:30:00",
    "source": "youtube",
    "channel_url": "https://www.youtube.com/@PokerGO",
    "total_videos": 3000,
    "total_playlists": 50
  },
  "channel": { ... },
  "videos": [ ... ],
  "playlists": [ ... ]
}
```

---

## 5. 실행 계획

### Step 1: 전체 채널 크롤링

```bash
# 전체 영상 + 재생목록 + 전체 메타데이터
pokergo crawl youtube --full --playlists
```

**예상 소요 시간**: 10-30분 (영상 수에 따라)

### Step 2: JSON 내보내기

```bash
# 전체 데이터 JSON 내보내기
pokergo export -o data/export/videos.json
```

### Step 3: URL 목록 생성

```bash
# 4K Downloader용
pokergo export-urls -o data/export/youtube_urls.txt
```

---

## 6. 구현 필요 사항

### 6.1 현재 구현됨 ✅

- [x] YouTube 크롤러 (yt-dlp 기반)
- [x] SQLite 데이터베이스
- [x] 기본 JSON 내보내기
- [x] URL 내보내기

### 6.2 추가 구현 필요 🔜

| 기능 | 설명 | 우선순위 |
|------|------|----------|
| **전체 메타데이터 모드** | view_count, like_count 등 포함 | P0 |
| **통합 JSON 내보내기** | 채널+영상+재생목록 통합 파일 | P0 |
| **크롤링 리포트** | 수집 통계 JSON 생성 | P1 |
| **재생목록 영상 매핑** | 재생목록별 영상 목록 | P2 |

---

## 7. 기술 세부사항

### 7.1 yt-dlp 옵션

```python
# 전체 메타데이터 추출 옵션
ydl_opts = {
    "skip_download": True,        # 다운로드 안 함
    "extract_flat": False,        # 전체 메타데이터
    "ignoreerrors": True,         # 에러 무시
    "quiet": False,
}
```

### 7.2 추출 필드

| 필드 | yt-dlp 키 | 설명 |
|------|-----------|------|
| video_id | `id` | YouTube 영상 ID |
| title | `title` | 제목 |
| description | `description` | 설명 |
| duration | `duration` | 길이 (초) |
| view_count | `view_count` | 조회수 |
| like_count | `like_count` | 좋아요 |
| upload_date | `upload_date` | 업로드 날짜 (YYYYMMDD) |
| thumbnail | `thumbnail` | 썸네일 URL |
| tags | `tags` | 태그 목록 |

---

## 8. 예상 결과

| 항목 | 예상 값 |
|------|---------|
| 총 영상 수 | ~3,000개 |
| 총 재생목록 | ~50개 |
| JSON 파일 크기 | ~10-30MB |
| 크롤링 시간 | ~10-30분 |

---

## 9. 실행 명령어 (최종)

```bash
# 1. 전체 크롤링 (전체 메타데이터 포함)
python -m pokergo_downloader.main crawl youtube --full --playlists

# 2. 통계 확인
python -m pokergo_downloader.main stats

# 3. JSON 내보내기
python -m pokergo_downloader.main export -o data/export/pokergo_videos.json

# 4. URL 목록 (4K Downloader용)
python -m pokergo_downloader.main export-urls -o data/export/youtube_urls.txt
```

---

## 10. 다음 단계

1. **P0**: 전체 크롤링 실행
2. **P1**: JSON 내보내기 기능 개선 (통합 파일)
3. **P2**: 4K Downloader로 필요한 영상 다운로드

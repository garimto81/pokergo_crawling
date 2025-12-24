# YouTube PokerGO 채널 분석 보고서

**분석 일시**: 2025-12-12 14:26 KST
**데이터 소스**: youtube.com/@PokerGO

---

## 1. 수집 통계

| 항목 | 수량 |
|------|------|
| 채널 | 1 |
| 비디오 | 2,132 |
| 플레이리스트 | 97 |
| 총 파일 크기 | ~1.4MB |

---

## 2. 채널 정보

- **채널 ID**: UCOPw3R-TUUNqgN2bQyidW2w
- **채널명**: PokerGO
- **URL**: https://www.youtube.com/channel/UCOPw3R-TUUNqgN2bQyidW2w
- **설명**: "PokerGO is the world's largest poker content company..."

---

## 3. 플레이리스트 분류 (97개)

### 3.1 WSOP Main Event 시리즈 (20개+)

| 년도 | 플레이리스트 ID |
|------|----------------|
| 2003 | PL2bAZuFpadxFlsn_vtQbvSiTZAXc3ExSp |
| 2004 | PL2bAZuFpadxF2EhtA5bUxm07zFF8pKsW2 |
| 2005 | PL2bAZuFpadxE3raBSaF52lq626JG7Kyyf |
| 2006 | PL2bAZuFpadxHlyU897QrOuW7fvK5-R2vk |
| 2007 | PL2bAZuFpadxE0cKSPVtSU7ziblRAWp8O3 |
| 2008 | PL2bAZuFpadxEGOlc6BpAH6c0KT8kNE3eW |
| 2009 | PL2bAZuFpadxFVN5VEiHB1z3G9dWH5OSlC |
| 2010 | PL2bAZuFpadxGNKv9BYGzwt1otgxSrHkjm |
| 2011 | PL2bAZuFpadxE36Bj5dT61sgBD9x5Y8oBP |
| 2012 | PL2bAZuFpadxGBKjnjY7FFKTrYTM57MYyq |
| 2013 | PL2bAZuFpadxEDWHuZYzXjh_GmGspHic0h |
| 2014 | PL2bAZuFpadxH9S1AK7SqKg8Ntg3GZ8Uh_ |
| 2015 | PL2bAZuFpadxG_FyFJO_Z7UYirWjo-QfyO |
| 2016 | PL2bAZuFpadxE_It0EYQrksiNjX32xnaXU |
| 2017 | PL2bAZuFpadxG7McZULuXn4Qk4YKoO0iok |
| 2018 | PL2bAZuFpadxHfwfNDqrx-RVBYYs4-0bDp |
| 2019 | PL2bAZuFpadxHB8YnsxdZv4P_6MT84V6mz |
| 2021 | PL2bAZuFpadxFErstn0OLpWHRot5Q3-UQf |
| 2022 | PL2bAZuFpadxEayQ-gn7mn3m0PwWk5w5cv |

### 3.2 주요 쇼 프로그램

| 프로그램 | 플레이리스트 |
|----------|-------------|
| **High Stakes Poker** | Season 1, Season 2, Top 5 Hands |
| **Poker After Dark** | Season 1, General |
| **No Gamble, No Future** | High Stakes Cash Game |
| **Super High Roller Bowl** | 2022 Europe, General |
| **High Stakes Duel** | General |
| **High Stakes Feud** | General |

### 3.3 토너먼트 시리즈

- **PokerGO Tour (PGT)**: Making or Breaking Millionaires, PLO Series 2023
- **U.S. Poker Open**: 2021, 2022, 2023
- **Poker Masters**: 2021, General, Online PLO Series
- **Super High Roller Series**: 2024, Europe 2022
- **PokerGO Cup**: 2021, 2022
- **Stairway to Millions**
- **PGT Heads-Up Showdown**

### 3.4 특별/컴필레이션

- WSOP Best Hands of All-Time
- Best Poker Hands of All Time!
- Best of Tom Dwan
- Daniel Negreanu Best Poker Hands!
- Best of Mike Matusow
- Best Celebrity Poker Hands

### 3.5 기타 프로그램

- NBC Heads-Up Championship
- Cash Flow
- Venetian Poker Live
- Texas Poker Open
- Face the Ace
- The Big Blind (Poker Game Show)
- PokerGO Podcast
- Poker Central Podcast

---

## 4. 데이터 품질 평가

### 4.1 수집된 메타데이터

| 필드 | 상태 |
|------|------|
| video_id | ✅ 완전 |
| title | ✅ 완전 |
| url | ✅ 완전 |
| duration | ⚠️ 일부 (flat mode) |
| description | ⚠️ 일부 |
| upload_date | ⚠️ 일부 |
| view_count | ❌ 없음 (flat mode) |
| like_count | ❌ 없음 |

### 4.2 제한 사항

- **Flat mode 사용**: Bot detection 회피를 위해 기본 메타데이터만 수집
- **플레이리스트 video_count**: 미수집 (null)
- **구독자 수**: 미수집

---

## 5. 다음 단계 권장

1. **Phase 2: NAS Archive 분석**
   - 보유 파일 목록 파싱
   - show/season/episode 메타데이터 추출

2. **Phase 3: pokergo.com 분석**
   - 웹사이트 구조 분석
   - API 엔드포인트 식별

3. **Phase 4: 3-way 매칭**
   - YouTube ↔ Archive 매칭
   - Archive ↔ pokergo.com 매칭
   - 중복/누락 식별

---

## 6. 파일 위치

```
data/sources/youtube/
├── exports/
│   ├── index.json          # 검색용 인덱스 (video_id → title)
│   ├── channel.json        # 채널 정보
│   ├── videos/
│   │   └── videos_001.json # 비디오 메타데이터 (2,132개)
│   ├── playlists/
│   │   └── playlists.json  # 플레이리스트 (97개)
│   └── urls/
│       └── youtube_urls.txt # 4K Downloader용 URL
└── snapshots/
    └── 2025-12-12_142644/  # 타임스탬프 백업
```

---

**생성**: Claude Code | **Phase**: 1/5 완료

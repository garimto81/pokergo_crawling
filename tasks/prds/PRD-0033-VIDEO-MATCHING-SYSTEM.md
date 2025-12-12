# PRD-0033: YouTube-NAS Video Matching System

**Version**: 1.0
**Date**: 2025-12-12
**Author**: Claude
**Status**: Draft

---

## 1. Executive Summary

YouTube 메타데이터와 NAS 비디오 파일을 매칭하는 시스템을 구축합니다. 두 소스는 완전히 다른 네이밍 컨벤션을 사용하므로, **Multi-Feature Extraction + RapidFuzz** 기반의 스마트 매칭이 필요합니다.

### 1.1 Key Metrics

| 소스 | 데이터 수 | 특징 |
|------|----------|------|
| YouTube | 2,132 videos | 마케팅 스타일 타이틀 |
| NAS | 1,277 files | 구조화된 파일명 (5+ 패턴) |
| 예상 매칭 | ~500-800 pairs | 30-60% 매칭률 |

---

## 2. Data Analysis

### 2.1 YouTube Title Patterns

```
패턴: [Marketing Style] + [Event/Show] + [Player Names] + [Year]

예시:
- "Phil Hellmuth Can't Handle Crazy Trash Talker! [Full Match]"
- "Daniel Negreanu Wins Super High Roller Bowl VII for $3,300,000"
- "Phil Ivey DESTROYS with 2-7 Triple Draw at WSOP 2024"
- "Every Tom Dwan Bluff on High Stakes Poker!"
```

**추출 가능한 피처:**
| Feature | 예시 | 추출률 |
|---------|------|--------|
| Player Names | Hellmuth, Negreanu, Ivey | 85% |
| Event Type | WSOP, High Stakes Poker | 90% |
| Year | 2024, 2025 | 40% |
| Keywords | Bluff, Final Table, Wins | 70% |

### 2.2 NAS Filename Patterns

**Pattern Type 1: Structured (WSOP 2024 Clips)**
```
{order}-wsop-{year}-{type}-ev-{event#}-{description}.mp4

예시:
- 13-wsop-2024-be-ev-26-25k-nlh-hr-day02-Bleznick-99-vs-sternheimer-88-Clean.mp4
- 44-wsop-2024-me-day1c-Hellmuth-gets-j5-bluff-thru-clean.mp4
```

**Pattern Type 2: Episode Style (Archive)**
```
WSOPE{year}_Episode_{num}_H264.mov

예시:
- WSOPE08_Episode_1_H264.mov
- WSOPE09_Episode_10_H264.mov
```

**Pattern Type 3: Short Code**
```
{event_code}{year}-{type}-{num}.mp4

예시:
- WE24-ME-01.mp4 (WSOP Europe 2024 Main Event Episode 1)
```

**Pattern Type 4: Descriptive**
```
#WSOPE {year} {game} {stage} {day} {bracket}.mp4

예시:
- #WSOPE 2024 NLH MAIN EVENT DAY 1B BRACELET EVENT #13.mp4
```

**Pattern Type 5: Archive (Pre-2016)**
```
wsop-{year}-me-{suffix}.mp4 또는 {year} World Series of Poker {num}.mov

예시:
- wsop-1973-me-nobug.mp4
- 1987 World Series of Poker 1.mov
```

### 2.3 Player Name Distribution

| Player | YouTube 언급 | NAS 언급 | 매칭 가능성 |
|--------|-------------|----------|------------|
| Hellmuth | 61 | 4 | High |
| Negreanu | 61 | 8 | High |
| Ivey | 15 | 5 | High |
| Dwan | 15 | 0 | YouTube Only |
| Matusow | 12 | 0 | YouTube Only |
| Deeb | 0 | 4 | NAS Only |
| Bleznick | 0 | 3 | NAS Only |

---

## 3. Matching Strategy

### 3.1 Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    VIDEO MATCHING PIPELINE                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐         ┌──────────────┐                      │
│  │   YouTube    │         │     NAS      │                      │
│  │   Titles     │         │   Filenames  │                      │
│  └──────┬───────┘         └──────┬───────┘                      │
│         │                        │                              │
│         ▼                        ▼                              │
│  ┌──────────────┐         ┌──────────────┐                      │
│  │   Feature    │         │   Feature    │                      │
│  │  Extractor   │         │  Extractor   │                      │
│  │  (YouTube)   │         │   (NAS)      │                      │
│  └──────┬───────┘         └──────┬───────┘                      │
│         │                        │                              │
│         ▼                        ▼                              │
│  ┌─────────────────────────────────────────────┐                │
│  │           Normalized Feature Set            │                │
│  │  {year, event, players, game, keywords}     │                │
│  └─────────────────────┬───────────────────────┘                │
│                        │                                        │
│                        ▼                                        │
│  ┌─────────────────────────────────────────────┐                │
│  │         PHASE 1: Blocking (Pre-filter)      │                │
│  │    - Same year? → candidate group           │                │
│  │    - Same event type? → candidate group     │                │
│  └─────────────────────┬───────────────────────┘                │
│                        │                                        │
│                        ▼                                        │
│  ┌─────────────────────────────────────────────┐                │
│  │         PHASE 2: Scoring (RapidFuzz)        │                │
│  │    - Player name match: +30 points          │                │
│  │    - Event number match: +25 points         │                │
│  │    - Game type match: +15 points            │                │
│  │    - Keyword similarity: +20 points         │                │
│  │    - Title fuzzy match: +10 points          │                │
│  └─────────────────────┬───────────────────────┘                │
│                        │                                        │
│                        ▼                                        │
│  ┌─────────────────────────────────────────────┐                │
│  │         PHASE 3: Validation & Output        │                │
│  │    - Score threshold: >= 60                 │                │
│  │    - Manual review queue: 40-60             │                │
│  │    - No match: < 40                         │                │
│  └─────────────────────────────────────────────┘                │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 Feature Extraction Rules

#### YouTube Title → Features

```python
def extract_youtube_features(title: str) -> dict:
    return {
        "year": extract_year(title),              # regex: 20[0-2][0-9]
        "event": extract_event_type(title),       # WSOP, HSP, PAD, SHRB
        "players": extract_player_names(title),   # from PLAYER_DICT
        "game": extract_game_type(title),         # NLH, PLO, 2-7TD
        "keywords": extract_keywords(title),      # Final Table, Bluff, etc.
        "episode": extract_episode(title),        # Episode N, Part N
        "normalized": normalize_text(title)       # lowercase, no punctuation
    }
```

#### NAS Filename → Features

```python
def extract_nas_features(filename: str, directory: str) -> dict:
    # Pattern detection
    pattern = detect_pattern(filename)  # structured/episode/short/descriptive/archive

    features = {
        "year": None,
        "event": None,
        "players": [],
        "game": None,
        "event_number": None,
        "day": None,
        "stage": None,  # ft (final table), day1, day2, etc.
        "normalized": normalize_text(filename)
    }

    if pattern == "structured":
        # 13-wsop-2024-be-ev-26-25k-nlh-hr-day02-Bleznick...
        match = STRUCTURED_REGEX.match(filename)
        features["year"] = match.group("year")
        features["event_number"] = match.group("event_num")
        features["game"] = match.group("game_type")
        features["players"] = extract_players_from_filename(filename)

    elif pattern == "episode":
        # WSOPE08_Episode_1_H264.mov
        features["year"] = "20" + match.group("year")  # 08 → 2008
        features["episode"] = match.group("episode")

    # ... other patterns

    # Fallback: extract from directory path
    if not features["year"]:
        features["year"] = extract_year_from_path(directory)

    return features
```

### 3.3 Scoring Algorithm

```python
def calculate_match_score(yt_features: dict, nas_features: dict) -> int:
    score = 0
    details = []

    # 1. Year Match (Required for high confidence)
    if yt_features["year"] == nas_features["year"]:
        score += 30
        details.append(f"year_match: +30 ({yt_features['year']})")
    elif yt_features["year"] is None or nas_features["year"] is None:
        score += 5  # Partial credit if unknown

    # 2. Player Name Match (Most reliable signal)
    common_players = set(yt_features["players"]) & set(nas_features["players"])
    if common_players:
        score += min(30, len(common_players) * 15)
        details.append(f"player_match: +{min(30, len(common_players) * 15)} ({common_players})")

    # 3. Event Type Match
    if yt_features["event"] == nas_features["event"]:
        score += 20
        details.append(f"event_match: +20 ({yt_features['event']})")

    # 4. Game Type Match
    if yt_features["game"] and yt_features["game"] == nas_features["game"]:
        score += 10
        details.append(f"game_match: +10 ({yt_features['game']})")

    # 5. Fuzzy Title Similarity (RapidFuzz)
    similarity = fuzz.token_set_ratio(
        yt_features["normalized"],
        nas_features["normalized"]
    )
    fuzzy_score = int(similarity * 0.1)  # Max 10 points
    score += fuzzy_score
    details.append(f"fuzzy_match: +{fuzzy_score} ({similarity}%)")

    return score, details
```

### 3.4 Match Categories

| Score Range | Category | Action |
|-------------|----------|--------|
| >= 80 | **Confident Match** | Auto-link |
| 60-79 | **Likely Match** | Auto-link with flag |
| 40-59 | **Possible Match** | Manual review queue |
| < 40 | **No Match** | Skip |

---

## 4. Data Dictionaries

### 4.1 Player Name Dictionary

```python
PLAYER_ALIASES = {
    # Format: canonical_name: [aliases]
    "phil_hellmuth": ["hellmuth", "phil hellmuth", "poker brat", "philhellmuth"],
    "daniel_negreanu": ["negreanu", "daniel negreanu", "dnegs", "kidpoker"],
    "phil_ivey": ["ivey", "phil ivey", "tiger woods of poker"],
    "tom_dwan": ["dwan", "tom dwan", "durrrr"],
    "patrik_antonius": ["antonius", "patrik antonius"],
    "doug_polk": ["polk", "doug polk"],
    "doyle_brunson": ["brunson", "doyle brunson", "texas dolly"],
    "mike_matusow": ["matusow", "mike matusow", "the mouth"],
    "antonio_esfandiari": ["esfandiari", "antonio esfandiari", "the magician"],
    "shaun_deeb": ["deeb", "shaun deeb"],
    "justin_bonomo": ["bonomo", "justin bonomo"],
    "jeremy_ausmus": ["ausmus", "jeremy ausmus"],
    "landon_tice": ["tice", "landon tice"],
    "eric_persson": ["persson", "eric persson"],
    # ... 50+ more players
}
```

### 4.2 Event Type Dictionary

```python
EVENT_TYPES = {
    "wsop": ["wsop", "world series of poker", "world series", "bracelet event"],
    "hsp": ["high stakes poker", "hsp", "high stakes"],
    "pad": ["poker after dark", "pad"],
    "shrb": ["super high roller bowl", "shrb", "shr bowl"],
    "hsd": ["high stakes duel", "hsd", "heads up duel"],
    "pgt": ["pokergo tour", "pgt"],
    "uspo": ["us poker open", "uspo", "u.s. poker open"],
    "pm": ["poker masters"],
}
```

### 4.3 Game Type Dictionary

```python
GAME_TYPES = {
    "nlh": ["nlh", "no limit hold'em", "no limit holdem", "nlhe", "no-limit"],
    "plo": ["plo", "pot limit omaha", "omaha"],
    "27td": ["2-7 triple draw", "27td", "2-7 td", "triple draw", "27 triple"],
    "stud": ["stud", "7 card stud", "razz"],
    "mixed": ["mixed", "horse", "8-game"],
}
```

---

## 5. Implementation Plan

### Phase 1: Feature Extractors (Day 1)

```
src/matching/
├── __init__.py
├── extractors/
│   ├── __init__.py
│   ├── youtube_extractor.py    # YouTube title → features
│   ├── nas_extractor.py        # NAS filename → features
│   └── dictionaries.py         # Player, Event, Game dictionaries
├── matchers/
│   ├── __init__.py
│   ├── scorer.py               # Match scoring algorithm
│   └── blocker.py              # Pre-filtering (blocking)
└── pipeline.py                 # Main matching pipeline
```

### Phase 2: Matching Engine (Day 2)

- RapidFuzz 기반 퍼지 매칭
- Blocking으로 후보군 축소 (O(n²) → O(n×k))
- 배치 처리 및 캐싱

### Phase 3: Results & Viewer (Day 3)

- 매칭 결과 JSON 생성
- 매칭 결과 뷰어 HTML
- Manual review 인터페이스

---

## 6. Expected Results

### 6.1 Match Distribution (Estimated)

```
Total YouTube: 2,132
Total NAS: 1,277

Expected Results:
├── Confident Match (>=80): ~200 pairs (15%)
├── Likely Match (60-79): ~300 pairs (25%)
├── Possible Match (40-59): ~200 pairs (15%)
├── No Match (YouTube only): ~1,432 videos
└── No Match (NAS only): ~577 files
```

### 6.2 Sample Matches

| YouTube Title | NAS Filename | Score |
|--------------|--------------|-------|
| "Phil Ivey DESTROYS at WSOP 2024 2-7 Triple Draw" | `16-wsop-2024-be-ev-29-2-7TD-Ivey-Vs-Wong...` | 85 |
| "Negreanu Hits Straight Flush at WSOP 2024" | `33-wsop-2024-be-ev-58-50k-ppc-day4-negreanu-hits-straight-fl...` | 90 |
| "Hellmuth Gets Bluff Through at 2024 WSOP Main Event" | `44-wsop-2024-me-day1c-Hellmuth-gets-j5-bluff-thru-clean.mp4` | 88 |

---

## 7. Technical Requirements

### 7.1 Dependencies

```
rapidfuzz>=3.0.0
python-Levenshtein>=0.12.0  # Optional, for speed
```

### 7.2 Performance Targets

| Metric | Target |
|--------|--------|
| Full matching time | < 30 seconds |
| Memory usage | < 500MB |
| Accuracy (confident) | > 95% |
| Manual review rate | < 20% |

---

## 8. Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|-----------|
| NAS 파일명 패턴 불일치 | 낮은 매칭률 | 패턴별 추출기 개발 |
| 동일 콘텐츠, 다른 편집본 | 중복 매칭 | 최고 점수만 채택 |
| 선수명 철자 변형 | 누락 | 별칭 사전 확장 |
| 연도 정보 없음 | 낮은 신뢰도 | 디렉토리 경로에서 추출 |

---

## 9. Success Criteria

- [ ] 500+ confident matches (score >= 80)
- [ ] 95%+ accuracy on confident matches (manual verification)
- [ ] Manual review queue < 300 pairs
- [ ] Full pipeline execution < 1 minute

---

## 10. Next Steps

1. **즉시**: Feature extractor 구현
2. **Day 2**: Matching engine 구현 및 테스트
3. **Day 3**: Results viewer 구현
4. **Day 4**: Manual review 및 사전 확장

# PRD-0035: Matching Result Viewer UI

**Version**: 1.0
**Date**: 2025-12-12
**Author**: Claude
**Status**: Draft
**Depends on**: PRD-0033 (Video Matching System), PRD-0034 (Matching Review UI)

---

## 1. Executive Summary

NAS Full Episode → YouTube 매칭 결과(742개)를 확인하고 관리하는 웹 UI입니다.
**핵심 목표**: 미업로드 콘텐츠(75개)를 식별하고, 매칭 결과를 검증하며, 수동 매칭을 지원합니다.

### 1.1 현재 매칭 결과

| 상태 | 개수 | 비율 | 설명 |
|------|------|------|------|
| **MATCHED** | 96 | 12.9% | 확실한 매칭 (score ≥ 80) |
| **LIKELY** | 532 | 71.7% | 유력 매칭 (60-79) |
| **POSSIBLE** | 39 | 5.3% | 검토 필요 (40-59) |
| **NOT_UPLOADED** | 75 | 10.1% | 미업로드 추정 (< 40) |

### 1.2 주요 기능

1. **대시보드**: 매칭 현황 통계
2. **매칭 비교 뷰**: YouTube ↔ NAS 직관적 Side-by-Side 비교
3. **매칭 목록**: 상태별 필터링 및 검색
4. **미업로드 관리**: 콘텐츠 업로드 계획 수립
5. **수동 매칭**: 자동 매칭 실패 시 수동 연결
6. **내보내기**: 보고서 생성

---

## 2. System Architecture

```mermaid
flowchart TB
    subgraph Client["Frontend (React + Vite)"]
        UI[Matching Viewer UI]
        Store[Zustand Store]
        Router[React Router]
    end

    subgraph Server["Backend (FastAPI)"]
        API[REST API]
        MatchService[Match Service]
        SearchService[Search Service]
    end

    subgraph Data["Data Layer"]
        SQLite[(content_mapping)]
        NAS_JSON[(nas_files.json)]
        YT_JSON[(videos.json)]
    end

    UI --> Store
    Store --> API
    API --> MatchService
    API --> SearchService
    MatchService --> SQLite
    SearchService --> NAS_JSON
    SearchService --> YT_JSON
```

---

## 3. Data Model

### 3.1 content_mapping 테이블 (기존)

```mermaid
erDiagram
    CONTENT_MAPPING {
        int id PK
        string nas_filename
        string nas_directory
        int nas_size_bytes
        string youtube_video_id
        string youtube_title
        int match_score
        string match_status "MATCHED|LIKELY|POSSIBLE|NOT_UPLOADED"
        json match_details
        datetime created_at
        datetime updated_at
    }

    YOUTUBE_VIDEO {
        string video_id PK
        string title
        int duration
        string thumbnail_url
    }

    NAS_FILE {
        string filename
        string directory
        int size_bytes
    }

    CONTENT_MAPPING }o--|| YOUTUBE_VIDEO : "matched_to"
    CONTENT_MAPPING ||--|| NAS_FILE : "source"
```

### 3.2 Match Status Flow

```mermaid
stateDiagram-v2
    [*] --> AUTO_MATCHED: score >= 80

    AUTO_MATCHED --> VERIFIED: 사용자 확인
    AUTO_MATCHED --> WRONG_MATCH: 오매칭 신고

    [*] --> LIKELY: score 60-79
    LIKELY --> VERIFIED: 사용자 확인
    LIKELY --> WRONG_MATCH: 오매칭 신고
    LIKELY --> MANUAL_MATCH: 수동 재매칭

    [*] --> POSSIBLE: score 40-59
    POSSIBLE --> VERIFIED: 사용자 확인
    POSSIBLE --> NOT_UPLOADED: 미업로드 확정
    POSSIBLE --> MANUAL_MATCH: 수동 재매칭

    [*] --> NOT_UPLOADED: score < 40
    NOT_UPLOADED --> MANUAL_MATCH: YouTube에서 발견
    NOT_UPLOADED --> UPLOAD_PLANNED: 업로드 예정
    NOT_UPLOADED --> EXCLUDED: 업로드 제외

    WRONG_MATCH --> MANUAL_MATCH: 재매칭

    VERIFIED --> [*]
    MANUAL_MATCH --> VERIFIED
    UPLOAD_PLANNED --> [*]
    EXCLUDED --> [*]
```

---

## 4. 매칭 비교 핵심 UI (Side-by-Side Comparison)

YouTube와 NAS 파일 간의 매칭을 **직관적으로 비교**하는 것이 이 시스템의 핵심입니다.

### 4.1 비교 UI 컨셉

```mermaid
flowchart LR
    subgraph Left["📁 NAS File (Source)"]
        NAS_Info["파일명, 경로, 크기\n추출된 특징\n(Year, Event, Day)"]
    end

    subgraph Center["🔗 Match Score"]
        Score["85점\n────\n매칭 상세"]
        Slider["◀━━━●━━━▶\n비교 슬라이더"]
    end

    subgraph Right["🎬 YouTube (Target)"]
        YT_Info["제목, 썸네일\n조회수, 길이\n업로드 날짜"]
    end

    Left <--> Center <--> Right
```

### 4.2 Split View 비교 레이아웃

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  Match Comparison View                                    Score: 85/100 🟢    │
├────────────────────────────────┬─────────────────────────────────────────────┤
│                                │                                             │
│  📁 NAS FILE                   │  🎬 YOUTUBE VIDEO                           │
│  ════════════════════════════  │  ════════════════════════════════════════   │
│                                │                                             │
│  wsop-2024-me-day4-ft.mp4     │  ┌─────────────────────────────────────┐    │
│                                │  │    [YouTube Thumbnail Preview]     │    │
│  📂 Path:                      │  │                                     │    │
│  ARCHIVE/WSOP/2024/Main Event/ │  │         ▶ 2:34:15                   │    │
│                                │  └─────────────────────────────────────┘    │
│  📊 Extracted Features:        │                                             │
│  ┌──────────────────────────┐  │  Title:                                     │
│  │ Year:    2024       ✅   │  │  2024 WSOP Main Event Day 4 - Final Table  │
│  │ Event:   WSOP       ✅   │  │                                             │
│  │ Day:     4          ✅   │  │  👁 125,432 views                           │
│  │ Type:    Main Event ✅   │  │  📅 Uploaded: 2024-07-20                    │
│  │ Episode: -          ⬜   │  │  ⏱ Duration: 2:34:15                        │
│  └──────────────────────────┘  │                                             │
│                                │  📊 Extracted Features:                     │
│  💾 Size: 2.4 GB               │  ┌───────────────────────────────────────┐  │
│  🎞 Format: MP4                │  │ Year:    2024       ✅ MATCH          │  │
│                                │  │ Event:   WSOP       ✅ MATCH          │  │
│                                │  │ Day:     4          ✅ MATCH          │  │
│                                │  │ Type:    Main Event ✅ MATCH          │  │
│                                │  │ Episode: -          ⬜ N/A            │  │
│                                │  └───────────────────────────────────────┘  │
│                                │                                             │
├────────────────────────────────┴─────────────────────────────────────────────┤
│                                                                              │
│  🔍 MATCH SCORE BREAKDOWN                                                    │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │
│                                                                              │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐            │
│  │ Year Match  │ │ Event Match │ │ Day Match   │ │ SBERT Score │            │
│  │    +30      │ │    +25      │ │    +15      │ │    +15      │            │
│  │  ███████████│ │  ███████████│ │  ███████████│ │  ██████████ │            │
│  │   (2024)    │ │   (WSOP)    │ │   (Day 4)   │ │  (sim:0.82) │            │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘            │
│                                                                              │
│                          Total Score: 85/100                                 │
│                                                                              │
├──────────────────────────────────────────────────────────────────────────────┤
│  [✓ Confirm Match]  [✗ Wrong Match]  [🔗 Re-match]  [▶ Watch on YouTube]    │
└──────────────────────────────────────────────────────────────────────────────┘
```

### 4.3 Feature Matching Visualization

```mermaid
flowchart LR
    subgraph NAS["NAS Features"]
        N_Year["Year: 2024"]
        N_Event["Event: WSOP"]
        N_Day["Day: 4"]
        N_Type["Type: Main Event"]
    end

    subgraph Match["Match Result"]
        M_Year["✅ +30"]
        M_Event["✅ +25"]
        M_Day["✅ +15"]
        M_SBERT["~ +15"]
    end

    subgraph YouTube["YouTube Features"]
        Y_Year["Year: 2024"]
        Y_Event["Event: WSOP"]
        Y_Day["Day: 4"]
        Y_Type["Type: Main Event"]
    end

    N_Year --> M_Year --> Y_Year
    N_Event --> M_Event --> Y_Event
    N_Day --> M_Day --> Y_Day
    N_Type --> M_SBERT --> Y_Type
```

### 4.4 비교 슬라이더 (Before/After Style)

이미지 비교 슬라이더 방식을 응용하여 NAS와 YouTube 정보를 동적으로 비교합니다.

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  ◀────────────────────●──────────────────────▶                       │
│                       ↑                                              │
│                   Drag to Compare                                    │
│                                                                      │
│  ┌──────────────────────┬───────────────────────────────────────┐   │
│  │                      │                                       │   │
│  │  📁 NAS              │  🎬 YouTube                           │   │
│  │                      │                                       │   │
│  │  wsop-2024-me-       │  2024 WSOP Main Event                 │   │
│  │  day4-ft.mp4         │  Day 4 - Final Table                  │   │
│  │                      │                                       │   │
│  │  Year: 2024          │  Year: 2024                           │   │
│  │  Event: WSOP     ◀───┼───▶ Event: WSOP                       │   │
│  │  Day: 4              │  Day: 4                               │   │
│  │                      │                                       │   │
│  └──────────────────────┴───────────────────────────────────────┘   │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### 4.5 Heat Map 스타일 매칭 점수

```
┌─────────────────────────────────────────────────────────────────────┐
│  Match Confidence Heat Map                                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Feature        NAS Value        YouTube Value     Score            │
│  ─────────────────────────────────────────────────────────────      │
│  Year           2024             2024              ████████████ 30  │
│  Event          WSOP             WSOP              ██████████   25  │
│  Day            4                4                 ██████       15  │
│  Episode        -                -                 ░░░░░░        0  │
│  Semantic       -                -                 ██████       15  │
│  ─────────────────────────────────────────────────────────────      │
│  TOTAL                                             ████████████ 85  │
│                                                                     │
│  🟢 MATCHED (High Confidence)                                       │
└─────────────────────────────────────────────────────────────────────┘
```

### 4.6 Butterfly Chart (좌우 대칭 비교)

```mermaid
---
config:
  xyChart:
    width: 600
    height: 300
---
xychart-beta
    title "Feature Match Comparison"
    x-axis ["Year", "Event", "Day", "Episode", "Semantic"]
    y-axis "Score" 0 --> 35
    bar [30, 25, 15, 0, 15]
```

### 4.7 Quick Compare Cards (리스트 뷰)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Quick Compare: 742 Matches                      [Grid View] [List View]    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │ 🟢 85   📁 wsop-2024-me-day4.mp4  ━━━━━━━━▶  🎬 2024 WSOP ME Day 4   │  │
│  │         Year ✅ Event ✅ Day ✅ Semantic ✅                            │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │ 🟡 68   📁 WSOPE08_Ep3.mov        ━━━━━━━━▶  🎬 WSOP Europe 2008 Ep3 │  │
│  │         Year ✅ Event ✅ Episode ✅ Semantic ⚠️                        │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │ 🔴 12   📁 2025-wsope-plo.mp4     ━━━ ✗ ━━▶  🎬 (No Match Found)     │  │
│  │         Year ❌ Event ⚠️ Day ❌ Semantic ❌                            │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 4.8 추천 React 컴포넌트

| 용도 | 컴포넌트 | 설명 |
|------|----------|------|
| Split View | `react-split-pane` | 드래그로 크기 조절 가능한 2분할 |
| Before/After Slider | `react-comparison-slider` | 키보드 접근 가능한 비교 슬라이더 |
| Diff View | `react-diff-viewer` | GitHub 스타일 차이 비교 |
| Heat Map | `recharts` HeatMapGrid | 점수 시각화 |
| 애니메이션 | `framer-motion` | 부드러운 전환 효과 |

---

## 5. Screen Design

### 5.1 전체 화면 구조

```mermaid
flowchart TB
    subgraph App["Application"]
        subgraph Nav["Navigation"]
            Dashboard[Dashboard]
            AllMatches[All Matches]
            NotUploaded[Not Uploaded]
            ManualMatch[Manual Match]
        end

        subgraph Content["Content Area"]
            DashPage[Dashboard Page]
            ListPage[Match List Page]
            NotUpPage[Not Uploaded Page]
            ManualPage[Manual Match Page]
        end
    end

    Dashboard --> DashPage
    AllMatches --> ListPage
    NotUploaded --> NotUpPage
    ManualMatch --> ManualPage
```

### 4.2 Dashboard 레이아웃

```mermaid
block-beta
    columns 4

    block:header:4
        Logo["PokerGO Content Matcher"]
        Space:2
        Export["Export Report"]
    end

    block:stats:4
        Total["Total NAS Files\n742"]
        Matched["Matched\n628 (84.6%)"]
        Possible["Need Review\n39 (5.3%)"]
        NotUp["Not Uploaded\n75 (10.1%)"]
    end

    block:chart1:2
        StatusPie["Status Distribution\n(Pie Chart)"]
    end

    block:chart2:2
        ScoreHist["Score Distribution\n(Histogram)"]
    end

    block:notup:4
        NotUpList["Not Uploaded by Category\n────────────────────────────\nWSOP Europe 2008-2012: 28\nWSOP Europe 2021-2025: 29\nWSOP Paradise: 13\nMPP Cyprus: 3\nOther: 2"]
    end

    block:actions:4
        ViewAll["View All Matches →"]
        ViewNotUp["Manage Not Uploaded →"]
        ViewManual["Manual Matching →"]
        Settings["Settings"]
    end
```

### 4.3 Match List View

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  PokerGO Content Matcher                    [Dashboard] [Matches] [Not Up]  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  [🔍 Search NAS filename or YouTube title...]                               │
│                                                                             │
│  Status: [All ▼]  Score: [0-100 ▼]  Year: [All ▼]  Event: [All ▼]          │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ 🟢 MATCHED [85]                                                      │   │
│  │                                                                       │   │
│  │ NAS:  wsop-2024-me-day4-final-table.mp4                              │   │
│  │       📁 ARCHIVE/WSOP/2024 WSOP/Main Event/                          │   │
│  │                                                                       │   │
│  │ YouTube: 2024 WSOP Main Event Day 4 - Final Table                    │   │
│  │          🎬 2:34:15 | 👁 125,432 views                                │   │
│  │                                                                       │   │
│  │ Match: year +30 | event +25 | day +15 | sbert +15                    │   │
│  │                                                                       │   │
│  │                              [✓ Verify] [✗ Wrong] [📄 Details]       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ 🟡 LIKELY [68]                                                       │   │
│  │                                                                       │   │
│  │ NAS:  WSOPE08_Episode_3_H264.mov                                     │   │
│  │       📁 ARCHIVE/WSOP Europe/2008/                                   │   │
│  │                                                                       │   │
│  │ YouTube: WSOP Europe 2008 - Episode 3 | Main Event Day 2             │   │
│  │          🎬 45:20 | 👁 45,231 views                                   │   │
│  │                                                                       │   │
│  │ Match: year +30 | event +25 | episode +10 | sbert +3                 │   │
│  │                                                                       │   │
│  │                              [✓ Verify] [✗ Wrong] [📄 Details]       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ 🔴 NOT_UPLOADED [12]                                                 │   │
│  │                                                                       │   │
│  │ NAS:  2025 WSOPE #10 10,000 Pot-Limit Omaha Mystery Bounty.mp4      │   │
│  │       📁 ARCHIVE/WSOP Europe/2025/                                   │   │
│  │                                                                       │   │
│  │ Best Match: WSOP Europe 2024 - PLO High Roller (score: 38)           │   │
│  │                                                                       │   │
│  │                              [🔗 Find Match] [📅 Plan Upload]        │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  [← Prev]  Page 1 of 75  [Next →]                    Showing 1-10 of 742   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 4.4 Not Uploaded Management

```mermaid
block-beta
    columns 3

    block:header:3
        Title["Not Uploaded Content (75 files)"]
        Filter["Filter by Event ▼"]
        BulkAction["Bulk Actions ▼"]
    end

    block:category1:1
        Cat1["WSOP Europe\n2008-2012\n────────\n28 files\n\n☐ Episode 1\n☐ Episode 2\n☐ Episode 3\n..."]
    end

    block:category2:1
        Cat2["WSOP Europe\n2021-2025\n────────\n29 files\n\n☐ 2021 ME FT\n☐ 2024 Day 1B\n☐ 2025 PLO\n..."]
    end

    block:category3:1
        Cat3["WSOP Paradise\n2023-2024\n────────\n13 files\n\n☐ ME Day 1A\n☐ ME Day 1B\n☐ Cash Game\n..."]
    end

    block:actions:3
        ActionBar["Selected: 0 | [📅 Schedule Upload] [🚫 Exclude] [🔗 Manual Match]"]
    end
```

### 4.5 Manual Match Modal

```
┌───────────────────────────────────────────────────────────────────────┐
│  Manual Match                                                    [X]  │
├───────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  NAS File:                                                            │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │ 📁 WSOPE08_Episode_1_H264.mov                                   │  │
│  │    ARCHIVE/WSOP Europe/2008/                                    │  │
│  │    Size: 1.2 GB                                                 │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                                                                       │
│  Search YouTube:                                                      │
│  [🔍 wsop europe 2008 episode 1...........................]           │
│                                                                       │
│  Search Results:                                                      │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │ ○ WSOP Europe 2008 - Episode 1 | Opening Day                   │  │
│  │   🎬 52:30 | 👁 23,456 views | Similarity: 72%                  │  │
│  ├─────────────────────────────────────────────────────────────────┤  │
│  │ ○ WSOP Europe 2008 Main Event Highlights                       │  │
│  │   🎬 15:20 | 👁 89,123 views | Similarity: 45%                  │  │
│  ├─────────────────────────────────────────────────────────────────┤  │
│  │ ○ Best of WSOP Europe 2008                                     │  │
│  │   🎬 28:45 | 👁 156,789 views | Similarity: 38%                 │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                                                                       │
│  ○ Mark as "Not on YouTube" (confirm not uploaded)                   │
│                                                                       │
│                              [Cancel]  [Confirm Match]                │
└───────────────────────────────────────────────────────────────────────┘
```

### 4.6 Match Detail View

```mermaid
block-beta
    columns 2

    block:header:2
        Back["← Back to List"]
        Actions["[✓ Verify] [✗ Wrong] [🔗 Re-match]"]
    end

    block:nas:1
        NASCard["📁 NAS File\n──────────────────\nFilename:\nwsop-2024-me-day4.mp4\n\nDirectory:\nARCHIVE/WSOP/2024/ME/\n\nSize: 2.4 GB\n\nExtracted Features:\n• Year: 2024\n• Event: WSOP\n• Day: 4\n• Type: Main Event"]
    end

    block:youtube:1
        YTCard["🎬 YouTube Match\n──────────────────\nTitle:\n2024 WSOP Main Event\nDay 4 - Final Table\n\nDuration: 2:34:15\nViews: 125,432\nUpload: 2024-07-20\n\n[▶ Watch on YouTube]\n[📋 Copy Video ID]"]
    end

    block:score:2
        ScoreCard["Match Score: 85/100\n─────────────────────────────────────────────────\n✓ Year Match      +30  (2024 = 2024)\n✓ Event Match     +25  (WSOP = WSOP)\n✓ Day Match       +15  (Day 4 = Day 4)\n○ Episode Match   +0   (not detected)\n~ SBERT Semantic  +15  (similarity: 0.82)"]
    end

    block:history:2
        History["Review History\n──────────────────────────────────────────────────\n2025-12-12 14:30  Created (auto-matched)\n2025-12-12 15:45  Verified by user"]
    end
```

---

## 5. User Flows

### 5.1 Dashboard Overview Flow

```mermaid
sequenceDiagram
    actor User
    participant Dash as Dashboard
    participant API as Backend API
    participant DB as SQLite

    User->>Dash: Open Dashboard
    Dash->>API: GET /api/stats/summary
    API->>DB: SELECT COUNT(*) GROUP BY status
    DB-->>API: Status counts
    API-->>Dash: {matched: 628, not_uploaded: 75, ...}

    Dash->>API: GET /api/stats/not-uploaded-categories
    API->>DB: SELECT directory, COUNT(*)
    DB-->>API: Category breakdown
    API-->>Dash: {wsope_2008: 28, wsope_2021: 29, ...}

    Dash->>User: Render dashboard with charts
```

### 5.2 Verify Match Flow

```mermaid
sequenceDiagram
    actor User
    participant List as Match List
    participant API as Backend API
    participant DB as SQLite

    User->>List: Click [✓ Verify] on match
    List->>API: PATCH /api/matches/123 {status: VERIFIED}
    API->>DB: UPDATE content_mapping SET match_status = 'VERIFIED'
    DB-->>API: Success
    API-->>List: Updated match
    List->>User: Show success toast, update UI
```

### 5.3 Manual Match Flow

```mermaid
sequenceDiagram
    actor User
    participant List as Match List
    participant Modal as Manual Match Modal
    participant API as Backend API
    participant DB as SQLite

    User->>List: Click [🔗 Find Match] on NOT_UPLOADED item
    List->>Modal: Open manual match modal

    User->>Modal: Type search query
    Modal->>API: GET /api/youtube/search?q=wsop europe 2008
    API-->>Modal: YouTube search results

    User->>Modal: Select matching video
    User->>Modal: Click [Confirm Match]

    Modal->>API: PATCH /api/matches/123 {youtube_id: "abc", status: MANUAL_MATCH}
    API->>DB: UPDATE content_mapping
    DB-->>API: Success
    API-->>Modal: Updated match
    Modal->>List: Close modal, refresh list
```

### 5.4 Bulk Action Flow

```mermaid
sequenceDiagram
    actor User
    participant NotUp as Not Uploaded Page
    participant Modal as Confirm Modal
    participant API as Backend API

    User->>NotUp: Select multiple items (checkbox)
    User->>NotUp: Click [📅 Schedule Upload]

    NotUp->>Modal: Show confirmation (15 items)
    User->>Modal: Add notes, confirm

    Modal->>API: POST /api/matches/bulk-update
    Note right of API: {ids: [1,2,3...], status: UPLOAD_PLANNED, notes: "Q1 2025"}
    API-->>Modal: Success (15 updated)
    Modal-->>NotUp: Refresh list
```

---

## 6. Component Hierarchy

```mermaid
flowchart TB
    App[App]

    App --> Layout[Layout]
    Layout --> Navbar[Navbar]
    Layout --> MainContent[Main Content]

    MainContent --> DashboardPage[DashboardPage]
    MainContent --> MatchListPage[MatchListPage]
    MainContent --> NotUploadedPage[NotUploadedPage]
    MainContent --> ManualMatchPage[ManualMatchPage]

    DashboardPage --> StatsCards[StatsCards]
    DashboardPage --> StatusPieChart[StatusPieChart]
    DashboardPage --> ScoreHistogram[ScoreHistogram]
    DashboardPage --> CategoryBreakdown[CategoryBreakdown]

    MatchListPage --> SearchBar[SearchBar]
    MatchListPage --> FilterBar[FilterBar]
    MatchListPage --> MatchCardList[MatchCardList]
    MatchListPage --> Pagination[Pagination]

    MatchCardList --> MatchCard[MatchCard]
    MatchCard --> StatusBadge[StatusBadge]
    MatchCard --> ScoreIndicator[ScoreIndicator]
    MatchCard --> MatchActions[MatchActions]

    NotUploadedPage --> CategoryFilter[CategoryFilter]
    NotUploadedPage --> SelectableList[SelectableList]
    NotUploadedPage --> BulkActionBar[BulkActionBar]

    ManualMatchPage --> NASFileCard[NASFileCard]
    ManualMatchPage --> YouTubeSearch[YouTubeSearch]
    ManualMatchPage --> SearchResults[SearchResults]
```

---

## 7. API Endpoints

### 7.1 API Overview

```mermaid
flowchart LR
    subgraph Stats["/api/stats"]
        GET_Summary["GET /summary"]
        GET_Categories["GET /not-uploaded-categories"]
        GET_ScoreDist["GET /score-distribution"]
    end

    subgraph Matches["/api/matches"]
        GET_List["GET /"]
        GET_Detail["GET /{id}"]
        PATCH_Update["PATCH /{id}"]
        POST_Bulk["POST /bulk-update"]
    end

    subgraph YouTube["/api/youtube"]
        GET_Search["GET /search"]
        GET_Video["GET /video/{id}"]
    end

    subgraph Export["/api/export"]
        GET_Report["GET /report"]
        GET_NotUploaded["GET /not-uploaded"]
    end
```

### 7.2 API Specifications

| Endpoint | Method | Description | Parameters |
|----------|--------|-------------|------------|
| `/api/stats/summary` | GET | 대시보드 통계 | - |
| `/api/stats/not-uploaded-categories` | GET | 미업로드 카테고리별 집계 | - |
| `/api/stats/score-distribution` | GET | 점수 분포 히스토그램 | `bins=10` |
| `/api/matches` | GET | 매칭 목록 | `status`, `score_min`, `score_max`, `year`, `event`, `page`, `limit` |
| `/api/matches/{id}` | GET | 매칭 상세 | - |
| `/api/matches/{id}` | PATCH | 매칭 업데이트 | `status`, `youtube_id`, `notes` |
| `/api/matches/bulk-update` | POST | 일괄 업데이트 | `ids[]`, `status`, `notes` |
| `/api/youtube/search` | GET | YouTube 검색 | `q`, `limit=10` |
| `/api/export/report` | GET | 전체 보고서 | `format=json|csv` |
| `/api/export/not-uploaded` | GET | 미업로드 목록 | `format=json|csv` |

### 7.3 Response Examples

```json
// GET /api/stats/summary
{
  "total": 742,
  "by_status": {
    "MATCHED": 96,
    "LIKELY": 532,
    "POSSIBLE": 39,
    "NOT_UPLOADED": 75
  },
  "match_rate": 84.6,
  "avg_score": 64.8
}

// GET /api/matches?status=NOT_UPLOADED&page=1&limit=10
{
  "items": [
    {
      "id": 1,
      "nas_filename": "WSOPE08_Episode_1_H264.mov",
      "nas_directory": "ARCHIVE/WSOP Europe/2008/",
      "youtube_title": null,
      "youtube_video_id": null,
      "match_score": 10,
      "match_status": "NOT_UPLOADED",
      "best_match": {
        "title": "WSOP Europe 2009 Episode 1",
        "score": 38
      }
    }
  ],
  "total": 75,
  "page": 1,
  "pages": 8
}
```

---

## 8. Filter & Search

### 8.1 Filter Options

```mermaid
flowchart TB
    subgraph Filters["Filter Panel"]
        Status["Status\n────────\n☐ MATCHED\n☐ LIKELY\n☐ POSSIBLE\n☐ NOT_UPLOADED\n☐ VERIFIED\n☐ MANUAL_MATCH"]

        Score["Score Range\n────────\n[0] ━━━━━●━━ [100]\n     Min: 40"]

        Year["Year\n────────\n☐ 2025\n☐ 2024\n☐ 2023\n☐ 2022\n☐ Earlier"]

        Event["Event Type\n────────\n☐ WSOP\n☐ WSOP Europe\n☐ WSOP Paradise\n☐ MPP\n☐ Other"]
    end
```

### 8.2 Search Behavior

```mermaid
flowchart LR
    Input["Search Input\n'wsop 2024 main'"]
    --> Debounce["Debounce\n300ms"]
    --> Query["Build Query"]

    Query --> NAS["Search NAS\nfilename, directory"]
    Query --> YT["Search YouTube\ntitle"]

    NAS --> Merge["Merge &\nRank Results"]
    YT --> Merge

    Merge --> Display["Display\nMatched Items"]
```

---

## 9. Tech Stack

| Layer | Technology | Rationale |
|-------|------------|-----------|
| Frontend | React 18 + TypeScript | 컴포넌트 기반, 타입 안전성 |
| Build Tool | Vite | 빠른 개발 서버 |
| UI Components | shadcn/ui + Tailwind | 일관된 디자인, 커스터마이징 용이 |
| Charts | Recharts | React 친화적, 가벼움 |
| State | Zustand | 심플한 상태 관리 |
| HTTP Client | TanStack Query | 캐싱, 자동 리페치 |
| Backend | FastAPI | 빠른 API 개발, OpenAPI 문서화 |
| Database | SQLite | 기존 content_mapping 테이블 활용 |

---

## 10. Directory Structure

```
pokergo_crawling/
├── src/
│   ├── api/                          # FastAPI Backend
│   │   ├── main.py                   # FastAPI app
│   │   ├── routers/
│   │   │   ├── stats.py              # /api/stats
│   │   │   ├── matches.py            # /api/matches
│   │   │   ├── youtube.py            # /api/youtube
│   │   │   └── export.py             # /api/export
│   │   ├── services/
│   │   │   ├── match_service.py
│   │   │   └── youtube_service.py
│   │   └── schemas/
│   │       └── match.py
│   │
│   └── ui/                           # React Frontend
│       ├── src/
│       │   ├── components/
│       │   │   ├── layout/
│       │   │   │   ├── Navbar.tsx
│       │   │   │   └── Layout.tsx
│       │   │   ├── dashboard/
│       │   │   │   ├── StatsCards.tsx
│       │   │   │   ├── StatusPieChart.tsx
│       │   │   │   └── CategoryBreakdown.tsx
│       │   │   ├── matches/
│       │   │   │   ├── MatchCard.tsx
│       │   │   │   ├── MatchList.tsx
│       │   │   │   ├── FilterBar.tsx
│       │   │   │   └── ManualMatchModal.tsx
│       │   │   └── common/
│       │   │       ├── StatusBadge.tsx
│       │   │       └── ScoreIndicator.tsx
│       │   ├── pages/
│       │   │   ├── Dashboard.tsx
│       │   │   ├── MatchList.tsx
│       │   │   ├── NotUploaded.tsx
│       │   │   └── ManualMatch.tsx
│       │   ├── stores/
│       │   │   └── matchStore.ts
│       │   ├── api/
│       │   │   └── matchApi.ts
│       │   ├── types/
│       │   │   └── match.ts
│       │   ├── App.tsx
│       │   └── main.tsx
│       ├── package.json
│       ├── vite.config.ts
│       └── tailwind.config.js
│
├── data/
│   ├── db/
│   │   └── pokergo.db               # SQLite (content_mapping)
│   └── analysis/
│       ├── full_episode_matching_all.json
│       └── not_uploaded_content.json
```

---

## 11. Implementation Phases

```mermaid
gantt
    title Implementation Timeline
    dateFormat  YYYY-MM-DD

    section Phase 1: Backend API
    FastAPI Setup           :a1, 2025-12-13, 1d
    Stats Endpoints         :a2, after a1, 1d
    Matches CRUD            :a3, after a2, 1d

    section Phase 2: Core UI
    React + Vite Setup      :b1, 2025-12-13, 1d
    Dashboard Page          :b2, after b1, 1d
    Match List Page         :b3, after b2, 2d

    section Phase 3: Features
    Not Uploaded Page       :c1, after b3, 1d
    Manual Match Modal      :c2, after c1, 1d
    Filter & Search         :c3, after c2, 1d

    section Phase 4: Polish
    Charts & Visualization  :d1, after c3, 1d
    Export Features         :d2, after d1, 1d
    Testing & Refinement    :d3, after d2, 1d
```

---

## 12. Key Features Summary

### 12.1 Dashboard
- 전체 매칭 현황 카드 (742개 중 628개 매칭)
- 상태별 파이 차트
- 점수 분포 히스토그램
- 미업로드 카테고리별 분류

### 12.2 Match List
- 상태, 점수, 연도, 이벤트별 필터
- NAS 파일명/YouTube 제목 검색
- 빠른 검증(Verify)/오류 신고(Wrong) 버튼
- 매칭 점수 상세 breakdown

### 12.3 Not Uploaded Management
- 카테고리별 그룹핑 (WSOP Europe, Paradise, etc.)
- 체크박스 다중 선택
- 일괄 작업 (업로드 예정, 제외, 수동 매칭)

### 12.4 Manual Match
- NAS 파일 정보 표시
- YouTube 검색 기능
- 유사도 점수와 함께 결과 표시
- "YouTube에 없음" 확정 옵션

---

## 13. Success Criteria

| Metric | Target |
|--------|--------|
| 대시보드 로딩 | < 1초 |
| 목록 페이지네이션 | < 200ms |
| 검색 응답 | < 500ms |
| 일괄 작업 (100건) | < 3초 |
| 검증 작업 클릭 수 | 1 click |

---

## 14. Future Enhancements

1. **YouTube 미리보기**: 영상 인라인 플레이어
2. **NAS 썸네일**: 비디오 파일 미리보기 이미지
3. **AI 추천**: 미매칭 콘텐츠에 대한 AI 기반 YouTube 검색
4. **알림**: 새 콘텐츠 감지 시 알림
5. **히스토리**: 모든 변경 이력 추적

---

## 15. References

- PRD-0033: Video Matching System
- PRD-0034: Matching Review UI (초기 설계)
- 매칭 결과: `data/analysis/full_episode_matching_all.json`
- 미업로드 목록: `data/analysis/not_uploaded_content.json`

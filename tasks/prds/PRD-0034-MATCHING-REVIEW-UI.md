# PRD-0034: Matching Review UI

**Version**: 1.0
**Date**: 2025-12-12
**Author**: Claude
**Status**: Draft
**Depends on**: PRD-0033 (Video Matching System)

---

## 1. Executive Summary

YouTube-NAS 비디오 매칭 결과를 검토하고 승인/거부할 수 있는 웹 기반 리뷰 UI를 설계합니다.

### 1.1 Goals

- 매칭 결과를 시각적으로 비교 검토
- 빠른 승인/거부 워크플로우
- 필터링 및 검색으로 효율적인 리뷰
- 매칭 통계 대시보드

### 1.2 Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | React + TypeScript |
| UI Framework | Tailwind CSS + shadcn/ui |
| State | Zustand |
| Backend | FastAPI (Python) |
| Database | SQLite (기존 DB 활용) |

---

## 2. System Architecture

```mermaid
flowchart TB
    subgraph Frontend["Frontend (React)"]
        UI[Review UI]
        Store[Zustand Store]
        API_Client[API Client]
    end

    subgraph Backend["Backend (FastAPI)"]
        Router[API Router]
        Service[Matching Service]
        Repo[Repository]
    end

    subgraph Database["Database"]
        SQLite[(SQLite DB)]
        JSON[(JSON Cache)]
    end

    UI --> Store
    Store --> API_Client
    API_Client -->|REST API| Router
    Router --> Service
    Service --> Repo
    Repo --> SQLite
    Repo --> JSON
```

---

## 3. Data Model

### 3.1 Entity Relationship Diagram

```mermaid
erDiagram
    YOUTUBE_VIDEO {
        string video_id PK
        string title
        string description
        int duration
        date upload_date
        int view_count
        string thumbnail_url
    }

    NAS_FILE {
        string file_id PK
        string filename
        string filepath
        int size_bytes
        string parsed_show
        int parsed_year
        int parsed_episode
    }

    MATCH_RESULT {
        int id PK
        string youtube_id FK
        string nas_file_id FK
        int score
        string status
        json score_details
        datetime created_at
        datetime reviewed_at
        string reviewed_by
    }

    REVIEW_LOG {
        int id PK
        int match_id FK
        string action
        string previous_status
        string new_status
        string notes
        datetime created_at
    }

    YOUTUBE_VIDEO ||--o{ MATCH_RESULT : "matched_to"
    NAS_FILE ||--o{ MATCH_RESULT : "matched_from"
    MATCH_RESULT ||--o{ REVIEW_LOG : "has_logs"
```

### 3.2 Match Status State Machine

```mermaid
stateDiagram-v2
    [*] --> Pending: 매칭 생성

    Pending --> Approved: 승인
    Pending --> Rejected: 거부
    Pending --> NeedsReview: 수동 검토 필요

    NeedsReview --> Approved: 승인
    NeedsReview --> Rejected: 거부
    NeedsReview --> Modified: 수정 후 승인

    Approved --> [*]
    Rejected --> [*]
    Modified --> [*]

    note right of Pending
        score >= 80: auto-approve candidate
        score 40-79: needs review
        score < 40: auto-reject candidate
    end note
```

---

## 4. Screen Design

### 4.1 Screen Flow

```mermaid
flowchart LR
    subgraph Main["Main Screens"]
        Dashboard[Dashboard]
        List[Match List]
        Detail[Match Detail]
        Bulk[Bulk Review]
    end

    subgraph Modals["Modals"]
        Filter[Filter Modal]
        Confirm[Confirm Modal]
        Notes[Notes Modal]
    end

    Dashboard --> List
    List --> Detail
    List --> Bulk
    List --> Filter
    Detail --> Confirm
    Detail --> Notes
    Bulk --> Confirm
```

### 4.2 Dashboard Layout

```mermaid
block-beta
    columns 4

    block:header:4
        Logo["PokerGO Matcher"] Space:2 User["User Menu"]
    end

    block:stats:4
        Total["Total Matches\n700"]
        Pending["Pending\n200"]
        Approved["Approved\n450"]
        Rejected["Rejected\n50"]
    end

    block:chart:2
        ScoreChart["Score Distribution\n(Bar Chart)"]
    end

    block:recent:2
        RecentList["Recent Reviews\n(Table)"]
    end

    block:actions:4
        StartReview["Start Review →"]
        BulkApprove["Bulk Approve High Score"]
        Export["Export Results"]
        Settings["Settings"]
    end
```

### 4.3 Match List View

```
┌─────────────────────────────────────────────────────────────────────────┐
│  [Search...........................] [Filter ▼] [Sort: Score ▼] [Bulk] │
├─────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ [85] Phil Ivey DESTROYS at WSOP 2024...                         │   │
│  │      ↔ 16-wsop-2024-be-ev-29-2-7TD-Ivey-Vs-Wong.mp4             │   │
│  │      Year ✓ | Player ✓ | Event ✓ | Game ✓                       │   │
│  │      [Approve] [Reject] [Details →]                    PENDING  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ [72] Negreanu Hits Straight Flush...                            │   │
│  │      ↔ 33-wsop-2024-be-ev-58-negreanu-hits-straight.mp4         │   │
│  │      Year ✓ | Player ✓ | Event ✓ | Game ✗                       │   │
│  │      [Approve] [Reject] [Details →]                    PENDING  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  [← Prev]  Page 1 of 35  [Next →]                                      │
└─────────────────────────────────────────────────────────────────────────┘
```

### 4.4 Match Detail View

```mermaid
block-beta
    columns 3

    block:header:3
        Back["← Back to List"]
        Title["Match Detail #127"]
        Actions["[Approve] [Reject]"]
    end

    block:youtube:1
        YT_Card["YouTube Video\n─────────────\nPhil Ivey DESTROYS...\n\nDuration: 12:34\nViews: 125,000\nUploaded: 2024-06-15\n\n[Watch on YouTube]"]
    end

    block:score:1
        Score_Card["Match Score: 85\n─────────────\n✓ Year: +30\n✓ Player: +30\n✓ Event: +20\n✗ Game: +0\n~ Fuzzy: +5"]
    end

    block:nas:1
        NAS_Card["NAS File\n─────────────\n16-wsop-2024-be-ev-29\n-2-7TD-Ivey-Vs-Wong.mp4\n\nSize: 1.2 GB\nPath: /ARCHIVE/WSOP/2024/\n\n[Open Folder]"]
    end

    block:notes:3
        Notes["Review Notes\n──────────────────────────────────────────\n[Add note...]"]
    end
```

---

## 5. User Flows

### 5.1 Single Review Flow

```mermaid
sequenceDiagram
    actor User
    participant List as Match List
    participant Detail as Detail View
    participant API as Backend API
    participant DB as Database

    User->>List: Click match item
    List->>Detail: Navigate to detail
    Detail->>API: GET /matches/{id}
    API->>DB: Query match data
    DB-->>API: Return data
    API-->>Detail: Match details + score breakdown

    User->>Detail: Click [Approve]
    Detail->>Detail: Show confirm modal
    User->>Detail: Confirm approval
    Detail->>API: PATCH /matches/{id} {status: approved}
    API->>DB: Update status
    DB-->>API: Success
    API-->>Detail: Updated match
    Detail->>List: Navigate back (auto-next)
```

### 5.2 Bulk Review Flow

```mermaid
sequenceDiagram
    actor User
    participant List as Match List
    participant Bulk as Bulk Modal
    participant API as Backend API
    participant DB as Database

    User->>List: Click [Bulk Review]
    List->>Bulk: Open bulk modal

    User->>Bulk: Set filter (score >= 80)
    Bulk->>API: GET /matches?score_min=80&status=pending
    API-->>Bulk: 150 matches found

    User->>Bulk: Click [Approve All]
    Bulk->>Bulk: Show confirmation (150 items)
    User->>Bulk: Confirm

    Bulk->>API: POST /matches/bulk-approve {ids: [...]}
    API->>DB: Batch update
    DB-->>API: 150 updated
    API-->>Bulk: Success summary

    Bulk->>List: Close & refresh
```

---

## 6. Component Hierarchy

```mermaid
flowchart TB
    App[App]

    App --> Layout[Layout]
    Layout --> Header[Header]
    Layout --> Sidebar[Sidebar]
    Layout --> Main[Main Content]

    Main --> Dashboard[DashboardPage]
    Main --> MatchList[MatchListPage]
    Main --> MatchDetail[MatchDetailPage]

    Dashboard --> StatsCards[StatsCards]
    Dashboard --> ScoreChart[ScoreDistributionChart]
    Dashboard --> RecentReviews[RecentReviewsTable]

    MatchList --> SearchBar[SearchBar]
    MatchList --> FilterPanel[FilterPanel]
    MatchList --> MatchCard[MatchCard]
    MatchList --> Pagination[Pagination]
    MatchList --> BulkActions[BulkActions]

    MatchCard --> ScoreBadge[ScoreBadge]
    MatchCard --> StatusBadge[StatusBadge]
    MatchCard --> QuickActions[QuickActions]

    MatchDetail --> YouTubePanel[YouTubePanel]
    MatchDetail --> ScorePanel[ScorePanel]
    MatchDetail --> NASPanel[NASPanel]
    MatchDetail --> ReviewActions[ReviewActions]
    MatchDetail --> NotesSection[NotesSection]
```

---

## 7. API Endpoints

### 7.1 API Structure

```mermaid
flowchart LR
    subgraph Matches["/api/matches"]
        GET_List["GET /\nList matches"]
        GET_One["GET /{id}\nGet single match"]
        PATCH_One["PATCH /{id}\nUpdate status"]
        POST_Bulk["POST /bulk-update\nBulk status update"]
    end

    subgraph Stats["/api/stats"]
        GET_Summary["GET /summary\nDashboard stats"]
        GET_Distribution["GET /distribution\nScore distribution"]
    end

    subgraph Export["/api/export"]
        POST_Export["POST /\nExport results"]
    end
```

### 7.2 API Specifications

| Endpoint | Method | Description | Parameters |
|----------|--------|-------------|------------|
| `/api/matches` | GET | List matches | `page`, `limit`, `status`, `score_min`, `score_max`, `search` |
| `/api/matches/{id}` | GET | Get match detail | - |
| `/api/matches/{id}` | PATCH | Update match | `status`, `notes` |
| `/api/matches/bulk-update` | POST | Bulk update | `ids[]`, `status` |
| `/api/stats/summary` | GET | Dashboard stats | - |
| `/api/stats/distribution` | GET | Score histogram | `bins` |
| `/api/export` | POST | Export to JSON/CSV | `format`, `status_filter` |

---

## 8. Filter & Search

### 8.1 Filter Options

```mermaid
flowchart TB
    subgraph Filters["Filter Panel"]
        Status["Status Filter\n☐ Pending\n☐ Approved\n☐ Rejected\n☐ Needs Review"]

        Score["Score Range\n[====|----] 40-100"]

        Date["Date Range\n[From] [To]"]

        Source["Source Filter\n☐ WSOP\n☐ High Stakes\n☐ Poker After Dark"]

        Year["Year\n☐ 2024\n☐ 2023\n☐ 2022\n☐ Earlier"]
    end
```

### 8.2 Search Behavior

```mermaid
flowchart LR
    Input[Search Input] --> Debounce[Debounce 300ms]
    Debounce --> Parse[Parse Query]

    Parse --> YouTube[Search YouTube titles]
    Parse --> NAS[Search NAS filenames]
    Parse --> Player[Search player names]

    YouTube --> Merge[Merge Results]
    NAS --> Merge
    Player --> Merge

    Merge --> Display[Display Results]
```

---

## 9. Keyboard Shortcuts

| Key | Action | Context |
|-----|--------|---------|
| `j` / `↓` | Next item | List view |
| `k` / `↑` | Previous item | List view |
| `Enter` | Open detail | List view |
| `a` | Approve | Detail view |
| `r` | Reject | Detail view |
| `Esc` | Back / Close modal | All |
| `/` | Focus search | All |
| `?` | Show shortcuts | All |

---

## 10. Implementation Plan

### 10.1 Phase Breakdown

```mermaid
gantt
    title Implementation Timeline
    dateFormat  YYYY-MM-DD

    section Backend
    API Endpoints           :b1, 2025-12-13, 1d
    Database Schema Update  :b2, after b1, 1d

    section Frontend
    Project Setup          :f1, 2025-12-13, 1d
    Dashboard Page         :f2, after f1, 1d
    Match List Page        :f3, after f2, 1d
    Match Detail Page      :f4, after f3, 1d
    Bulk Review Feature    :f5, after f4, 1d

    section Integration
    API Integration        :i1, after b2, 1d
    Testing & Polish       :i2, after f5, 1d
```

### 10.2 Directory Structure

```
src/
├── api/                          # FastAPI Backend
│   ├── main.py
│   ├── routers/
│   │   ├── matches.py
│   │   └── stats.py
│   └── schemas/
│       └── match.py
│
└── ui/                           # React Frontend
    ├── src/
    │   ├── components/
    │   │   ├── layout/
    │   │   ├── match/
    │   │   └── common/
    │   ├── pages/
    │   │   ├── Dashboard.tsx
    │   │   ├── MatchList.tsx
    │   │   └── MatchDetail.tsx
    │   ├── stores/
    │   │   └── matchStore.ts
    │   ├── api/
    │   │   └── matchApi.ts
    │   └── App.tsx
    ├── package.json
    └── vite.config.ts
```

---

## 11. Success Criteria

- [ ] Dashboard loads in < 1 second
- [ ] List pagination smooth (< 200ms per page)
- [ ] Single review: < 3 clicks to approve/reject
- [ ] Bulk review: process 100+ items in single action
- [ ] Keyboard-first workflow supported
- [ ] Mobile-responsive design

---

## 12. Future Enhancements

1. **Video Preview**: YouTube 영상 인라인 미리보기
2. **NAS Thumbnail**: 비디오 파일 썸네일 생성
3. **AI Suggestions**: 낮은 점수 매칭에 대한 AI 추천
4. **Undo/Redo**: 리뷰 작업 되돌리기
5. **Collaboration**: 다중 리뷰어 지원

---

## 13. References

- PRD-0033: Video Matching System
- shadcn/ui: https://ui.shadcn.com/
- Zustand: https://zustand-demo.pmnd.rs/

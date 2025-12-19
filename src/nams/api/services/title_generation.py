"""Title generation service for NAMS.

Phase 3: 제목 생성 및 개선 서비스
- 패턴 기반 제목 생성 (기본)
- AI 추론 제목 생성 (Gemini, 선택사항)
"""
import os
import re
from pathlib import Path

# Load .env file
from dotenv import load_dotenv

env_path = Path(__file__).parent.parent.parent.parent.parent / '.env'
load_dotenv(env_path)
from dataclasses import dataclass
from typing import Optional

from sqlalchemy.orm import Session

from ..database.models import Category, CategoryEntry


@dataclass
class TitleGenerationResult:
    """제목 생성 결과."""
    entry_id: int
    old_title: str
    new_title: str
    method: str  # 'pattern' | 'ai'
    confidence: float


# =============================================================================
# Pattern-based Title Generation
# =============================================================================

REGION_NAMES = {
    'LV': '',  # Las Vegas는 기본값이므로 생략
    'EU': 'Europe',
    'APAC': 'APAC',
    'PARADISE': 'Paradise',
    'CYPRUS': 'Cyprus',
    'LA': 'Circuit LA',
    'LONDON': 'London',
}

EVENT_TYPE_NAMES = {
    'ME': 'Main Event',
    'BR': 'Bracelet Event',
    'HU': 'Heads-Up Championship',
    'GM': 'Grudge Match',
    'HR': 'High Roller',
    'FT': 'Final Table',
    'MB': 'Mystery Bounty',
    'BEST': 'Best Of',
}


def generate_title_pattern(entry: CategoryEntry, category: Category) -> str:
    """패턴 기반 제목 생성.

    형식: "WSOP [Region] [Year] [Event Type] [Sequence]"
    예: "WSOP Europe 2022 Main Event Day 3"
    """
    parts = ['WSOP']

    # Region (LV는 생략)
    if category and category.region and category.region != 'LV':
        region_name = REGION_NAMES.get(category.region, category.region)
        if region_name:
            parts.append(region_name)

    # Year
    if entry.year:
        parts.append(str(entry.year))

    # Event Type
    if entry.event_type:
        event_name = EVENT_TYPE_NAMES.get(entry.event_type, entry.event_type)
        parts.append(event_name)

    # Sequence (Day/Episode/Part)
    if entry.sequence:
        seq_type = entry.sequence_type or 'Episode'
        if seq_type.upper() == 'DAY':
            parts.append(f'Day {entry.sequence}')
        elif seq_type.upper() == 'PART':
            parts.append(f'Part {entry.sequence}')
        else:
            parts.append(f'Episode {entry.sequence}')

    return ' '.join(parts)


def improve_title_consistency(title: str) -> str:
    """제목 일관성 개선.

    - 대소문자 정규화
    - 공백 정리
    - 약어 표준화
    """
    if not title:
        return title

    # Normalize WSOP/Wsop
    title = re.sub(r'\bwsop\b', 'WSOP', title, flags=re.I)
    title = re.sub(r'\bwsope\b', 'WSOPE', title, flags=re.I)

    # Normalize common terms
    replacements = {
        r'\bmain\s+event\b': 'Main Event',
        r'\bfinal\s+table\b': 'Final Table',
        r'\bheads[\-\s]?up\b': 'Heads-Up',
        r'\bhigh\s+roller\b': 'High Roller',
        r'\bgrudge\s+match\b': 'Grudge Match',
        r'\bday\s*(\d+)': r'Day \1',
        r'\bepisode\s*(\d+)': r'Episode \1',
        r'\bpart\s*(\d+)': r'Part \1',
        r'\bevent\s*#?\s*(\d+)': r'Event #\1',
    }

    for pattern, replacement in replacements.items():
        title = re.sub(pattern, replacement, title, flags=re.I)

    # Clean up whitespace
    title = ' '.join(title.split())

    return title


# =============================================================================
# AI-based Title Generation (Optional)
# =============================================================================

def generate_title_ai(
    entry: CategoryEntry,
    category: Category,
    pokergo_context: list[dict],
) -> Optional[str]:
    """AI 기반 제목 생성 (Gemini).

    환경변수 GOOGLE_API_KEY가 필요합니다.
    """
    api_key = os.environ.get('GOOGLE_API_KEY')
    if not api_key:
        return None

    try:
        import google.generativeai as genai

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.0-flash')

        # Build context from similar PokerGO episodes
        context_examples = []
        for ctx in pokergo_context[:10]:
            context_examples.append(f"- {ctx.get('title', '')}")

        prompt = f"""
다음 NAS 파일 정보를 바탕으로 WSOP 콘텐츠 제목을 생성해주세요.

## 파일 정보
- 연도: {entry.year}
- 지역: {category.region if category else 'LV'}
- 이벤트 타입: {entry.event_type}
- 시퀀스: {entry.sequence} ({entry.sequence_type})
- 현재 제목: {entry.display_title}

## PokerGO 제목 예시 (참고)
{chr(10).join(context_examples)}

## 생성 규칙
1. 형식: "WSOP [지역] [연도] [이벤트] [세부정보]"
2. 지역이 LV(Las Vegas)면 생략
3. 이벤트: Main Event, Bracelet Event, High Roller 등
4. 세부정보: Day 1, Episode 3, Part 2 등

제목만 한 줄로 출력해주세요.
"""

        response = model.generate_content(prompt)
        return response.text.strip()

    except ImportError as e:
        print(f"[AI] ImportError: {e}")
        return None
    except Exception as e:
        print(f"[AI] Exception: {e}")
        return None


# =============================================================================
# Main Functions
# =============================================================================

def generate_titles_for_none_entries(
    db: Session,
    use_ai: bool = False,
    dry_run: bool = False,
) -> dict:
    """NONE 매칭 항목의 제목 생성/개선.

    Args:
        db: Database session
        use_ai: AI 생성 사용 여부
        dry_run: True면 실제 저장하지 않음

    Returns:
        통계 정보
    """
    stats = {
        'total': 0,
        'improved': 0,
        'ai_generated': 0,
        'pattern_generated': 0,
        'unchanged': 0,
        'samples': [],
    }

    # NONE 매칭 항목 조회
    entries = db.query(CategoryEntry).filter(
        CategoryEntry.match_type == 'NONE'
    ).all()

    stats['total'] = len(entries)

    # Category lookup
    categories = {c.id: c for c in db.query(Category).all()}

    # PokerGO context for AI (if enabled)
    pokergo_context = []
    if use_ai:
        from ..database.models import PokergoEpisode
        episodes = db.query(PokergoEpisode).limit(100).all()
        pokergo_context = [{'title': ep.title} for ep in episodes]

    for entry in entries:
        category = categories.get(entry.category_id)
        old_title = entry.display_title

        # Generate new title
        new_title = None

        # Try AI first if enabled
        if use_ai:
            new_title = generate_title_ai(entry, category, pokergo_context)
            if new_title:
                stats['ai_generated'] += 1

        # Fallback to pattern
        if not new_title:
            new_title = generate_title_pattern(entry, category)
            stats['pattern_generated'] += 1

        # Improve consistency
        new_title = improve_title_consistency(new_title)

        # Check if actually improved
        if new_title and new_title != old_title:
            if not dry_run:
                entry.display_title = new_title

            stats['improved'] += 1

            # Sample for reporting
            if len(stats['samples']) < 10:
                stats['samples'].append({
                    'entry_code': entry.entry_code,
                    'old': old_title,
                    'new': new_title,
                })
        else:
            stats['unchanged'] += 1

    if not dry_run:
        db.commit()

    return stats


def improve_all_titles(db: Session, dry_run: bool = False) -> dict:
    """모든 제목의 일관성 개선.

    대소문자, 공백, 약어 표준화.
    """
    stats = {
        'total': 0,
        'improved': 0,
        'samples': [],
    }

    entries = db.query(CategoryEntry).all()
    stats['total'] = len(entries)

    for entry in entries:
        old_title = entry.display_title
        new_title = improve_title_consistency(old_title)

        if new_title != old_title:
            if not dry_run:
                entry.display_title = new_title

            stats['improved'] += 1

            if len(stats['samples']) < 10:
                stats['samples'].append({
                    'entry_code': entry.entry_code,
                    'old': old_title,
                    'new': new_title,
                })

    if not dry_run:
        db.commit()

    return stats


# =============================================================================
# Standalone
# =============================================================================

def run_title_generation(use_ai: bool = False, dry_run: bool = False) -> dict:
    """독립 실행."""
    from ..database import get_db_context

    with get_db_context() as db:
        results = {}

        # 1. Improve all titles consistency
        results['consistency'] = improve_all_titles(db, dry_run)

        # 2. Generate titles for NONE entries
        results['generation'] = generate_titles_for_none_entries(db, use_ai, dry_run)

        return results

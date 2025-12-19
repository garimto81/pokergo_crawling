"""Analyze unmatched NAS files and classify failure reasons.

PRD 원인 코드:
- P01: 패턴 미지원
- P02: 연도 추출 실패
- P03: 이벤트 타입 인식 실패
- P04: 에피소드 번호 추출 실패
- M01: PokerGO 타이틀 형식 불일치
- M02: 유사도 점수 임계값 문제
- D01: PokerGO에 해당 콘텐츠 없음
- D02: NAS에 해당 콘텐츠 없음
"""
import re
import sys
import sqlite3
from pathlib import Path
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Optional

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))


@dataclass
class FailureAnalysis:
    """Analysis result for a single unmatched file."""
    filename: str
    full_path: str
    reason_code: str
    reason_detail: str
    year: Optional[int] = None
    region: Optional[str] = None
    event_type: Optional[str] = None
    episode: Optional[int] = None
    suggested_fix: Optional[str] = None


# Pattern extractors
YEAR_PATTERNS = [
    (r'WS(\d{2})_', 'WS_YY'),
    (r'WSOP(\d{2})_', 'WSOP_YY'),
    (r'WSOPE(\d{2})_', 'WSOPE_YY'),
    (r'WSOP\s+(\d{4})', 'WSOP_YYYY'),
    (r'(\d{4})\s+WSOP', 'YYYY_WSOP'),
    (r'(\d{4})\s+World Series', 'YYYY_WS'),
    (r'wsop-(\d{4})-', 'wsop-yyyy'),
    (r'wsope-(\d{4})-', 'wsope-yyyy'),
    (r'_(\d{4})_', '_YYYY_'),
    (r'\b(19[789]\d|20[012]\d)\b', 'generic'),
]

EVENT_TYPE_PATTERNS = [
    (r'_ME\d', 'ME'),
    (r'Main Event', 'ME'),
    (r'main-event', 'ME'),
    (r'_GM\d', 'GM'),
    (r'Grudge Match', 'GM'),
    (r'_HU\d', 'HU'),
    (r'Heads.?Up', 'HU'),
    (r'_BR\d', 'BR'),
    (r'Bracelet', 'BR'),
    (r'Event #\d', 'BR'),
    (r'_HR\d', 'HR'),
    (r'High Roller', 'HR'),
    (r'APAC', 'APAC'),
    (r'Europe', 'EU'),
    (r'WSOPE', 'EU'),
    (r'Paradise', 'PARADISE'),
]

EPISODE_PATTERNS = [
    (r'_ME(\d+)', 'ME_episode'),
    (r'Episode[\s_]*(\d+)', 'Episode_N'),
    (r'Ep\.?\s*(\d+)', 'Ep_N'),
    (r'Show[\s_]*(\d+)', 'Show_N'),
    (r'Part[\s_]*(\d+)', 'Part_N'),
    (r'Day[\s_]*(\d+)', 'Day_N'),
    (r'#(\d+)', 'hash_N'),
]


def extract_year(filename: str) -> tuple[Optional[int], Optional[str]]:
    """Extract year from filename."""
    for pattern, name in YEAR_PATTERNS:
        match = re.search(pattern, filename, re.I)
        if match:
            year_str = match.group(1)
            if len(year_str) == 2:
                year = int(year_str)
                year = 2000 + year if year < 50 else 1900 + year
            else:
                year = int(year_str)
            return year, name
    return None, None


def extract_event_type(filename: str) -> tuple[Optional[str], Optional[str]]:
    """Extract event type from filename."""
    for pattern, event_type in EVENT_TYPE_PATTERNS:
        if re.search(pattern, filename, re.I):
            return event_type, pattern
    return None, None


def extract_episode(filename: str) -> tuple[Optional[int], Optional[str]]:
    """Extract episode number from filename."""
    for pattern, name in EPISODE_PATTERNS:
        match = re.search(pattern, filename, re.I)
        if match:
            return int(match.group(1)), name
    return None, None


def classify_failure(
    filename: str,
    full_path: str,
    has_pokergo_match: bool,
    db_year: Optional[int],
    db_event_type: Optional[str],
    db_episode: Optional[int],
) -> FailureAnalysis:
    """Classify the failure reason for an unmatched file."""

    # Extract metadata from filename
    year, year_pattern = extract_year(filename)
    event_type, event_pattern = extract_event_type(filename)
    episode, episode_pattern = extract_episode(filename)

    # Determine failure reason
    reason_code = "P01"  # Default: pattern not supported
    reason_detail = "Unknown pattern"
    suggested_fix = None

    # Check extraction results
    if year is None:
        reason_code = "P02"
        reason_detail = f"Year extraction failed from: {filename}"
        suggested_fix = "Add year extraction pattern"
    elif event_type is None:
        reason_code = "P03"
        reason_detail = f"Event type not recognized in: {filename}"
        suggested_fix = "Add event type keyword"
    elif episode is None and event_type in ('ME', 'BR', 'EU'):
        reason_code = "P04"
        reason_detail = f"Episode number not found in: {filename}"
        suggested_fix = "Add episode extraction pattern"
    elif has_pokergo_match is False:
        # Check if it's historic content (before 2011)
        if year and year < 2011:
            reason_code = "D01"
            reason_detail = f"Historic content ({year}) - PokerGO may not have this"
            suggested_fix = "Generate catalog title automatically"
        else:
            reason_code = "M01"
            reason_detail = f"PokerGO title format mismatch for year={year}, type={event_type}, ep={episode}"
            suggested_fix = "Improve matching algorithm"
    else:
        reason_code = "M02"
        reason_detail = "Match score below threshold"
        suggested_fix = "Adjust similarity threshold"

    # Detect specific patterns
    if filename.startswith('#'):
        reason_code = "P01"
        reason_detail = "Hash prefix pattern not supported"
        suggested_fix = "Add pattern for #WSOPE format"
    elif filename.startswith('$'):
        reason_code = "P01"
        reason_detail = "Dollar prefix pattern (tournament name only)"
        suggested_fix = "Add pattern for prize pool format"
    elif '🏆' in filename:
        reason_code = "P01"
        reason_detail = "Emoji pattern not supported"
        suggested_fix = "Add emoji removal preprocessing"
    elif re.match(r'^\d+_\d{4}', filename):
        reason_code = "P01"
        reason_detail = "Numeric prefix pattern not supported"
        suggested_fix = "Add pattern for sequence_year format"
    elif 'Best' in filename and 'Of' in filename:
        reason_code = "P03"
        reason_detail = "Best Of content type"
        suggested_fix = "Add BEST event type handling"
    elif 'Circuit' in filename.lower():
        reason_code = "D01"
        reason_detail = "WSOP Circuit - separate event"
        suggested_fix = "Exclude from WSOP matching"

    return FailureAnalysis(
        filename=filename,
        full_path=full_path,
        reason_code=reason_code,
        reason_detail=reason_detail,
        year=year,
        region=event_type if event_type in ('EU', 'APAC', 'PARADISE') else None,
        event_type=event_type,
        episode=episode,
        suggested_fix=suggested_fix,
    )


def analyze_unmatched_files(db_path: str) -> dict:
    """Analyze all unmatched files and classify failure reasons."""

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Get unmatched files (not excluded, no asset_group or no pokergo match)
    cursor.execute('''
        SELECT
            nf.id,
            nf.filename,
            nf.full_path,
            nf.year,
            nf.is_excluded,
            nf.role,
            ag.pokergo_episode_id,
            ag.match_category
        FROM nas_files nf
        LEFT JOIN asset_groups ag ON nf.asset_group_id = ag.id
        WHERE nf.is_excluded = 0
          AND (ag.pokergo_episode_id IS NULL OR ag.id IS NULL)
    ''')

    unmatched = cursor.fetchall()

    # Classify each file
    analyses = []
    reason_counter = Counter()
    pattern_samples = defaultdict(list)

    for row in unmatched:
        analysis = classify_failure(
            filename=row['filename'],
            full_path=row['full_path'],
            has_pokergo_match=row['pokergo_episode_id'] is not None,
            db_year=row['year'],
            db_event_type=None,  # Would need join to get
            db_episode=None,
        )
        analyses.append(analysis)
        reason_counter[analysis.reason_code] += 1

        if len(pattern_samples[analysis.reason_code]) < 5:
            pattern_samples[analysis.reason_code].append({
                'filename': analysis.filename[:80],
                'detail': analysis.reason_detail,
                'fix': analysis.suggested_fix,
            })

    conn.close()

    return {
        'total_unmatched': len(analyses),
        'by_reason': dict(reason_counter.most_common()),
        'samples': dict(pattern_samples),
        'analyses': analyses,
    }


def print_report(result: dict):
    """Print analysis report."""
    print("=" * 80)
    print("미매칭 파일 원인 분석 보고서")
    print("=" * 80)
    print()
    print(f"총 미매칭 파일: {result['total_unmatched']}")
    print()
    print("원인 코드별 분포:")
    print("-" * 40)

    reason_names = {
        'P01': '패턴 미지원',
        'P02': '연도 추출 실패',
        'P03': '이벤트 타입 인식 실패',
        'P04': '에피소드 번호 추출 실패',
        'M01': 'PokerGO 타이틀 형식 불일치',
        'M02': '유사도 점수 임계값 문제',
        'D01': 'PokerGO에 해당 콘텐츠 없음',
        'D02': 'NAS에 해당 콘텐츠 없음',
    }

    for code, count in result['by_reason'].items():
        pct = count / result['total_unmatched'] * 100 if result['total_unmatched'] > 0 else 0
        name = reason_names.get(code, code)
        print(f"  {code} ({name}): {count} ({pct:.1f}%)")

    print()
    print("샘플 파일 및 해결 방안:")
    print("-" * 40)

    for code, samples in result['samples'].items():
        name = reason_names.get(code, code)
        print(f"\n[{code}] {name}")
        for s in samples[:3]:
            print(f"  - {s['filename']}")
            print(f"    원인: {s['detail']}")
            print(f"    해결: {s['fix']}")


def main():
    """Main entry point."""
    import io
    import sys
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    db_path = Path(__file__).parent.parent / 'src' / 'nams' / 'data' / 'nams.db'

    if not db_path.exists():
        print(f"DB not found: {db_path}")
        return

    print(f"Analyzing: {db_path}")
    result = analyze_unmatched_files(str(db_path))
    print_report(result)

    # Export to JSON
    import json
    output_path = Path(__file__).parent.parent / 'data' / 'analysis' / 'unmatched_analysis.json'
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Convert analyses to dicts for JSON
    export_data = {
        'total_unmatched': result['total_unmatched'],
        'by_reason': result['by_reason'],
        'samples': result['samples'],
    }

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, ensure_ascii=False, indent=2)

    print(f"\nExported to: {output_path}")


if __name__ == '__main__':
    main()

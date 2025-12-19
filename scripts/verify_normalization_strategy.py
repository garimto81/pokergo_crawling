"""Verify normalization strategy covers all 2025 NAS files."""
import sys
import re
from pathlib import Path
from dataclasses import dataclass, field
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.stdout.reconfigure(encoding='utf-8')

from src.nams.api.database import get_db
from src.nams.api.database.models import NasFile


@dataclass
class NasFileNormalized:
    """Normalized NAS file data."""
    file_id: int
    full_path: str
    filename: str

    # Normalized elements
    region: str = ''           # LV, EU, CYPRUS_MPP, CIRCUIT, UNKNOWN
    series: str = ''           # WSOP, WSOPE, MPP, OTHER
    event_type: str = ''       # BR, ME, OTHER
    event_num: int | None = None
    day: str = ''              # 1, 1A, 2ABC, FT, FT_D1, Final, FinalDay, F4
    part: int | None = None
    session: int | None = None # 1, 2 (Cyprus MPP Main Event)

    # Cyprus specific
    cyprus_event: str = ''     # POKEROK, LUXON, MPP_ME

    # Additional info
    source: str = ''           # PokerGO, YouTube
    version: str = ''          # NC, STREAM
    resolution: str = ''       # 1080p, 720p
    is_raw: bool = False       # HyperDeck raw file (v1.2)
    hd_sequence: tuple = (0, 0)  # HyperDeck sequence (main, sub) for sorting

    # Meta
    pattern_id: str = ''       # P1-P10
    is_excluded: bool = False
    exclusion_reason: str = ''

    # Validation
    issues: list = field(default_factory=list)


def extract_region(full_path: str) -> str:
    """Extract region from path."""
    if not full_path:
        return 'UNKNOWN'
    path_upper = full_path.upper()

    if 'WSOP-LAS VEGAS' in path_upper:
        return 'LV'
    elif 'WSOP-EUROPE' in path_upper:
        return 'EU'
    elif 'MPP' in path_upper and 'CYPRUS' in path_upper:
        return 'CYPRUS_MPP'
    elif 'CIRCUIT' in path_upper:
        return 'CIRCUIT'

    return 'UNKNOWN'


def extract_series(full_path: str, filename: str) -> str:
    """Extract series from path + filename."""
    combined = (full_path + filename).upper()

    if 'WSOPE' in combined:
        return 'WSOPE'
    elif 'WSOP' in combined:
        return 'WSOP'
    elif 'MPP' in combined:
        return 'MPP'
    elif 'POKEROK' in combined or 'LUXON' in combined:
        return 'POKEROK'

    return 'OTHER'


def extract_event_type(full_path: str, filename: str) -> str:
    """Extract event type from path (priority) + filename."""
    path_upper = full_path.upper() if full_path else ''
    fname_upper = filename.upper()

    # Path-based (priority)
    if 'MAIN EVENT' in path_upper:
        return 'ME'
    elif 'BRACELET' in path_upper or 'SIDE EVENT' in path_upper:
        return 'BR'

    # Filename-based
    if 'MAIN EVENT' in fname_upper:
        return 'ME'
    elif 'BRACELET' in fname_upper or 'EVENT #' in fname_upper or 'WSOPE #' in fname_upper:
        return 'BR'

    return 'OTHER'


def extract_event_num(full_path: str, filename: str) -> int | None:
    """Extract Event # from path + filename."""
    combined = (full_path or '') + ' ' + filename

    # Pattern 1: Event #N (WSOP LV)
    match = re.search(r'Event\s*#(\d+)', combined, re.I)
    if match:
        return int(match.group(1))

    # Pattern 2: [BRACELET #N] or [BRACELET EVENT #N]
    match = re.search(r'\[BRACELET(?:\s+EVENT)?\s*#(\d+)\]', combined, re.I)
    if match:
        return int(match.group(1))

    # Pattern 3: WSOPE #N (WSOP Europe) - filename only
    match = re.search(r'WSOPE\s*#(\d+)', filename, re.I)
    if match:
        return int(match.group(1))

    # Pattern 4: WSOP-EUROPE #N (path) - v1.1 fix
    if full_path:
        match = re.search(r'WSOP-EUROPE\s*#(\d+)', full_path, re.I)
        if match:
            return int(match.group(1))

    return None


def extract_day(filename: str) -> str:
    """Extract Day from filename."""
    # Pattern 1: Day NA_B_C or Day NA/B/C (복합 Day) - v1.1 우선 처리
    match = re.search(r'Day\s*(\d+)([A-D])(?:[_/])([A-D])(?:[_/])?([A-D])?', filename, re.I)
    if match:
        day = match.group(1)
        parts = [match.group(2), match.group(3)]
        if match.group(4):
            parts.append(match.group(4))
        return day + ''.join(parts)  # e.g., 2ABC

    # Pattern 2: Day N[A-D] (e.g., Day 1A, Day 2)
    match = re.search(r'Day\s*(\d+)\s*([A-D])?', filename, re.I)
    if match:
        day = match.group(1)
        suffix = match.group(2) or ''
        return day + suffix

    # Pattern 3: Final Table _ Day N
    match = re.search(r'Final Table.*Day\s*(\d+)', filename, re.I)
    if match:
        return 'FT_D' + match.group(1)

    # Pattern 4: Final Table (no day specified)
    if re.search(r'Final Table', filename, re.I):
        return 'FT'

    # Pattern 5: Final Day
    if 'Final Day' in filename:
        return 'FinalDay'

    # Pattern 6: Final (Heads-Up Final, etc.) - but not in Event name
    if re.search(r'(?<!Event\s)Final(?!\s*Table)', filename) and 'Final Four' not in filename:
        # Check it's not part of event name like "Event #7 Final"
        if not re.search(r'Event\s*#\d+.*Final', filename):
            return 'Final'

    # Pattern 7: Final Four
    if 'Final Four' in filename:
        return 'F4'

    return ''


def extract_session(filename: str) -> int | None:
    """Extract Session from filename (Cyprus MPP Main Event)."""
    match = re.search(r'Session\s*(\d+)', filename, re.I)
    if match:
        return int(match.group(1))
    return None


def extract_cyprus_event(full_path: str, filename: str) -> str:
    """Extract Cyprus event name."""
    fname_upper = filename.upper()

    if 'POKEROK' in fname_upper or 'MYSTERY BOUNTY' in fname_upper:
        return 'POKEROK'
    elif 'LUXON' in fname_upper:
        return 'LUXON'
    elif 'MPP MAIN EVENT' in fname_upper:
        return 'MPP_ME'

    return ''


def extract_hyperdeck_sequence(filename: str) -> tuple[int, int]:
    """Extract sequence numbers from HyperDeck filename.

    Returns (main_num, sub_num) for sorting.
    Example: HyperDeck_0010-004.mp4 → (10, 4)
    """
    match = re.match(r'HyperDeck_(\d+)(?:-(\d+))?', filename)
    if match:
        main_num = int(match.group(1))
        sub_num = int(match.group(2)) if match.group(2) else 0
        return (main_num, sub_num)
    return (0, 0)


def normalize_hyperdeck_from_path(full_path: str, filename: str) -> dict:
    """Extract normalization elements from HyperDeck file path (v1.2)."""
    result = {
        'region': 'EU',
        'series': 'WSOPE',
        'event_type': 'BR',
        'event_num': None,
        'day': 'Final',
        'version': 'NC',
        'is_raw': True,
        'hd_sequence': extract_hyperdeck_sequence(filename)  # For sorting
    }

    # Event # from path: WSOP-EUROPE #N
    match = re.search(r'WSOP-EUROPE\s*#(\d+)', full_path, re.I)
    if match:
        result['event_num'] = int(match.group(1))

    # Event Type: MAIN EVENT → ME, otherwise → BR
    if 'MAIN EVENT' in full_path.upper():
        result['event_type'] = 'ME'

    # Day from folder: "Day 1 A", "Day 2", etc.
    # Note: folder has space like "Day 1 A" not "Day 1A"
    match = re.search(r'Day\s*(\d+)\s*([A-D])?', full_path, re.I)
    if match:
        result['day'] = match.group(1) + (match.group(2) or '')

    return result


def extract_part(filename: str) -> int | None:
    """Extract Part from filename."""
    # Pattern 1: Part N or (Part N)
    match = re.search(r'Part\s*(\d+)', filename, re.I)
    if match:
        return int(match.group(1))

    # Pattern 2: PartN_NC (WSOPE NC files)
    match = re.search(r'Part(\d+)_NC', filename, re.I)
    if match:
        return int(match.group(1))

    return None


def extract_sequence(filename: str) -> int | None:
    """Extract sequence prefix (EU NC files)."""
    # Pattern: N_2025 WSOPE... (1 digit = Part order)
    match = re.match(r'^(\d)_\d{4}\s+WSOPE', filename)
    if match:
        return int(match.group(1))

    return None


def extract_source(filename: str) -> str:
    """Extract source from filename prefix."""
    match = re.match(r'\((PokerGO|YouTube)\)', filename, re.I)
    if match:
        return match.group(1)
    return ''


def extract_version(full_path: str, filename: str) -> str:
    """Extract version from filename or path."""
    if '_NC' in filename:
        return 'NC'
    if full_path and 'NO COMMENTARY' in full_path.upper():
        return 'NC'
    if full_path and 'STREAM' in full_path.upper():
        return 'STREAM'
    return ''


def extract_resolution(filename: str) -> str:
    """Extract resolution from filename."""
    match = re.search(r'\((\d+[pP])\)', filename)
    if match:
        return match.group(1).lower()
    return ''


def classify_pattern(filename: str, full_path: str) -> str:
    """Classify file by pattern ID."""
    path_upper = (full_path or '').upper()
    fname_upper = filename.upper()

    # P8: HyperDeck (excluded)
    if filename.startswith('HyperDeck_'):
        return 'P8'

    # P6: Circuit
    if 'CIRCUIT' in path_upper:
        return 'P6'

    # P9: Source Prefix
    if re.match(r'^\((PokerGO|YouTube)\)', filename):
        return 'P9'

    # P10: Date Prefix
    if re.match(r'^\d{6}_', filename):
        return 'P10'

    # P4: WSOPE NC (EU) - N_2025 WSOPE pattern
    if re.match(r'^\d_\d{4}\s+WSOPE', filename):
        return 'P4'

    # P3: WSOPE Stream (EU) - emoji or WSOPE in stream folder
    if '🏆' in filename or ('WSOPE' in fname_upper and 'STREAM' in path_upper):
        return 'P3'

    # P7: Cyprus MPP
    if 'MPP' in path_upper and 'CYPRUS' in path_upper:
        return 'P7'

    # P5: Cyprus PokerOK/Luxon
    if 'POKEROK' in fname_upper or 'LUXON' in fname_upper or 'MYSTERY BOUNTY' in fname_upper:
        return 'P5'

    # P2: WSOP Main Event (LV)
    if 'MAIN EVENT' in path_upper and 'WSOP-LAS VEGAS' in path_upper:
        return 'P2'

    # P1: WSOP Bracelet (LV)
    if 'BRACELET' in path_upper and 'WSOP-LAS VEGAS' in path_upper:
        return 'P1'

    return 'P0'  # Unclassified


def normalize_file(file: NasFile) -> NasFileNormalized:
    """Apply normalization strategy to a single file."""
    result = NasFileNormalized(
        file_id=file.id,
        full_path=file.full_path or '',
        filename=file.filename
    )

    # Apply DB exclusion status first
    result.is_excluded = file.is_excluded
    result.exclusion_reason = file.exclusion_reason or ''

    result.pattern_id = classify_pattern(file.filename, file.full_path or '')

    # P8: HyperDeck - use path-based normalization (v1.2)
    if result.pattern_id == 'P8':
        hd = normalize_hyperdeck_from_path(file.full_path or '', file.filename)
        result.region = hd['region']
        result.series = hd['series']
        result.event_type = hd['event_type']
        result.event_num = hd['event_num']
        result.day = hd['day']
        result.version = hd['version']
        result.is_raw = hd['is_raw']
        result.hd_sequence = hd['hd_sequence']
        # HyperDeck is now normalized, not excluded
        return result

    # P6: Circuit - use DB exclusion status
    if result.pattern_id == 'P6':
        result.is_excluded = file.is_excluded
        result.exclusion_reason = file.exclusion_reason or ''
        if not result.is_excluded:
            # Normalize Circuit files
            result.region = 'CIRCUIT'
            result.series = 'WSOP_CIRCUIT'
            result.event_type = 'ME'
            result.day = extract_day(file.filename)
            # Extract suffix as part number
            suffix_match = re.search(r'-(\d+)\.mp4$', file.filename)
            if suffix_match:
                result.part = int(suffix_match.group(1))
        return result

    # Extract all elements for other patterns
    result.region = extract_region(file.full_path)
    result.series = extract_series(file.full_path or '', file.filename)
    result.event_type = extract_event_type(file.full_path or '', file.filename)
    result.event_num = extract_event_num(file.full_path or '', file.filename)
    result.day = extract_day(file.filename)
    result.part = extract_part(file.filename)
    result.session = extract_session(file.filename)  # v1.1
    result.cyprus_event = extract_cyprus_event(file.full_path or '', file.filename)  # v1.1
    result.source = extract_source(file.filename)
    result.version = extract_version(file.full_path or '', file.filename)
    result.resolution = extract_resolution(file.filename)

    # Handle sequence → part conversion (EU NC files)
    if result.pattern_id == 'P4' and result.part is None:
        seq = extract_sequence(file.filename)
        if seq:
            result.part = seq

    # Validate and collect issues
    if result.region == 'UNKNOWN':
        result.issues.append('Region: UNKNOWN')

    if result.event_type == 'OTHER' and not result.is_excluded:
        if result.region != 'CYPRUS_MPP':  # Cyprus MPP doesn't need event_type
            result.issues.append('Event Type: OTHER')

    if result.event_type == 'BR' and result.event_num is None and not result.is_excluded:
        if result.region != 'CYPRUS_MPP':  # Cyprus doesn't have event numbers
            result.issues.append('Event #: Missing for BR')

    if result.pattern_id == 'P0':
        result.issues.append('Pattern: Unclassified')

    return result


def generate_normalized_key(elem: NasFileNormalized) -> str:
    """Generate normalized unique key."""
    if elem.is_excluded:
        return f"EXCLUDED_{elem.pattern_id}"

    parts = [elem.region, elem.series]

    # Cyprus MPP: use event name for distinction (v1.1)
    if elem.region == 'CYPRUS_MPP' and elem.cyprus_event:
        parts.append(elem.cyprus_event)
    elif elem.event_type == 'BR':
        parts.append('BR')
        if elem.event_num:
            parts.append(f'E{elem.event_num}')
    elif elem.event_type == 'ME':
        parts.append('ME')
        if elem.event_num:  # EU Main Event has event_num
            parts.append(f'E{elem.event_num}')

    if elem.day:
        parts.append(f'D{elem.day}')

    # Session (Cyprus MPP Main Event) - v1.1
    if elem.session:
        parts.append(f'S{elem.session}')

    if elem.part:
        parts.append(f'P{elem.part}')

    if elem.version:
        parts.append(elem.version)

    # Raw file marker (HyperDeck) - v1.2
    if elem.is_raw:
        parts.append('RAW')

    return '_'.join(parts)


def assign_hyperdeck_parts(normalized: list) -> None:
    """Assign part numbers to HyperDeck files based on sequence within folder.

    Each folder (same Event + Day) represents one video split into parts.
    Parts are numbered by sorting on hd_sequence.
    """
    # Group HyperDeck files by base key (without RAW)
    hd_groups = defaultdict(list)
    for n in normalized:
        if n.is_raw:
            # Generate base key (without RAW suffix)
            base_key = f"{n.region}_{n.series}_{n.event_type}_E{n.event_num}_D{n.day}_{n.version}"
            hd_groups[base_key].append(n)

    # Sort each group and assign part numbers
    for base_key, files_list in hd_groups.items():
        # Sort by sequence number
        files_list.sort(key=lambda x: x.hd_sequence)
        # Assign part numbers (1-based)
        for i, f in enumerate(files_list, 1):
            f.part = i


def main():
    print('=' * 70)
    print('NAS 정규화 전략 검증 (2025 전체 파일)')
    print('=' * 70)

    db = next(get_db())
    files = db.query(NasFile).filter(NasFile.year == 2025).order_by(NasFile.full_path).all()

    print(f'\n총 파일 수: {len(files)}')

    # Normalize all files
    normalized = [normalize_file(f) for f in files]

    # Assign part numbers to HyperDeck files
    assign_hyperdeck_parts(normalized)

    # === Statistics ===
    print('\n' + '=' * 70)
    print('1. 패턴별 분류')
    print('=' * 70)

    pattern_counts = defaultdict(list)
    for n in normalized:
        pattern_counts[n.pattern_id].append(n)

    pattern_names = {
        'P1': 'WSOP Bracelet (LV)',
        'P2': 'WSOP Main Event (LV)',
        'P3': 'WSOPE Stream (EU)',
        'P4': 'WSOPE NC (EU)',
        'P5': 'Cyprus PokerOK/Luxon',
        'P6': 'WSOP Circuit (제외)',
        'P7': 'Cyprus MPP',
        'P8': 'HyperDeck RAW (EU)',
        'P9': 'Source Prefix',
        'P10': 'Date Prefix',
        'P0': 'Unclassified',
    }

    for pid in ['P1', 'P2', 'P3', 'P4', 'P5', 'P6', 'P7', 'P8', 'P9', 'P10', 'P0']:
        if pid in pattern_counts:
            print(f'  {pid}: {len(pattern_counts[pid]):3d} - {pattern_names.get(pid, "")}')

    # === Region Statistics ===
    print('\n' + '=' * 70)
    print('2. 지역별 분류')
    print('=' * 70)

    region_counts = defaultdict(int)
    for n in normalized:
        region_counts[n.region] += 1

    for region in ['LV', 'EU', 'CYPRUS_MPP', 'CIRCUIT', 'UNKNOWN']:
        if region in region_counts:
            print(f'  {region}: {region_counts[region]}')

    # === Event Type Statistics ===
    print('\n' + '=' * 70)
    print('3. 이벤트 타입별 분류')
    print('=' * 70)

    event_type_counts = defaultdict(int)
    for n in normalized:
        if not n.is_excluded:
            event_type_counts[n.event_type] += 1

    for et in ['BR', 'ME', 'OTHER']:
        if et in event_type_counts:
            print(f'  {et}: {event_type_counts[et]}')

    # === Issues ===
    print('\n' + '=' * 70)
    print('4. 문제 파일')
    print('=' * 70)

    files_with_issues = [n for n in normalized if n.issues and not n.is_excluded]

    if files_with_issues:
        print(f'\n  문제 파일 수: {len(files_with_issues)}')
        for n in files_with_issues:
            print(f'\n  [{n.pattern_id}] {n.filename}')
            print(f'       Path: {n.full_path}')
            print(f'       Issues: {", ".join(n.issues)}')
            print(f'       Extracted: region={n.region}, series={n.series}, event_type={n.event_type}, event_num={n.event_num}')
    else:
        print('\n  문제 파일 없음!')

    # === Excluded Files ===
    print('\n' + '=' * 70)
    print('5. 제외 파일')
    print('=' * 70)

    excluded = [n for n in normalized if n.is_excluded]
    exclusion_reasons = defaultdict(int)
    for n in excluded:
        exclusion_reasons[n.exclusion_reason] += 1

    print(f'\n  총 제외 파일: {len(excluded)}')
    for reason, count in exclusion_reasons.items():
        print(f'    - {reason}: {count}')

    # === Normalized Keys ===
    print('\n' + '=' * 70)
    print('6. 정규화 키 생성 결과')
    print('=' * 70)

    key_counts = defaultdict(list)
    for n in normalized:
        if not n.is_excluded:
            key = generate_normalized_key(n)
            key_counts[key].append(n)

    print(f'\n  고유 키 수: {len(key_counts)}')

    # Show keys with multiple files (potential grouping)
    multi_file_keys = {k: v for k, v in key_counts.items() if len(v) > 1}
    if multi_file_keys:
        print(f'\n  다중 파일 키 (동일 콘텐츠 그룹):')
        for key, files_list in sorted(multi_file_keys.items()):
            print(f'    {key}: {len(files_list)} files')
            for f in files_list[:3]:  # Show first 3
                print(f'      - {f.filename[:60]}...' if len(f.filename) > 60 else f'      - {f.filename}')
            if len(files_list) > 3:
                print(f'      ... and {len(files_list) - 3} more')

    # === Summary ===
    print('\n' + '=' * 70)
    print('7. 최종 요약')
    print('=' * 70)

    valid_files = [n for n in normalized if not n.is_excluded]
    classified_files = [n for n in valid_files if n.pattern_id != 'P0']
    no_issues_files = [n for n in valid_files if not n.issues]

    print(f'''
  전체 파일:     {len(normalized)}
  제외 파일:     {len(excluded)}
  유효 파일:     {len(valid_files)}

  패턴 분류됨:   {len(classified_files)} / {len(valid_files)} ({100*len(classified_files)//len(valid_files) if valid_files else 0}%)
  문제 없음:     {len(no_issues_files)} / {len(valid_files)} ({100*len(no_issues_files)//len(valid_files) if valid_files else 0}%)

  고유 Entry 키: {len(key_counts)}
''')

    # === Detailed Output by Pattern ===
    print('\n' + '=' * 70)
    print('8. 패턴별 상세 (샘플)')
    print('=' * 70)

    for pid in ['P1', 'P2', 'P3', 'P4', 'P5', 'P7']:
        if pid in pattern_counts:
            print(f'\n  === {pid}: {pattern_names.get(pid, "")} ===')
            samples = pattern_counts[pid][:3]
            for n in samples:
                key = generate_normalized_key(n)
                print(f'    File: {n.filename[:70]}{"..." if len(n.filename) > 70 else ""}')
                print(f'    Key:  {key}')
                print(f'    Elements: region={n.region}, event_type={n.event_type}, event_num={n.event_num}, day={n.day}, part={n.part}')
                print()


if __name__ == '__main__':
    main()

"""
NAS Asset Grouping System
=========================
동일 콘텐츠의 여러 포맷 파일을 그룹화하고 Primary/Backup 역할 지정

출력:
- data/asset_groups/index.json          # 마스터 인덱스
- data/asset_groups/groups.json         # 전체 그룹 데이터
- data/asset_groups/by_year/            # 연도별 청크
- Google Sheet: NAS-ASSET-GROUPS        # 관리용 시트
"""

import json
import re
import sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict
import gspread
from google.oauth2.service_account import Credentials

sys.stdout.reconfigure(encoding='utf-8')

# 경로 설정
DATA_DIR = Path("D:/AI/claude01/pokergo_crawling/data")
NAS_FILE = DATA_DIR / "sources/nas/nas_files.json"
POKERGO_FILE = DATA_DIR / "pokergo/episodes.json"
OUTPUT_DIR = DATA_DIR / "asset_groups"

# 설정
MIN_SIZE_GB = 1.0
NAS_BASE_PATH = r'\\10.10.100.122\ggpwsop\WSOP backup'

# Role 우선순위 (낮을수록 우선)
ROLE_PRIORITY = {
    '.mp4': 1,   # Primary (방송/배포용)
    '.mov': 2,   # Backup 1 (편집용)
    '.mxf': 3,   # Backup 2 (아카이브용)
    '.avi': 4,   # Backup 3 (레거시)
    '.mkv': 5,   # Backup 4
    '.wmv': 6,   # Backup 5
    '.m4v': 7,   # Backup 6
}

# Google Sheets 연결
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
creds = Credentials.from_service_account_file(
    'D:/AI/claude01/json/service_account_key.json',
    scopes=SCOPES
)
gc = gspread.authorize(creds)
SHEET_ID = '1h27Ha7pR-iYK_Gik8F4FfSvsk4s89sxk49CsU3XP_m4'


def extract_year_from_text(text):
    """Extract year from text, excluding PRE-XXXX patterns."""
    text = str(text)
    cleaned = re.sub(r'PRE-\d{4}', '', text, flags=re.IGNORECASE)
    match = re.search(r'(19|20)\d{2}', cleaned)
    return match.group(0) if match else None


def extract_wsop_code_info(text, directory=""):
    """
    Extract info from WSOP file code pattern.
    Returns: (year, region, event_type, episode) or (None, None, None, None)

    Priority patterns (P0-P10):
    - P0: WSOP{YY}_APAC_*
    - P1: WS{YY}_{TYPE}{EP}
    - P2: WSOP{YY}_{TYPE}{EP}
    - P3: WSOP_{YYYY}_{SEQ}_{TYPE}{EP}
    - P4: WSOPE{YY}_Episode_{EP}
    - P5: {YYYY} World Series...Main Event Show
    - P6: {YYYY} WSOP Show ME
    - P7: WSOP {YYYY} Show ME
    - P8: {YYYY} WSOP ME{##}
    - P9: wsop-{yyyy}-me-*
    - P10: Folder year + filename parsing
    """
    text_upper = str(text).upper()
    dir_upper = str(directory).upper()

    # Event type code map
    type_map = {
        'ME': 'main_event',
        'GM': 'grudge_match',
        'HU': 'heads_up',
        'BR': 'bracelet',
    }

    # P0: WSOP{YY}_APAC_* (Asia Pacific)
    m = re.match(r'WSOP(\d{2})[_\-]APAC[_\-]([A-Z_]+?)[_\-]?(?:SHOW\s*)?(\d+)', text_upper)
    if m:
        y = int(m.group(1))
        year = f"20{y:02d}" if y <= 30 else f"19{y:02d}"
        event = m.group(2).replace('_', ' ').strip()
        if 'ME' in event or 'MAIN' in event:
            event_type = 'main_event'
        elif 'HIGH' in event:
            event_type = 'high_roller'
        else:
            event_type = event.lower()
        episode = int(m.group(3))
        return year, 'APAC', event_type, episode

    # P1: WS{YY}_{TYPE}{EP}
    m = re.match(r'WS(\d{2})[_\-]([A-Z]{2})(\d{1,2})', text_upper)
    if m:
        y = int(m.group(1))
        year = f"20{y:02d}" if y <= 30 else f"19{y:02d}"
        event_type = type_map.get(m.group(2), m.group(2).lower())
        episode = int(m.group(3))
        return year, None, event_type, episode

    # P2: WSOP{YY}_{TYPE}{EP}
    m = re.match(r'WSOP(\d{2})[_\-]([A-Z]{2})(\d{1,2})', text_upper)
    if m:
        y = int(m.group(1))
        year = f"20{y:02d}" if y <= 30 else f"19{y:02d}"
        event_type = type_map.get(m.group(2), m.group(2).lower())
        episode = int(m.group(3))
        return year, None, event_type, episode

    # P3: WSOP_{YYYY}_{SEQ}_{TYPE}{EP}
    m = re.match(r'WSOP[_\-](\d{4})[_\-]\d+[_\-]([A-Z]{2})(\d{1,2})', text_upper)
    if m:
        year = m.group(1)
        event_type = type_map.get(m.group(2), m.group(2).lower())
        episode = int(m.group(3))
        return year, None, event_type, episode

    # P4: WSOPE{YY}_Episode_{EP}
    m = re.search(r'WSOPE(\d{2})[_\-]?(?:EPISODE)?[_\-]?(\d+)', text_upper)
    if m:
        y = int(m.group(1))
        year = f"20{y:02d}" if y <= 30 else f"19{y:02d}"
        episode = int(m.group(2))
        return year, 'EU', 'main_event', episode

    # P5: {YYYY} World Series... Main Event Show {##}
    m = re.match(r'(\d{4})\s+WORLD\s+SERIES.*?MAIN\s*EVENT.*?SHOW\s*(\d+)', text_upper)
    if m:
        year = m.group(1)
        episode = int(m.group(2))
        return year, None, 'main_event', episode

    # P6: {YYYY} WSOP Show {##} ME {##}
    m = re.match(r'(\d{4})\s+WSOP.*?SHOW\s*\d+.*?ME\s*(\d+)', text_upper)
    if m:
        year = m.group(1)
        episode = int(m.group(2))
        return year, None, 'main_event', episode

    # P7: WSOP {YYYY} Show {##} ME {##}
    m = re.match(r'WSOP\s+(\d{4}).*?SHOW\s*\d+.*?ME\s*(\d+)', text_upper)
    if m:
        year = m.group(1)
        episode = int(m.group(2))
        return year, None, 'main_event', episode

    # P8: {YYYY} WSOP ME{##}
    m = re.match(r'(\d{4})\s+WSOP\s+ME(\d+)', text_upper)
    if m:
        year = m.group(1)
        episode = int(m.group(2))
        return year, None, 'main_event', episode

    # P9-A: WSOP_{YYYY}-{EP} 또는 WSOP_{YYYY}_{EP} (에피소드 번호 포맷)
    # 혼합 구분자 지원: WSOP_2003-01, WSOP_2003_01, WSOP-2003-01
    m = re.match(r'WSOP[_\-](\d{4})[_\-](\d{1,2})(?:\.|_|\s|$)', text_upper)
    if m:
        year = m.group(1)
        episode = int(m.group(2))
        return year, None, 'main_event', episode

    # P9-B: Best Of 콘텐츠 타입 (P9보다 먼저!)
    if 'BEST OF' in text_upper or 'BEST_OF' in text_upper:
        year_m = re.search(r'(19|20)\d{2}', text_upper + ' ' + dir_upper)
        if year_m:
            year = year_m.group(0)
            # Best Of 세부 타입 추출
            if 'ALL' in text_upper and 'IN' in text_upper:
                return year, None, 'best_of_allins', None
            elif 'BLUFF' in text_upper:
                return year, None, 'best_of_bluffs', None
            elif 'MONEYMAKER' in text_upper:
                return year, None, 'best_of_moneymaker', None
            return year, None, 'best_of', None

    # P9-C: Final Table 콘텐츠 타입 (P9보다 먼저!)
    if 'FINAL TABLE' in text_upper or 'FINAL_TABLE' in text_upper:
        year_m = re.search(r'(19|20)\d{2}', text_upper + ' ' + dir_upper)
        if year_m:
            year = year_m.group(0)
            return year, None, 'final_table', None

    # P9: wsop-{yyyy}-me-* or wsope-{yyyy}-*
    m = re.match(r'WSOPE?[-_](\d{4})[-_]', text_upper)
    if m:
        year = m.group(1)
        region = 'EU' if 'WSOPE' in text_upper else None
        event_type = 'main_event' if 'ME' in text_upper else None
        return year, region, event_type, None

    # P10-A: PARADISE 지역 (바하마)
    if 'PARADISE' in text_upper or 'PARADISE' in dir_upper:
        year_m = re.search(r'(20\d{2})', text_upper + ' ' + dir_upper)
        if year_m:
            year = year_m.group(1)
            # Day 추출 (에피소드 대체)
            day_m = re.search(r'DAY\s*(\d+[A-D]?)', text_upper)
            if day_m:
                day_str = day_m.group(1)
                # Day 1A, 1B 등 → 숫자로 변환
                day_num = int(re.match(r'\d+', day_str).group())
                return year, 'PARADISE', 'main_event', day_num
            # Final Day/Table
            if 'FINAL' in text_upper:
                return year, 'PARADISE', 'main_event', 99  # Final = 99
            return year, 'PARADISE', None, None

    # P10: Folder year extraction + filename parsing
    dir_year_match = re.search(r'WSOP\s*(\d{4})', dir_upper)
    if dir_year_match:
        year = dir_year_match.group(1)
        region = 'EU' if 'EUROPE' in dir_upper or 'WSOPE' in text_upper else None

        # Detect event type from filename
        event_type = None
        if 'MAIN' in text_upper and 'EVENT' in text_upper:
            event_type = 'main_event'
        elif ' ME' in text_upper or '_ME' in text_upper or text_upper.startswith('ME'):
            event_type = 'main_event'
        elif 'BRACELET' in text_upper:
            event_type = 'bracelet'
        elif 'HIGH' in text_upper and 'ROLLER' in text_upper:
            event_type = 'high_roller'

        # Extract episode
        episode = None
        ep_m = re.search(r'(?:SHOW|EPISODE|EP)[_\s]*(\d+)', text_upper)
        if ep_m:
            episode = int(ep_m.group(1))
        else:
            ep_m = re.search(r'ME\s*(\d+)', text_upper)
            if ep_m:
                episode = int(ep_m.group(1))

        return year, region, event_type, episode

    # Fallback: Extract year from filename
    m = re.search(r'(\d{4})', text_upper)
    if m:
        year = int(m.group(1))
        if 1970 <= year <= 2030:
            region = 'EU' if 'WSOPE' in text_upper or 'EUROPE' in dir_upper else None
            return str(year), region, None, None

    return None, None, None, None


def extract_event_info_from_path(filename, directory):
    """
    Extract event info from filename and directory.
    Returns: (year, region, event_type, episode)
    """
    # Use the comprehensive pattern matcher
    return extract_wsop_code_info(filename, directory)


def generate_group_id(year, region, event_type, episode):
    """Generate group ID from components.

    Format: {year}_{region-}{type}_{episode}
    Examples:
    - 2011_ME_25 = WSOP 2011 Main Event Episode 25
    - 2013_APAC-ME_01 = WSOP APAC 2013 Main Event Episode 1
    - 2011_EU_01 = WSOP Europe 2011 Episode 1
    """
    if not year:
        return None

    event_abbrev = {
        'main_event': 'ME',
        'grudge_match': 'GM',
        'heads_up': 'HU',
        'bracelet': 'BR',
        'high_roller': 'HR',
        'best_of': 'BEST',
        'best_of_allins': 'BEST-ALLINS',
        'best_of_bluffs': 'BEST-BLUFFS',
        'best_of_moneymaker': 'BEST-MM',
        'final_table': 'FT',
    }

    # Build type abbreviation
    if region == 'APAC':
        abbrev = f"APAC-{event_abbrev.get(event_type, event_type.upper() if event_type else 'UNK')}"
    elif region == 'EU':
        abbrev = 'EU'
    elif region == 'PARADISE':
        abbrev = f"PARADISE-{event_abbrev.get(event_type, event_type.upper() if event_type else 'UNK')}"
    else:
        abbrev = event_abbrev.get(event_type, event_type.upper() if event_type else 'UNK')

    if episode:
        return f"{year}_{abbrev}_{episode:02d}"
    else:
        return f"{year}_{abbrev}"


def load_pokergo_index():
    """Load PokerGO episodes and build index."""
    with open(POKERGO_FILE, 'r', encoding='utf-8') as f:
        pokergo_data = json.load(f)

    # Filter WSOP episodes with proper titles
    pokergo_eps = [ep for ep in pokergo_data.get('episodes', [])
                   if 'WSOP' in ep.get('collection_title', '')
                   and '|' in ep.get('title', '')]

    # Build index by (year, event_type, episode)
    index = {}
    for ep in pokergo_eps:
        title = ep.get('title', '')
        year = extract_year_from_text(title)

        # Determine event type from title/season
        event_type = None
        title_lower = title.lower()
        season_lower = ep.get('season_title', '').lower()

        if 'main event' in title_lower or 'main event' in season_lower:
            event_type = 'main_event'
        elif 'grudge' in title_lower or 'grudge' in season_lower:
            event_type = 'grudge_match'
        elif 'heads-up' in title_lower or 'heads up' in season_lower:
            event_type = 'heads_up'
        elif 'bracelet' in title_lower or 'bracelet' in season_lower:
            event_type = 'bracelet'

        # Extract episode number
        ep_match = re.search(r'Episode\s*(\d+)', title)
        episode = int(ep_match.group(1)) if ep_match else None

        if year:
            group_id = generate_group_id(year, None, event_type, episode)
            if group_id and group_id not in index:
                index[group_id] = {
                    'title': title,
                    'collection': ep.get('collection_title', ''),
                    'season': ep.get('season_title', ''),
                    'duration_min': ep.get('duration_min', 0)
                }

    return index


def process_nas_files():
    """Process NAS files and create asset groups.

    백업 파일 조건 (아래 중 하나라도 충족):
    - 조건 A: 파일명 동일 (확장자만 다름) + 크기 동일
    - 조건 B: 분석 결과 동일 (연도+대회+이벤트+에피소드 = Group ID)
    """
    print("NAS 데이터 로딩...")
    with open(NAS_FILE, 'r', encoding='utf-8') as f:
        nas_data = json.load(f)
    nas_files = nas_data.get('files', [])
    print(f"  전체 파일: {len(nas_files)}개")

    print("PokerGO 인덱스 로딩...")
    pokergo_index = load_pokergo_index()
    print(f"  인덱스 항목: {len(pokergo_index)}개")

    # Group files by group_id (연도+대회+이벤트+에피소드)
    # 조건 B: 분석 결과가 동일하면 같은 콘텐츠로 백업 처리
    groups = defaultdict(list)
    ungrouped = []
    excluded = {'small': 0, 'clip': 0, 'non_wsop': 0}

    for f in nas_files:
        filename = f.get('filename', '')
        directory = f.get('directory', '')
        rel_path = f.get('relative_path', '')
        size_bytes = f.get('size_bytes', 0)
        size_gb = size_bytes / (1024**3)
        extension = Path(filename).suffix.lower()
        base_name = Path(filename).stem  # 확장자 제외 파일명
        origin = f'{NAS_BASE_PATH}\\{rel_path}' if rel_path else ''

        # Skip small files
        if size_gb < MIN_SIZE_GB:
            excluded['small'] += 1
            continue

        # Skip clip/circuit (PARADISE는 포함!)
        combined_lower = f"{filename} {directory}".lower()
        if 'clip' in combined_lower or 'circuit' in combined_lower:
            excluded['clip'] += 1
            continue

        # Check WSOP
        if 'WSOP' not in f"{filename} {directory}".upper():
            excluded['non_wsop'] += 1
            continue

        # Extract event info (for Group ID)
        year, region, event_type, episode = extract_event_info_from_path(filename, directory)
        group_id = generate_group_id(year, region, event_type, episode)

        file_info = {
            'filename': filename,
            'base_name': base_name,
            'extension': extension,
            'size_bytes': size_bytes,
            'size_gb': round(size_gb, 2),
            'origin': origin,
            'directory': directory,
            'relative_path': rel_path,
            'year': year,
            'region': region,
            'event_type': event_type,
            'episode': episode,
            'group_id': group_id,
            'priority': ROLE_PRIORITY.get(extension, 99)
        }

        # 그룹화 규칙: Group ID (연도+대회+이벤트+에피소드) 기반
        if group_id:
            groups[group_id].append(file_info)
        else:
            ungrouped.append(file_info)

    print(f"  제외: 1GB미만 {excluded['small']}, Clip등 {excluded['clip']}, Non-WSOP {excluded['non_wsop']}")
    print(f"  그룹화: {len(groups)}개 그룹, 미분류: {len(ungrouped)}개")

    # Process groups - assign roles
    asset_groups = []

    event_type_map = {
        'ME': 'Main Event',
        'GM': 'Grudge Match',
        'HU': 'Heads Up',
        'BR': 'Bracelet',
        'HR': 'High Roller',
        'EU': 'Europe',
        'FT': 'Final Table',
        'BEST': 'Best Of',
        'BEST-ALLINS': 'Best Of All-Ins',
        'BEST-BLUFFS': 'Best Of Bluffs',
        'BEST-MM': 'Best Of Moneymaker',
        'APAC-ME': 'APAC Main Event',
        'APAC-HR': 'APAC High Roller',
        'APAC-UNK': 'APAC Unknown',
        'PARADISE-ME': 'Paradise Main Event',
        'PARADISE-UNK': 'Paradise Unknown',
    }

    event_abbrev_map = {
        'main_event': 'ME',
        'grudge_match': 'GM',
        'heads_up': 'HU',
        'bracelet': 'BR',
        'high_roller': 'HR',
        'europe': 'EU',
        'final_table': 'FT',
        'best_of': 'BEST',
        'best_of_allins': 'BEST-ALLINS',
        'best_of_bluffs': 'BEST-BLUFFS',
        'best_of_moneymaker': 'BEST-MM',
    }

    for group_id, files in sorted(groups.items()):
        # Sort by priority (lowest first = primary)
        files_sorted = sorted(files, key=lambda x: x['priority'])

        primary = files_sorted[0]
        backups = files_sorted[1:] if len(files_sorted) > 1 else []

        # Get PokerGO match
        pokergo_match = pokergo_index.get(group_id, {})

        # Parse group_id for metadata
        parts = group_id.split('_')
        year = parts[0] if len(parts) > 0 else ''
        event_abbrev = parts[1] if len(parts) > 1 else 'UNK'
        episode = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else None

        group_data = {
            'group_id': group_id,
            'year': year,
            'event_type': event_type_map.get(event_abbrev, event_abbrev),
            'event_abbrev': event_abbrev,
            'episode': episode,
            'pokergo_match': pokergo_match,
            'has_pokergo_match': bool(pokergo_match),
            'primary': {
                'filename': primary['filename'],
                'extension': primary['extension'],
                'size_gb': primary['size_gb'],
                'size_bytes': primary['size_bytes'],
                'origin': primary['origin'],
                'directory': primary['directory']
            },
            'backups': [
                {
                    'filename': b['filename'],
                    'extension': b['extension'],
                    'size_gb': b['size_gb'],
                    'size_bytes': b['size_bytes'],
                    'origin': b['origin'],
                    'directory': b['directory']
                }
                for b in backups
            ],
            'stats': {
                'file_count': len(files_sorted),
                'total_size_gb': round(sum(f['size_gb'] for f in files_sorted), 2),
                'has_backup': len(backups) > 0
            }
        }

        asset_groups.append(group_data)

    return asset_groups, ungrouped, excluded


def save_json_output(asset_groups, ungrouped):
    """Save JSON outputs."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Full groups data
    full_data = {
        'created_at': datetime.now().isoformat(),
        'version': '1.0',
        'stats': {
            'total_groups': len(asset_groups),
            'groups_with_backup': sum(1 for g in asset_groups if g['stats']['has_backup']),
            'groups_with_pokergo': sum(1 for g in asset_groups if g['has_pokergo_match']),
            'total_files': sum(g['stats']['file_count'] for g in asset_groups),
            'total_size_gb': round(sum(g['stats']['total_size_gb'] for g in asset_groups), 2),
            'ungrouped_files': len(ungrouped)
        },
        'groups': asset_groups,
        'ungrouped': ungrouped
    }

    with open(OUTPUT_DIR / "groups.json", 'w', encoding='utf-8') as f:
        json.dump(full_data, f, ensure_ascii=False, indent=2)

    # Index (lightweight)
    index_data = {
        'created_at': datetime.now().isoformat(),
        'stats': full_data['stats'],
        'groups': [
            {
                'group_id': g['group_id'],
                'year': g['year'],
                'event_type': g['event_type'],
                'episode': g['episode'],
                'file_count': g['stats']['file_count'],
                'has_pokergo': g['has_pokergo_match'],
                'primary_ext': g['primary']['extension']
            }
            for g in asset_groups
        ]
    }

    with open(OUTPUT_DIR / "index.json", 'w', encoding='utf-8') as f:
        json.dump(index_data, f, ensure_ascii=False, indent=2)

    # By year chunks
    by_year_dir = OUTPUT_DIR / "by_year"
    by_year_dir.mkdir(exist_ok=True)

    by_year = defaultdict(list)
    for g in asset_groups:
        by_year[g['year']].append(g)

    for year, groups in by_year.items():
        with open(by_year_dir / f"{year}.json", 'w', encoding='utf-8') as f:
            json.dump({
                'year': year,
                'count': len(groups),
                'groups': groups
            }, f, ensure_ascii=False, indent=2)

    print(f"  groups.json: {(OUTPUT_DIR / 'groups.json').stat().st_size / 1024:.1f} KB")
    print(f"  index.json: {(OUTPUT_DIR / 'index.json').stat().st_size / 1024:.1f} KB")
    print(f"  by_year/: {len(by_year)}개 파일")

    return full_data['stats']


def update_google_sheet(asset_groups, ungrouped):
    """Update Google Sheet with asset groups."""
    print("Google Sheet 업데이트...")

    sheet = gc.open_by_key(SHEET_ID)

    # Check if sheet exists
    try:
        ws = sheet.worksheet('NAS-ASSET-GROUPS')
        ws.clear()
        print("  기존 시트 초기화")
    except:
        ws = sheet.add_worksheet('NAS-ASSET-GROUPS', rows=2000, cols=15)
        print("  새 시트 생성")

    # Prepare rows
    headers = [
        'Group_ID', 'Year', 'Event_Type', 'Episode',
        'Role', 'Filename', 'Extension', 'Size(GB)',
        'Origin', 'PokerGO Title', 'Has_Backup', 'File_Count'
    ]

    rows = [headers]

    for g in asset_groups:
        # Primary row
        rows.append([
            g['group_id'],
            g['year'],
            g['event_type'],
            g['episode'] or '',
            'Primary',
            g['primary']['filename'],
            g['primary']['extension'],
            g['primary']['size_gb'],
            g['primary']['origin'],
            g['pokergo_match'].get('title', ''),
            'Yes' if g['stats']['has_backup'] else 'No',
            g['stats']['file_count']
        ])

        # Backup rows
        for i, backup in enumerate(g['backups']):
            rows.append([
                g['group_id'],
                g['year'],
                g['event_type'],
                g['episode'] or '',
                f'Backup {i+1}',
                backup['filename'],
                backup['extension'],
                backup['size_gb'],
                backup['origin'],
                '',  # PokerGO title only on primary
                '',
                ''
            ])

    # Add ungrouped files
    if ungrouped:
        rows.append([''] * len(headers))  # Empty row separator
        rows.append(['=== UNGROUPED FILES ==='] + [''] * (len(headers) - 1))

        for f in ungrouped:
            rows.append([
                'UNGROUPED',
                f.get('year', ''),
                f.get('event_type', ''),
                f.get('episode', ''),
                'Unknown',
                f['filename'],
                f['extension'],
                f['size_gb'],
                f['origin'],
                '',
                '',
                ''
            ])

    # Upload
    print(f"  업로드 중... ({len(rows)-1}개 행)")
    ws.update(values=rows, range_name='A1')

    # Format header row
    ws.format('A1:L1', {
        'backgroundColor': {'red': 0.2, 'green': 0.4, 'blue': 0.6},
        'textFormat': {'bold': True, 'foregroundColor': {'red': 1, 'green': 1, 'blue': 1}}
    })

    # Highlight Primary rows
    worksheet_id = ws.id
    requests = [
        {
            "addConditionalFormatRule": {
                "rule": {
                    "ranges": [{"sheetId": worksheet_id, "startRowIndex": 1, "endRowIndex": len(rows)}],
                    "booleanRule": {
                        "condition": {
                            "type": "TEXT_EQ",
                            "values": [{"userEnteredValue": "Primary"}]
                        },
                        "format": {
                            "backgroundColor": {"red": 0.85, "green": 0.92, "blue": 0.83}
                        }
                    }
                },
                "index": 0
            }
        }
    ]

    try:
        sheet.batch_update({"requests": requests})
    except Exception as e:
        print(f"  조건부 서식 적용 실패: {e}")

    return len(rows) - 1


def main():
    print("=" * 60)
    print("NAS Asset Grouping System")
    print("=" * 60)

    # Process files
    print("\n[1/3] NAS 파일 그룹화...")
    asset_groups, ungrouped, excluded = process_nas_files()

    # Save JSON
    print("\n[2/3] JSON 저장...")
    stats = save_json_output(asset_groups, ungrouped)

    # Update Sheet
    print("\n[3/3] Google Sheet 업데이트...")
    row_count = update_google_sheet(asset_groups, ungrouped)

    # Summary
    print("\n" + "=" * 60)
    print("완료")
    print("=" * 60)

    print(f"\n[통계]")
    print(f"  총 그룹: {stats['total_groups']}개")
    print(f"  백업 있는 그룹: {stats['groups_with_backup']}개")
    print(f"  PokerGO 매칭: {stats['groups_with_pokergo']}개")
    print(f"  총 파일: {stats['total_files']}개")
    print(f"  총 용량: {stats['total_size_gb']:.1f} GB")
    print(f"  미분류: {stats['ungrouped_files']}개")

    print(f"\n[출력]")
    print(f"  JSON: {OUTPUT_DIR}")
    print(f"  Sheet: NAS-ASSET-GROUPS ({row_count}행)")


if __name__ == "__main__":
    main()

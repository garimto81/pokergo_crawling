"""Create NAS-POKERGO sheet with matching information."""
import json
import sys
import re
import gspread
from google.oauth2.service_account import Credentials
from difflib import SequenceMatcher

sys.stdout.reconfigure(encoding='utf-8')

# Google Sheets 연결
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
creds = Credentials.from_service_account_file(
    'D:/AI/claude01/json/service_account_key.json',
    scopes=SCOPES
)
gc = gspread.authorize(creds)
sheet = gc.open_by_key('1h27Ha7pR-iYK_Gik8F4FfSvsk4s89sxk49CsU3XP_m4')

# Check if sheet exists
print('기존 시트 확인...')
existing_sheet = None
try:
    existing_sheet = sheet.worksheet('NAS-POKERGO')
    print('  기존 NAS-POKERGO 시트 발견')
except:
    print('  기존 시트 없음')

# Load NAS data
print('NAS 데이터 로딩...')
with open('data/sources/nas/nas_files.json', 'r', encoding='utf-8') as f:
    nas_data = json.load(f)
nas_files = nas_data.get('files', [])
print(f'NAS 전체 파일: {len(nas_files)}개')

# Load PokerGO data (WSOP only, exclude category pages)
print('PokerGO 데이터 로딩 (WSOP only)...')
with open('data/pokergo/episodes.json', 'r', encoding='utf-8') as f:
    pokergo_data = json.load(f)

# Filter: WSOP collection AND exclude category pages (title without "|" = no episode info)
pokergo_all = [ep for ep in pokergo_data.get('episodes', [])
               if 'WSOP' in ep.get('collection_title', '')]
pokergo_eps = [ep for ep in pokergo_all
               if '|' in ep.get('title', '')]  # Must have "|" for episode detail
category_count = len(pokergo_all) - len(pokergo_eps)
print(f'PokerGO WSOP 에피소드: {len(pokergo_eps)}개 (카테고리 페이지 {category_count}개 제외)')


# Helper functions
def extract_year_from_text(text):
    """Extract year from text, excluding PRE-XXXX patterns."""
    text = str(text)
    # Remove PRE-XXXX patterns first
    cleaned = re.sub(r'PRE-\d{4}', '', text, flags=re.IGNORECASE)
    match = re.search(r'(19|20)\d{2}', cleaned)
    return match.group(0) if match else None


def extract_year_smart(filename, directory, rel_path):
    """
    Smart year extraction with priority:
    1. Filename (most reliable)
    2. Immediate directory name
    3. Full path (excluding PRE-XXXX)
    """
    # Priority 1: Filename
    year = extract_year_from_text(filename)
    if year:
        return year, 'filename'

    # Priority 2: Immediate directory (last folder)
    if directory:
        last_folder = directory.split('\\')[-1] if '\\' in directory else directory
        year = extract_year_from_text(last_folder)
        if year:
            return year, 'directory'

    # Priority 3: Full path (excluding PRE-XXXX)
    year = extract_year_from_text(rel_path)
    if year:
        return year, 'path'

    return None, None


def extract_event_number(text):
    match = re.search(r'[Ee]vent\s*#?\s*(\d+)', str(text))
    return int(match.group(1)) if match else None


def extract_episode_number(text):
    match = re.search(r'[Ee]pisode\s*(\d+)', str(text))
    return int(match.group(1)) if match else None


def normalize_text(text):
    text = str(text).lower()
    text = re.sub(r'[^a-z0-9\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def text_similarity(a, b):
    return SequenceMatcher(None, normalize_text(a), normalize_text(b)).ratio()


def has_wsop(filename, directory):
    """Check if WSOP exists in filename or directory."""
    combined = f"{filename} {directory}".upper()
    return 'WSOP' in combined


def extract_event_type(text):
    """
    Extract WSOP event type from text.
    Returns: 'main_event', 'bracelet', 'paradise', 'europe', or None
    """
    text_lower = str(text).lower()
    text_upper = str(text).upper()

    # Check specific event types (order matters - more specific first)
    if 'paradise' in text_lower:
        return 'paradise'
    if 'europe' in text_lower:
        return 'europe'
    if 'main event' in text_lower or 'main-event' in text_lower or 'mainevent' in text_lower:
        return 'main_event'
    # Check for ME pattern (WS11_ME01, ME01, _ME_, -ME-)
    if re.search(r'[_\-]ME\d{1,2}|[_\-]ME[_\-]', text_upper):
        return 'main_event'
    if 'bracelet' in text_lower:
        return 'bracelet'

    return None


def extract_wsop_code_info(text):
    """
    Extract info from WSOP file code pattern.
    Returns: (year, event_type, episode) or (None, None, None)

    Patterns:
    - WS11_ME01 = WSOP 2011 Main Event Episode 1 (WS + 2-digit year)
    - WSOP13_ME01 = WSOP 2013 Main Event Episode 1 (WSOP + 2-digit year)
    - ME = Main Event
    - Number after ME = Episode number
    """
    text_upper = str(text).upper()

    # Pattern 1: WS + 2-digit year (WS11, WS24, etc.)
    ws_match = re.search(r'WS(\d{2})[_\-]', text_upper)
    if ws_match:
        year_2digit = int(ws_match.group(1))
        # Convert 2-digit to 4-digit year (00-30 = 2000-2030, 31-99 = 1931-1999)
        if year_2digit <= 30:
            year = f"20{year_2digit:02d}"
        else:
            year = f"19{year_2digit:02d}"

        # Check for ME (Main Event) + episode number
        me_match = re.search(r'ME(\d{1,2})', text_upper)
        if me_match:
            episode = int(me_match.group(1))
            return year, 'main_event', episode

        return year, None, None

    # Pattern 2: WSOP + 2-digit year (WSOP13, WSOP14, WSOP15, etc.)
    wsop_match = re.search(r'WSOP(\d{2})[_\-]', text_upper)
    if wsop_match:
        year_2digit = int(wsop_match.group(1))
        # Convert 2-digit to 4-digit year (00-30 = 2000-2030, 31-99 = 1931-1999)
        if year_2digit <= 30:
            year = f"20{year_2digit:02d}"
        else:
            year = f"19{year_2digit:02d}"

        # Check for ME (Main Event) + episode number
        me_match = re.search(r'ME(\d{1,2})', text_upper)
        if me_match:
            episode = int(me_match.group(1))
            return year, 'main_event', episode

        # Check for APAC (Asia Pacific) pattern
        if 'APAC' in text_upper:
            me_match = re.search(r'ME(\d{1,2})', text_upper)
            if me_match:
                episode = int(me_match.group(1))
                return year, 'main_event', episode

        return year, None, None

    return None, None, None


def event_types_compatible(nas_type, pokergo_type):
    """
    Check if NAS and PokerGO event types are compatible for matching.
    """
    # If NAS has no specific type, allow any match
    if nas_type is None:
        return True

    # If PokerGO has no specific type, allow any match
    if pokergo_type is None:
        return True

    # Types must match
    return nas_type == pokergo_type


def parse_collection(collection_title):
    """
    Parse collection title into components.
    'WSOP 2024' → (Series: 'WSOP', Year: '2024')
    'WSOP | World Series of Poker' → (Series: 'WSOP', Year: '')
    """
    if not collection_title:
        return '', ''

    if '|' in collection_title:
        # Meta collection: 'WSOP | World Series of Poker'
        parts = collection_title.split('|')
        series = parts[0].strip()
        return series, ''
    else:
        # Year collection: 'WSOP 2024'
        m = re.match(r'(WSOP)\s*(\d{4})?', collection_title)
        if m:
            series = m.group(1)
            year = m.group(2) or ''
            return series, year
        return collection_title, ''


def parse_season(season_title):
    """
    Parse season title into components.
    'WSOP 2024 Main Event' → (Year: '2024', EventType: 'Main Event', ContentType: '')
    'WSOP 2024 Main Event | Episodes' → (Year: '2024', EventType: 'Main Event', ContentType: 'Episodes')
    'WSOP 2024 Bracelet Events | Livestreams' → (Year: '2024', EventType: 'Bracelet Events', ContentType: 'Livestreams')
    """
    if not season_title:
        return '', '', ''

    # Split by '|' for content type
    if '|' in season_title:
        main_part, content_type = season_title.split('|', 1)
        content_type = content_type.strip()
    else:
        main_part = season_title
        content_type = ''

    # Parse main part: 'WSOP 2024 Main Event'
    m = re.match(r'WSOP\s*(\d{4})?\s*(.*)', main_part.strip())
    if m:
        year = m.group(1) or ''
        event_type = m.group(2).strip()
        return year, event_type, content_type

    return '', main_part.strip(), content_type


# Build PokerGO index for matching
print('PokerGO 인덱스 생성...')
pokergo_index = {}  # (year, event, episode) -> list
pokergo_by_year = {}  # year -> list of episodes

for ep in pokergo_eps:
    title = ep.get('title', '')
    year = extract_year_from_text(title)
    event_num = extract_event_number(title)
    ep_num = extract_episode_number(title)
    event_type = extract_event_type(title)

    # Parse collection and season
    collection_title = ep.get('collection_title', '')
    season_title = ep.get('season_title', '')
    col_series, col_year = parse_collection(collection_title)
    season_year, season_event_type, season_content_type = parse_season(season_title)

    ep_data = {
        'title': title,
        'year': year,
        'event_type': event_type,
        'collection': collection_title,
        'season': season_title,
        # Parsed fields
        'series': col_series,
        'pg_year': season_year or col_year,  # Prefer season year
        'pg_event_type': season_event_type,
        'pg_content_type': season_content_type,
        'duration_min': ep.get('duration_min', 0)
    }

    # Index by (year, event, episode)
    key = (year, event_num, ep_num)
    if key not in pokergo_index:
        pokergo_index[key] = []
    pokergo_index[key].append(ep_data)

    # Index by year only
    if year:
        if year not in pokergo_by_year:
            pokergo_by_year[year] = []
        pokergo_by_year[year].append(ep_data)

print(f'  PokerGO 연도 범위: {min(pokergo_by_year.keys())} ~ {max(pokergo_by_year.keys())}')

# Match NAS with PokerGO
print('NAS-PokerGO 매칭 진행...')
nas_with_matching = []
matched_count = 0
wsop_count = 0
non_wsop_count = 0
no_year_in_pokergo = 0
small_file_count = 0
clip_file_count = 0
ws_code_match_count = 0  # WS코드 패턴 매칭 카운트

MIN_SIZE_GB = 1.0  # 1GB 미만 파일 제외
NAS_BASE_PATH = r'\\10.10.100.122\ggpwsop\WSOP backup'

for f in nas_files:
    filename = f.get('filename', '')
    directory = f.get('directory', '')
    rel_path = f.get('relative_path', '')
    size_gb = f.get('size_bytes', 0) / (1024**3)
    origin = f'{NAS_BASE_PATH}\\{rel_path}' if rel_path else ''

    # Skip files smaller than 1GB
    if size_gb < MIN_SIZE_GB:
        small_file_count += 1
        continue

    # Skip files containing "clip", "circuit", or "paradise" (excluded content)
    combined_lower = f"{filename} {directory}".lower()
    if 'clip' in combined_lower or 'circuit' in combined_lower or 'paradise' in combined_lower:
        clip_file_count += 1
        continue

    # Check WSOP in filename OR directory
    is_wsop = has_wsop(filename, directory)

    # Extract info from NAS (use both filename and directory)
    combined_text = f"{filename} {directory}"

    # Try WSOP code pattern first (WS11_ME01_NB.mp4)
    code_year, code_event_type, code_episode = extract_wsop_code_info(filename)

    is_ws_code_pattern = False
    is_ws_code_unknown = False  # WS code but not ME (GM, HU, etc.)
    if code_year and code_event_type == 'main_event' and code_episode:
        # Use code-extracted info (high confidence) - ONLY for Main Event with episode
        nas_year = code_year
        nas_event_type = code_event_type
        nas_episode = code_episode
        nas_event = None  # Event number not in code pattern
        is_ws_code_pattern = True
        ws_code_match_count += 1
    elif code_year:
        # WS code pattern found but not Main Event (GM, HU, etc.) - skip matching
        nas_year = code_year
        nas_event_type = None
        nas_episode = None
        nas_event = None
        year_source = 'ws_code'
        is_ws_code_unknown = True  # Mark to skip fuzzy matching
    else:
        # Fall back to smart extraction
        nas_year, year_source = extract_year_smart(filename, directory, rel_path)
        nas_event = extract_event_number(combined_text)
        nas_episode = extract_episode_number(combined_text)
        nas_event_type = extract_event_type(combined_text)

    # Determine match eligibility
    matched_collection = ''
    matched_season = ''
    matched_series = ''
    matched_pg_year = ''
    matched_pg_event_type = ''
    matched_pg_content_type = ''

    if not is_wsop:
        # Non-WSOP files cannot be matched
        is_matched = False
        matched_title = ''
        match_score = 0
        match_reason = '[제외] WSOP 콘텐츠 아님'
        non_wsop_count += 1
    elif is_ws_code_unknown:
        # WS code pattern but not Main Event (GM, HU, etc.) - skip matching
        wsop_count += 1
        is_matched = False
        matched_title = ''
        match_score = 0
        # Extract code type from filename (GM, HU, etc.)
        import re
        code_match = re.search(r'WS\d{2}_([A-Z]{2})\d', filename.upper())
        code_type = code_match.group(1) if code_match else 'unknown'
        match_reason = f'[{nas_year}] WS코드 {code_type} 타입 - ME(Main Event)만 매칭'
    else:
        wsop_count += 1
        is_matched = False
        matched_title = ''
        match_score = 0
        match_reason = ''

        # Rule 1: If year extracted, only match with same year PokerGO
        if nas_year:
            # Check if PokerGO has this year
            if nas_year in pokergo_by_year:
                # Filter candidates by event type compatibility
                compatible_eps = [ep for ep in pokergo_by_year[nas_year]
                                  if event_types_compatible(nas_event_type, ep.get('event_type'))]

                if not compatible_eps:
                    # No compatible event type in PokerGO for this year
                    event_type_str = nas_event_type or 'unknown'
                    match_reason = f'[{nas_year}] PokerGO에 {event_type_str} 타입 없음'
                else:
                    # Try exact key match first
                    key = (nas_year, nas_event, nas_episode)
                    if key in pokergo_index:
                        candidates = [c for c in pokergo_index[key]
                                      if event_types_compatible(nas_event_type, c.get('event_type'))]
                        if candidates:
                            best_match = max(candidates, key=lambda x: text_similarity(x['title'], combined_text))
                            match_score = text_similarity(best_match['title'], combined_text)

                            # WS code pattern (e.g., WS11_ME01) is high-confidence, skip similarity check
                            if is_ws_code_pattern:
                                is_matched = True
                                matched_title = best_match['title']
                                matched_collection = best_match.get('collection', '')
                                matched_season = best_match.get('season', '')
                                matched_series = best_match.get('series', '')
                                matched_pg_year = best_match.get('pg_year', '')
                                matched_pg_event_type = best_match.get('pg_event_type', '')
                                matched_pg_content_type = best_match.get('pg_content_type', '')
                                match_score = 1.0  # 100% confidence for code pattern
                                match_reason = f'[{nas_year}] WS코드 패턴 정확 매칭 ({filename[:15]})'
                            elif match_score > 0.25:
                                is_matched = True
                                matched_title = best_match['title']
                                matched_collection = best_match.get('collection', '')
                                matched_season = best_match.get('season', '')
                                matched_series = best_match.get('series', '')
                                matched_pg_year = best_match.get('pg_year', '')
                                matched_pg_event_type = best_match.get('pg_event_type', '')
                                matched_pg_content_type = best_match.get('pg_content_type', '')
                                match_reason = f'[{nas_year}] 연도+이벤트+에피소드 정확 매칭'

                    # Fuzzy match within same year and compatible event type only
                    if not is_matched:
                        best_score = 0
                        best_title = ''
                        best_ep = None
                        for ep in compatible_eps:
                            score = text_similarity(ep['title'], combined_text)
                            if score > best_score:
                                best_score = score
                                best_title = ep['title']
                                best_ep = ep

                        if best_score > 0.35:
                            is_matched = True
                            matched_title = best_title
                            matched_collection = best_ep.get('collection', '') if best_ep else ''
                            matched_season = best_ep.get('season', '') if best_ep else ''
                            matched_series = best_ep.get('series', '') if best_ep else ''
                            matched_pg_year = best_ep.get('pg_year', '') if best_ep else ''
                            matched_pg_event_type = best_ep.get('pg_event_type', '') if best_ep else ''
                            matched_pg_content_type = best_ep.get('pg_content_type', '') if best_ep else ''
                            match_score = best_score
                            event_type_str = nas_event_type or 'all'
                            match_reason = f'[{nas_year}] {event_type_str} 타입 내 유사도 매칭'
                        elif nas_event_type:
                            match_reason = f'[{nas_year}] {nas_event_type} 타입 유사도 부족 ({best_score*100:.0f}%)'
                        else:
                            match_reason = f'[{nas_year}] 유사도 부족 ({best_score*100:.0f}%)'
            else:
                # Year not in PokerGO - no match possible
                match_reason = f'[{nas_year}] PokerGO 데이터 없음 (2011-2025만 존재)'
                no_year_in_pokergo += 1

        else:
            # No year extracted - fall back to general fuzzy match (with event type check)
            best_score = 0
            best_title = ''
            best_ep = None
            for ep in pokergo_eps:
                if event_types_compatible(nas_event_type, ep.get('event_type', extract_event_type(ep.get('title', '')))):
                    score = text_similarity(ep.get('title', ''), combined_text)
                    if score > best_score:
                        best_score = score
                        best_title = ep.get('title', '')
                        best_ep = ep

            if best_score > 0.5:  # Higher threshold for no-year matches
                is_matched = True
                matched_title = best_title
                matched_collection = best_ep.get('collection', '') if best_ep else ''
                matched_season = best_ep.get('season', '') if best_ep else ''
                matched_series = best_ep.get('series', '') if best_ep else ''
                matched_pg_year = best_ep.get('pg_year', '') if best_ep else ''
                matched_pg_event_type = best_ep.get('pg_event_type', '') if best_ep else ''
                matched_pg_content_type = best_ep.get('pg_content_type', '') if best_ep else ''
                match_score = best_score
                match_reason = f'[연도미상] 전체 검색 유사도 매칭'
            else:
                match_reason = f'[연도미상] 파일명에서 연도 추출 실패'

        if is_matched:
            matched_count += 1

    nas_with_matching.append({
        'origin': origin,
        'filename': filename,
        'directory': directory,
        'size_gb': round(size_gb, 2),
        'year': nas_year or '',
        'year_source': year_source or '',
        'is_wsop': is_wsop,
        'is_matched': is_matched,
        # Parsed PokerGO fields
        'matched_series': matched_series,
        'matched_pg_year': matched_pg_year,
        'matched_pg_event_type': matched_pg_event_type,
        'matched_pg_content_type': matched_pg_content_type,
        'matched_pokergo': matched_title,
        'match_score': round(match_score * 100, 1),
        'match_reason': match_reason,
        'source': 'NAS'
    })

print(f'NAS 파일 필터링: 1GB 미만 {small_file_count}개, Clip 파일 {clip_file_count}개 제외')
print(f'NAS WSOP 파일: {wsop_count}개, Non-WSOP 파일: {non_wsop_count}개')
print(f'NAS 매칭 완료: {matched_count}개')
print(f'  WS코드 패턴 파일: {ws_code_match_count}개')
print(f'  PokerGO에 해당 연도 없음: {no_year_in_pokergo}개')

# Find PokerGO-only episodes (not matched to any NAS file)
print('PokerGO-only 에피소드 찾기...')
matched_pokergo_titles = set(item['matched_pokergo'] for item in nas_with_matching if item['is_matched'])

pokergo_only = []
for ep in pokergo_eps:
    title = ep.get('title', '')
    if title not in matched_pokergo_titles:
        year = extract_year_from_text(title)
        event_type = extract_event_type(title)
        event_str = event_type or 'unknown'

        # Parse collection and season for PokerGO-only items
        collection_title = ep.get('collection_title', '')
        season_title = ep.get('season_title', '')
        col_series, col_year = parse_collection(collection_title)
        season_year, season_event_type, season_content_type = parse_season(season_title)

        pokergo_only.append({
            'origin': '',  # No NAS file
            'filename': '',
            'directory': '[PokerGO Only]',
            'size_gb': 0,
            'is_wsop': True,
            'is_matched': False,
            # Parsed PokerGO fields
            'matched_series': col_series,
            'matched_pg_year': season_year or col_year,
            'matched_pg_event_type': season_event_type,
            'matched_pg_content_type': season_content_type,
            'matched_pokergo': title,
            'match_score': 0,
            'match_reason': f'[{year}] NAS에 해당 파일 없음 ({event_str})'
        })

print(f'PokerGO-only WSOP 에피소드: {len(pokergo_only)}개')

# Combine all data
all_data = nas_with_matching + pokergo_only

# Create or clear sheet
print('시트 준비...')
if existing_sheet:
    ws = existing_sheet
    ws.clear()
    print('  기존 시트 초기화')
else:
    ws = sheet.add_worksheet('NAS-POKERGO', rows=len(all_data) + 10, cols=15)
    print('  새 시트 생성')

# Prepare data with Origin and parsed PokerGO fields
headers = ['Matched', 'WSOP', 'Origin', 'Directory', 'Filename', 'PokerGO Title', 'Series', 'PG_Year', 'Event_Type', 'Content_Type', 'Match Reason', 'Score(%)', 'Size(GB)']
rows = [headers]

for item in all_data:
    rows.append([
        item['is_matched'],
        item['is_wsop'],
        item.get('origin', ''),
        item['directory'],
        item['filename'],
        item['matched_pokergo'],
        item.get('matched_series', ''),
        item.get('matched_pg_year', ''),
        item.get('matched_pg_event_type', ''),
        item.get('matched_pg_content_type', ''),
        item.get('match_reason', ''),
        item['match_score'],
        item['size_gb']
    ])

# Upload data
print(f'시트 업로드 중... ({len(rows)-1}개 행)')
ws.update(values=rows, range_name='A1')

# Format checkboxes using batch update
print('체크박스 포맷 적용...')
worksheet_id = ws.id

# Batch update for checkbox formatting
requests = [
    {
        "repeatCell": {
            "range": {
                "sheetId": worksheet_id,
                "startRowIndex": 1,
                "endRowIndex": len(rows),
                "startColumnIndex": 0,
                "endColumnIndex": 1
            },
            "cell": {
                "dataValidation": {
                    "condition": {
                        "type": "BOOLEAN"
                    }
                }
            },
            "fields": "dataValidation"
        }
    },
    {
        "repeatCell": {
            "range": {
                "sheetId": worksheet_id,
                "startRowIndex": 1,
                "endRowIndex": len(rows),
                "startColumnIndex": 1,
                "endColumnIndex": 2
            },
            "cell": {
                "dataValidation": {
                    "condition": {
                        "type": "BOOLEAN"
                    }
                }
            },
            "fields": "dataValidation"
        }
    }
]

sheet.batch_update({"requests": requests})

# Summary
nas_wsop = sum(1 for r in nas_with_matching if r['is_wsop'])
nas_matched = sum(1 for r in nas_with_matching if r['is_matched'])
nas_non_wsop = sum(1 for r in nas_with_matching if not r['is_wsop'])
pokergo_only_count = len(pokergo_only)

excluded_count = small_file_count + clip_file_count
print()
print('=== 완료 ===')
print(f'NAS-POKERGO 시트 생성됨')
print(f'')
print(f'[NAS 파일]')
print(f'  전체: {len(nas_files)}개')
print(f'  제외: {excluded_count}개 (1GB 미만: {small_file_count}, Paradise/Clip/Circuit: {clip_file_count})')
print(f'  처리 대상: {len(nas_files) - excluded_count}개')
print(f'  WSOP: {nas_wsop}개 (매칭: {nas_matched}개, {nas_matched/nas_wsop*100:.1f}%)' if nas_wsop > 0 else f'  WSOP: 0개')
print(f'  Non-WSOP: {nas_non_wsop}개 (매칭 불가)')
print(f'')
print(f'[PokerGO Only]')
print(f'  NAS에 없는 WSOP 에피소드: {pokergo_only_count}개')
print(f'')
print(f'[총계]')
print(f'  시트 총 행 수: {len(all_data)}개')

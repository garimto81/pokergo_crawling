"""
Semantic Matcher: NAS 파일명 <-> PokerGO title 매칭 시스템

매칭 전략:
1. Direct Normalized Match: 정규화된 텍스트 직접 비교
2. Semantic Match: 메타데이터 추출 후 (Year, Type, Episode/Day/Event) 매칭
3. Classic Match: 연도 기반 Classic 콘텐츠 매칭
"""
import json
import re
from pathlib import Path
from collections import defaultdict
from dataclasses import dataclass
from typing import Optional, Dict, List, Tuple


@dataclass
class Metadata:
    """Extracted metadata from filename/title."""
    year: Optional[int] = None
    region: str = 'LV'  # LV, EU, APAC, PAR
    type: Optional[str] = None  # ME, BR, HR, HU, GM, PPC, NC, BO
    episode: Optional[int] = None
    day: Optional[str] = None
    event_num: Optional[int] = None
    part: Optional[int] = None
    show_num: Optional[int] = None
    is_final: bool = False
    original: str = ''


def normalize_for_matching(text: str) -> str:
    """Normalize text for direct matching."""
    if not text:
        return ''

    # Remove source prefix
    text = re.sub(r'^\s*\(?(YouTube|PokerGO|PokerGo)\)?\s*', '', text, flags=re.I)

    # Remove extension
    text = re.sub(r'\.(mp4|mov|mxf|avi|mkv|wmv|m4v)$', '', text, flags=re.I)

    # Remove resolution
    text = re.sub(r'\s*\(?(1080p|720p|480p|4K|HD|UHD)\)?', '', text, flags=re.I)

    # Remove trailing markers
    text = re.sub(r'[_-](NB|FINAL|4CH|CLEAN|MASTER(ED)?)$', '', text, flags=re.I)

    # Normalize separators (including slash for Day 2A/B/C patterns)
    text = text.replace('|', ' ')
    text = text.replace('_', ' ')
    text = text.replace('-', ' ')
    text = text.replace('/', ' ')  # 슬래시도 공백으로 (Day 2A/B/C -> Day 2A B C)

    # Remove currency
    text = re.sub(r'[$€£]', '', text)

    # Multiple spaces
    text = re.sub(r'\s+', ' ', text)

    return text.strip().lower()


def extract_pkg_metadata(title: str, year: str) -> Metadata:
    """Extract metadata from PokerGO title."""
    title_lower = title.lower()
    meta = Metadata(original=title)

    # Year
    meta.year = int(year) if year else None

    # Region
    if 'europe' in title_lower or 'wsope' in title_lower:
        meta.region = 'EU'
    elif 'apac' in title_lower:
        meta.region = 'APAC'
    elif 'paradise' in title_lower:
        meta.region = 'PAR'

    # Type
    if 'main event' in title_lower:
        meta.type = 'ME'
    elif 'bracelet' in title_lower:
        meta.type = 'BR'
    elif 'high roller' in title_lower:
        meta.type = 'HR'
    elif 'heads-up' in title_lower or 'heads up' in title_lower:
        meta.type = 'HU'
    elif 'grudge' in title_lower:
        meta.type = 'GM'
    elif 'poker players championship' in title_lower:
        meta.type = 'PPC'
    elif 'national championship' in title_lower:
        meta.type = 'NC'
    elif 'big one' in title_lower:
        meta.type = 'BO'

    # Episode
    m = re.search(r'episode\s*(\d+)', title_lower)
    if m:
        meta.episode = int(m.group(1))

    # Day
    m = re.search(r'day\s*(\d+[a-d]?)', title_lower)
    if m:
        meta.day = m.group(1).upper()

    # Event number
    m = re.search(r'event\s*#(\d+)', title_lower)
    if m:
        meta.event_num = int(m.group(1))

    # Part
    m = re.search(r'\(part\s*(\d+)\)', title_lower)
    if m:
        meta.part = int(m.group(1))

    # Final
    if 'final table' in title_lower or 'final day' in title_lower:
        meta.is_final = True

    return meta


def extract_nas_metadata(filename: str) -> Metadata:
    """Extract metadata from NAS filename."""
    fname_lower = filename.lower()
    meta = Metadata(original=filename)

    # Region
    if 'wsope' in fname_lower or 'europe' in fname_lower:
        meta.region = 'EU'
    elif 'apac' in fname_lower:
        meta.region = 'APAC'
    elif 'paradise' in fname_lower:
        meta.region = 'PAR'

    # =========== Year Extraction ===========

    # Pattern 1: WS11_, WS09_ -> 2011, 2009
    m = re.search(r'\bws(\d{2})[-_]', fname_lower)
    if m:
        yy = int(m.group(1))
        meta.year = 2000 + yy if yy < 50 else 1900 + yy

    # Pattern 2: WSOP14_, WSOP_2011
    if not meta.year:
        m = re.search(r'wsop(\d{2})[-_]', fname_lower)
        if m:
            yy = int(m.group(1))
            meta.year = 2000 + yy if yy < 50 else 1900 + yy

    # Pattern 3: WSE13- (WSOP Europe short code) -> 2013
    if not meta.year:
        m = re.search(r'\bwse(\d{2})[-_]', fname_lower)
        if m:
            yy = int(m.group(1))
            meta.year = 2000 + yy if yy < 50 else 1900 + yy
            meta.region = 'EU'

    # Pattern 4: WE24- (WSOP Europe short code variant) -> 2024
    if not meta.year:
        m = re.search(r'\bwe(\d{2})[-_]', fname_lower)
        if m:
            yy = int(m.group(1))
            meta.year = 2000 + yy if yy < 50 else 1900 + yy
            meta.region = 'EU'

    # Pattern 5: WSOPE08 (WSOP Europe without separator) -> 2008
    if not meta.year:
        m = re.search(r'wsope(\d{2})[_-]', fname_lower)
        if m:
            yy = int(m.group(1))
            meta.year = 2000 + yy if yy < 50 else 1900 + yy
            meta.region = 'EU'

    # Pattern 6: WSOP 2024, wsop-2021, wsope-2021
    if not meta.year:
        m = re.search(r'wsop[e]?\s*[-_]?\s*(19|20)(\d{2})', fname_lower)
        if m:
            meta.year = int(m.group(1) + m.group(2))

    # Pattern 7: "N_YYYY WSOPE" (index prefix format) -> 2025
    if not meta.year:
        m = re.search(r'^\d+[_-]?(19|20)(\d{2})\s+wsop', fname_lower)
        if m:
            meta.year = int(m.group(1) + m.group(2))
            if 'wsope' in fname_lower:
                meta.region = 'EU'

    # Pattern 8: "2016 World Series of Poker"
    if not meta.year:
        m = re.search(r'^(19|20)(\d{2})\s+world\s+series', fname_lower)
        if m:
            meta.year = int(m.group(1) + m.group(2))

    # Pattern 9: Just year in filename (fallback)
    if not meta.year:
        m = re.search(r'\b(19[7-9]\d|20[0-2]\d)\b', fname_lower)
        if m:
            meta.year = int(m.group(1))

    # =========== Type & Episode Extraction ===========

    # Europe short code: WSE13-ME01, WE24-ME-01
    m = re.search(r'(wse|we)\d{2}[-_]me[-_]?(\d+)', fname_lower)
    if m:
        meta.region = 'EU'
        meta.type = 'ME'
        meta.episode = int(m.group(2))

    # Europe Episode pattern: WSOPE08_Episode_1
    if not meta.episode:
        m = re.search(r'wsope\d{2}[_-]episode[_-](\d+)', fname_lower)
        if m:
            meta.region = 'EU'
            meta.type = 'ME'
            meta.episode = int(m.group(1))

    # Short Code: WS11_ME01, WS11_GM02, WSOP13_NC01, WSOP16_GCC_P01
    m = re.search(r'(ws|wsop)\d{2}[-_](me|gm|hu|ppc|nc|bo|gcc)(\d+)', fname_lower)
    if m:
        type_map = {'me': 'ME', 'gm': 'GM', 'hu': 'HU', 'ppc': 'PPC', 'nc': 'NC', 'bo': 'BO', 'gcc': 'GCC'}
        meta.type = type_map.get(m.group(2), m.group(2).upper())
        meta.episode = int(m.group(3))

    # GCC pattern: WSOP16_GCC_P01, GCC_P2_Final
    if not meta.type:
        m = re.search(r'gcc[_-]?p(\d+)', fname_lower)
        if m:
            meta.type = 'GCC'
            meta.part = int(m.group(1))

    # Show Code: WS12_Show_10_ME06, "Main Event Show 01"
    if not meta.episode:
        m = re.search(r'show[-_\s](\d+)[-_\s]me(\d+)', fname_lower)
        if m:
            meta.type = 'ME'
            meta.show_num = int(m.group(1))
            meta.episode = int(m.group(2))

    # Show_N_FINAL pattern: WS12_Show_17_FINAL -> ME Episode 17
    if not meta.episode:
        m = re.search(r'show[-_](\d+)[-_](final|nb)', fname_lower)
        if m:
            meta.type = 'ME'
            meta.show_num = int(m.group(1))
            meta.episode = int(m.group(1))  # Show number = Episode number

    # Main Event Show pattern: "Main Event Show 01"
    if not meta.episode:
        m = re.search(r'main\s*event\s*show\s*(\d+)', fname_lower)
        if m:
            meta.type = 'ME'
            meta.episode = int(m.group(1))

    # ME pattern: WSOP15_ME11, _ME25, "WSOP ME01"
    if not meta.episode:
        m = re.search(r'[-_\s]me(\d+)', fname_lower)
        if m:
            meta.type = 'ME'
            meta.episode = int(m.group(1))

    # APAC patterns: WSOP14_APAC_MAIN_EVENT-SHOW 1
    if 'apac' in fname_lower:
        meta.region = 'APAC'
        if 'main' in fname_lower or 'me' in fname_lower:
            meta.type = 'ME'
        elif 'high' in fname_lower and 'roller' in fname_lower:
            meta.type = 'HR'
        m = re.search(r'show\s*(\d+)', fname_lower)
        if m:
            meta.episode = int(m.group(1))

    # Day extraction
    m = re.search(r'day\s*[-_]?(\d+[a-d]?)', fname_lower)
    if m:
        meta.day = m.group(1).upper()
        if not meta.type:
            meta.type = 'ME'

    # Event number (Bracelet)
    m = re.search(r'event\s*#?(\d+)', fname_lower)
    if m:
        meta.event_num = int(m.group(1))
        if not meta.type:
            meta.type = 'BR'

    # Bracelet pattern: [BRACELET #10], BRACELET EVENT #13
    m = re.search(r'bracelet\s*#?(\d+)', fname_lower)
    if m:
        meta.event_num = int(m.group(1))
        meta.type = 'BR'

    # Part
    m = re.search(r'part\s*[-_]?(\d+)', fname_lower)
    if m:
        meta.part = int(m.group(1))

    # Final
    if 'final' in fname_lower or '-ft-' in fname_lower or '_ft_' in fname_lower:
        meta.is_final = True

    # Fallback type detection
    if not meta.type:
        if 'main event' in fname_lower or 'main_event' in fname_lower:
            meta.type = 'ME'
        elif 'bracelet' in fname_lower:
            meta.type = 'BR'
        elif 'high roller' in fname_lower or 'highroller' in fname_lower:
            meta.type = 'HR'

    return meta


class SemanticMatcher:
    """Semantic matching engine for NAS <-> PokerGO."""

    def __init__(self):
        self.pkg_by_normalized: Dict[str, str] = {}
        self.pkg_by_key: Dict[Tuple, str] = {}
        self.pkg_by_year: Dict[int, List[dict]] = defaultdict(list)
        self.videos: List[dict] = []

    def load_pokergo(self, json_path: Path):
        """Load PokerGO data and build indexes."""
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        # Handle both list format and dict format
        self.videos = data if isinstance(data, list) else data.get('videos', [])

        for v in self.videos:
            title = v.get('title', '')
            year = v.get('year', '')
            title_lower = title.lower()

            # Normalized index
            norm = normalize_for_matching(title)
            if norm:
                self.pkg_by_normalized[norm] = title

            # Metadata index
            meta = extract_pkg_metadata(title, year)
            if meta.year:
                self.pkg_by_year[meta.year].append(v)

            if meta.year and meta.type:
                # Episode key
                if meta.episode:
                    key = (meta.year, meta.region, meta.type, 'ep', meta.episode)
                    self.pkg_by_key[key] = title

                # Day+Part key (Part가 있으면 Day+Part 조합, 없으면 Day만)
                if meta.day:
                    if meta.part:
                        # Day+Part 조합 키 (예: '2A_P1', '2A_P2')
                        key = (meta.year, meta.region, meta.type, 'day_part', f'{meta.day}_P{meta.part}')
                        self.pkg_by_key[key] = title
                    else:
                        # Day만 있는 경우
                        key = (meta.year, meta.region, meta.type, 'day', meta.day)
                        self.pkg_by_key[key] = title

                # Final Table key (Main Event)
                if meta.is_final and meta.type == 'ME':
                    if meta.day:
                        # Final Table Day (예: WSOP 2025 Main Event | Final Table | Day 1)
                        key = (meta.year, meta.region, 'ME', 'final_day', meta.day)
                        self.pkg_by_key[key] = title
                    elif meta.part:
                        # Final Table Part (예: Wsop Main Event 2006 Final Table Part 1)
                        key = (meta.year, meta.region, 'ME', 'final_part', meta.part)
                        self.pkg_by_key[key] = title
                    else:
                        # Final Table만 (예: Wsop Main Event 2004 Final Table)
                        key = (meta.year, meta.region, 'ME', 'final', 1)
                        self.pkg_by_key[key] = title

                # Event key (Bracelet)
                if meta.event_num:
                    key = (meta.year, meta.region, 'BR', 'event', meta.event_num)
                    self.pkg_by_key[key] = title

                    # Event+Day+Part 키 (Bracelet Event Day/Part)
                    if meta.day:
                        if meta.part:
                            key = (meta.year, meta.region, 'BR', f'event{meta.event_num}_day_part', f'{meta.day}_P{meta.part}')
                            self.pkg_by_key[key] = title
                        else:
                            key = (meta.year, meta.region, 'BR', f'event{meta.event_num}_day', meta.day)
                            self.pkg_by_key[key] = title

                    # Event+Final 키 (Bracelet Event Final Table)
                    if meta.is_final:
                        key = (meta.year, meta.region, 'BR', f'event{meta.event_num}_final', 1)
                        self.pkg_by_key[key] = title

            # Special type indexing
            year_int = int(year) if year else None

            # Grudge Match: map by year and episode
            if 'grudge' in title_lower and year_int:
                # Determine episode from match participants
                if 'moneymaker' in title_lower or 'farha' in title_lower:
                    key = (year_int, 'LV', 'GM', 'ep', 1)
                    self.pkg_by_key[key] = title
                elif 'chan' in title_lower or 'hellmuth' in title_lower:
                    key = (year_int, 'LV', 'GM', 'ep', 2)
                    self.pkg_by_key[key] = title

            # Big One for One Drop: map by year and part
            if 'big one' in title_lower and year_int:
                m = re.search(r'\(part\s*(\d+)\)', title_lower)
                if m:
                    part = int(m.group(1))
                    key = (year_int, 'LV', 'BO', 'part', part)
                    self.pkg_by_key[key] = title

            # National Championship: map by year and part
            if 'national championship' in title_lower and year_int:
                m = re.search(r'\(part\s*(\d+)\)', title_lower)
                if m:
                    part = int(m.group(1))
                    key = (year_int, 'LV', 'NC', 'part', part)
                    self.pkg_by_key[key] = title

            # Global Casino Championship: map by year and part
            if 'global casino championship' in title_lower and year_int:
                m = re.search(r'\(part\s*(\d+)\)', title_lower)
                if m:
                    part = int(m.group(1))
                    key = (year_int, 'LV', 'GCC', 'part', part)
                    self.pkg_by_key[key] = title

            # Heads Up Championship: map by year
            if 'heads-up' in title_lower and 'championship' in title_lower and year_int:
                if 'final' in title_lower:
                    key = (year_int, 'LV', 'HU', 'final', 1)
                    self.pkg_by_key[key] = title
                elif 'semi' in title_lower:
                    key = (year_int, 'LV', 'HU', 'semi', 1)
                    self.pkg_by_key[key] = title

            # Classic format: "Wsop 2009 01 Me Day1A" -> key by (year, show_number)
            # Pattern: Wsop YYYY NN ...
            m = re.match(r'wsop\s+(\d{4})\s+(\d+)\s+', title_lower)
            if m and year_int:
                show_num = int(m.group(2))
                key = (year_int, 'LV', 'CLASSIC', 'show', show_num)
                self.pkg_by_key[key] = title

            # Europe format: "Wsop Europe 2009 Main Event Episode N"
            m = re.search(r'wsop\s+europe\s+(\d{4})\s+main\s+event\s+episode\s+(\d+)', title_lower)
            if m:
                eu_year = int(m.group(1))
                ep = int(m.group(2))
                key = (eu_year, 'EU', 'ME', 'ep', ep)
                self.pkg_by_key[key] = title

        print(f'Loaded {len(self.videos)} PokerGO videos')
        print(f'  Normalized index: {len(self.pkg_by_normalized)} entries')
        print(f'  Key index: {len(self.pkg_by_key)} entries')

    def match(self, filename: str) -> Tuple[Optional[str], str]:
        """
        Match NAS filename to PokerGO title.

        Returns: (matched_title, match_method)
        """
        # Stage 1: Direct Normalized Match
        norm = normalize_for_matching(filename)
        if norm in self.pkg_by_normalized:
            return self.pkg_by_normalized[norm], 'normalized'

        # Stage 2: Semantic Metadata Match
        meta = extract_nas_metadata(filename)
        fname_lower = filename.lower()

        if meta.year and meta.type:
            # Try episode
            if meta.episode:
                key = (meta.year, meta.region, meta.type, 'ep', meta.episode)
                if key in self.pkg_by_key:
                    return self.pkg_by_key[key], 'semantic_episode'

            # Try day+part first (if part exists), then day only
            if meta.day:
                if meta.part:
                    # Day+Part 조합 매칭 우선
                    key = (meta.year, meta.region, meta.type, 'day_part', f'{meta.day}_P{meta.part}')
                    if key in self.pkg_by_key:
                        return self.pkg_by_key[key], 'semantic_day_part'
                # Day만 매칭 (Part 없거나 Day+Part 매칭 실패 시)
                key = (meta.year, meta.region, meta.type, 'day', meta.day)
                if key in self.pkg_by_key:
                    return self.pkg_by_key[key], 'semantic_day'

            # Try event (Bracelet)
            if meta.event_num:
                # Final Table 매칭 우선 (is_final=True인 경우)
                if meta.is_final:
                    key = (meta.year, meta.region, 'BR', f'event{meta.event_num}_final', 1)
                    if key in self.pkg_by_key:
                        return self.pkg_by_key[key], 'semantic_event_final'
                    # Final Table인데 PokerGO에 없으면 매칭하지 않음 (잘못된 fallback 방지)
                    # 아래 Day/Event fallback 건너뛰기
                else:
                    # Event+Day+Part 매칭 먼저 시도
                    if meta.day and meta.part:
                        key = (meta.year, meta.region, 'BR', f'event{meta.event_num}_day_part', f'{meta.day}_P{meta.part}')
                        if key in self.pkg_by_key:
                            return self.pkg_by_key[key], 'semantic_event_day_part'
                    if meta.day:
                        key = (meta.year, meta.region, 'BR', f'event{meta.event_num}_day', meta.day)
                        if key in self.pkg_by_key:
                            return self.pkg_by_key[key], 'semantic_event_day'
                    # Event만 매칭 (fallback) - day/part 정보가 없는 경우만
                    if not meta.day and not meta.part:
                        key = (meta.year, meta.region, 'BR', 'event', meta.event_num)
                        if key in self.pkg_by_key:
                            return self.pkg_by_key[key], 'semantic_event'

            # Try part (for BO, NC, GCC types) - episode number = part number
            if meta.type in ('BO', 'NC', 'GCC'):
                part_num = meta.part or meta.episode  # Use episode as part if no explicit part
                if part_num:
                    key = (meta.year, meta.region, meta.type, 'part', part_num)
                    if key in self.pkg_by_key:
                        return self.pkg_by_key[key], 'semantic_part'

            # Try explicit part
            elif meta.part:
                key = (meta.year, meta.region, meta.type, 'part', meta.part)
                if key in self.pkg_by_key:
                    return self.pkg_by_key[key], 'semantic_part'

        # Stage 3: Special pattern extraction for WS12_Show_X_TYPE_N
        if meta.year:
            # Big One for One Drop: WS12_Show_1_BIG_ONE_1
            m = re.search(r'big[-_]?one[-_]?(\d+)', fname_lower)
            if m:
                part = int(m.group(1))
                key = (meta.year, 'LV', 'BO', 'part', part)
                if key in self.pkg_by_key:
                    return self.pkg_by_key[key], 'semantic_bigone'

            # National Championship: WS12_Show_3_NAT_CHAMP_1
            m = re.search(r'nat[-_]?champ[-_]?(\d+)', fname_lower)
            if m:
                part = int(m.group(1))
                key = (meta.year, 'LV', 'NC', 'part', part)
                if key in self.pkg_by_key:
                    return self.pkg_by_key[key], 'semantic_natchamp'

            # Heads Up Championship
            if 'hu' in fname_lower or 'heads' in fname_lower:
                if 'final' in fname_lower:
                    key = (meta.year, 'LV', 'HU', 'final', 1)
                    if key in self.pkg_by_key:
                        return self.pkg_by_key[key], 'semantic_hu'

        # Stage 4: Classic show number match (2003-2010)
        # NAS: "2009 WSOP ME03" -> PKG: "Wsop 2009 03 Me ..."
        if meta.year and 2003 <= meta.year <= 2010:
            # Extract show number from various patterns
            show_num = None

            # Pattern: ME03, ME14 (episode number)
            m = re.search(r'me(\d+)', fname_lower)
            if m:
                show_num = int(m.group(1))

            # Pattern: Show 1, SHOW_10
            if not show_num:
                m = re.search(r'show\s*[-_]?(\d+)', fname_lower)
                if m:
                    show_num = int(m.group(1))

            # Pattern: SEASON N SHOW M
            if not show_num:
                m = re.search(r'season\s*\d+\s*show\s*(\d+)', fname_lower)
                if m:
                    show_num = int(m.group(1))

            if show_num:
                key = (meta.year, 'LV', 'CLASSIC', 'show', show_num)
                if key in self.pkg_by_key:
                    return self.pkg_by_key[key], 'classic_show'

        # Stage 5: Europe ME episode match
        if meta.region == 'EU' and meta.type == 'ME' and meta.year:
            # Try episode
            if meta.episode:
                key = (meta.year, 'EU', 'ME', 'ep', meta.episode)
                if key in self.pkg_by_key:
                    return self.pkg_by_key[key], 'europe_episode'

        # Stage 6: Vintage Classic Year Match (for 1973-2002)
        if meta.year and meta.year <= 2002:
            videos = self.pkg_by_year.get(meta.year, [])
            if videos:
                # Prefer Main Event
                me_videos = [v for v in videos if 'main event' in v.get('title', '').lower()]
                if me_videos:
                    return me_videos[0]['title'], 'classic_year'
                elif len(videos) == 1:
                    return videos[0]['title'], 'classic_year'

        return None, 'no_match'


def is_excludable(filename: str) -> Tuple[bool, str]:
    """Check if file should be excluded from matching."""
    fname_lower = filename.lower()

    # Hand clips
    if re.match(r'^\d+-wsop-', fname_lower):
        return True, 'hand_clip'
    if '-hs-' in fname_lower or '_hs_' in fname_lower:
        return True, 'hand_segment'
    if 'hand_' in fname_lower:
        return True, 'hand_clip'

    # Highlights
    if 'highlight' in fname_lower:
        return True, 'highlight'
    if 'clip' in fname_lower:
        return True, 'clip'

    # Circuit
    if 'circuit' in fname_lower:
        return True, 'circuit'

    # Raw footage
    if 'raw' in fname_lower or 'iso' in fname_lower:
        return True, 'raw_footage'

    # Promo/Trailer
    if 'trailer' in fname_lower or 'promo' in fname_lower or 'teaser' in fname_lower:
        return True, 'promo'

    # Interview
    if 'interview' in fname_lower or 'itw' in fname_lower:
        return True, 'interview'

    # Graphics
    if 'graphic' in fname_lower or 'slate' in fname_lower or 'logo' in fname_lower:
        return True, 'graphics'

    return False, ''


def main():
    """Test the semantic matcher."""
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from src.nams.api.database import get_db, NasFile

    # Load matcher
    matcher = SemanticMatcher()
    json_path = Path(__file__).parent.parent / 'data' / 'pokergo' / 'wsop_final.json'
    matcher.load_pokergo(json_path)

    # Load NAS files
    db = next(get_db())
    all_files = db.query(NasFile).filter(
        (NasFile.full_path.ilike('%wsop%') |
         NasFile.full_path.ilike('%ws0%') |
         NasFile.full_path.ilike('%ws1%') |
         NasFile.full_path.ilike('%ws2%'))
    ).all()

    # Statistics
    stats = defaultdict(int)
    matched = []
    unmatched = []
    excluded = []

    for f in all_files:
        # Check exclusion first
        is_excl, excl_reason = is_excludable(f.filename)
        if is_excl:
            excluded.append((f.filename, excl_reason))
            stats['excluded'] += 1
            continue

        # Try matching
        title, method = matcher.match(f.filename)
        if title:
            matched.append((f.filename, title, method))
            stats[f'match_{method}'] += 1
        else:
            meta = extract_nas_metadata(f.filename)
            unmatched.append((f.filename, meta))
            stats['no_match'] += 1

    # Report
    print('\n' + '=' * 60)
    print('SEMANTIC MATCHING RESULTS')
    print('=' * 60)

    total = len(all_files)
    print(f'\nTotal NAS files: {total}')
    print(f'Excluded: {stats["excluded"]} ({stats["excluded"]/total*100:.1f}%)')

    matchable = total - stats['excluded']
    matched_count = matchable - stats['no_match']
    print(f'\nMatchable: {matchable}')
    print(f'Matched: {matched_count} ({matched_count/matchable*100:.1f}%)')
    print(f'Unmatched: {stats["no_match"]} ({stats["no_match"]/matchable*100:.1f}%)')

    print('\n--- Match Methods ---')
    for key in sorted(stats.keys()):
        if key.startswith('match_'):
            print(f'  {key}: {stats[key]}')

    print('\n--- Sample Matches ---')
    for nas, pkg, method in matched[:10]:
        clean = nas.encode('ascii', 'ignore').decode()[:40]
        print(f'[{method}] {clean}')
        print(f'  -> {pkg[:50]}')

    print('\n--- Sample Unmatched ---')
    for nas, meta in unmatched[:15]:
        clean = nas.encode('ascii', 'ignore').decode()[:50]
        print(f'{clean}')
        print(f'  meta: year={meta.year}, type={meta.type}, ep={meta.episode}, day={meta.day}')


if __name__ == '__main__':
    main()

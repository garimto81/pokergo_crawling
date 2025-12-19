"""Pattern matching engine for extracting metadata from full paths."""
import re
from dataclasses import dataclass

from sqlalchemy.orm import Session

from ..database import EventType, NasFile, Pattern, Region, get_db_context


@dataclass
class ExtractionResult:
    """Result of pattern extraction."""
    matched: bool
    pattern_id: int | None = None
    pattern_name: str | None = None
    year: int | None = None
    region_id: int | None = None
    region_code: str | None = None
    event_type_id: int | None = None
    event_type_code: str | None = None
    episode: int | None = None
    confidence: float = 0.0

    # Extended metadata (new fields)
    stage: str | None = None        # D1A, D2, FT, FINAL, S1
    event_num: int | None = None    # Event #13 -> 13
    season: int | None = None       # PAD S12 -> 12
    buyin: str | None = None        # $100K, $5K
    gtd: str | None = None          # $5M GTD -> 5M
    version: str | None = None      # NC (No Commentary), NB, CLEAN
    part: int | None = None         # Part number (for CLASSIC era: Part 1, Part 2)


def get_region_id(db: Session, code: str) -> int | None:
    """Get region ID by code."""
    if not code:
        return None
    region = db.query(Region).filter(Region.code == code.upper()).first()
    return region.id if region else None


def get_event_type_id(db: Session, code: str) -> int | None:
    """Get event type ID by code."""
    if not code:
        return None
    # Normalize code
    code = code.upper().replace('_', '-')
    event_type = db.query(EventType).filter(EventType.code == code).first()
    return event_type.id if event_type else None


def extract_year_from_path(path: str) -> int | None:
    """Extract year from full path.

    Priority:
    1. Year at start of filename (most reliable): "1987 World Series..."
    2. WSOP patterns in filename: "WSOP_2003-01.mxf", "wsop-1973-me-nobug.mp4"
    3. WSOP patterns in path (excluding PRE-XXXX)
    4. Folder year: ".../1987/..." (but not PRE-2003)
    """
    # Extract filename
    filename = path.split('\\')[-1].split('/')[-1]

    # Priority 1: Year at start of filename (most reliable)
    # Pattern: "1987 World Series...", "2003 WSOP...", "2002 World Series Part 1"
    filename_start_year = re.match(r'^(\d{4})\s+', filename)
    if filename_start_year:
        year = int(filename_start_year.group(1))
        if 1970 <= year <= 2030:
            return year

    # Priority 2: WSOP patterns in FILENAME only
    filename_patterns = [
        r'WSOP[_\-](\d{4})',         # "WSOP_2003", "WSOP-2024"
        r'WSOP\s*-\s*(\d{4})',       # "WSOP - 1973"
        r'wsope?-(\d{4})-',          # "wsop-1973-", "wsope-2021-"
        r'WSOP[E]?\s*(\d{4})',       # "WSOP 2024", "WSOPE 2024"
    ]
    for pattern in filename_patterns:
        match = re.search(pattern, filename, re.I)
        if match:
            year = int(match.group(1))
            if 1970 <= year <= 2030:
                return year

    # Priority 3: WSOP patterns in full path (but exclude PRE-XXXX)
    # Remove PRE-XXXX from path before searching
    path_cleaned = re.sub(r'PRE-\d{4}', '', path)

    path_patterns = [
        r'(\d{4})\s*WSOP',           # "2024 WSOP"
        r'WSOP[E]?\s*(\d{4})',       # "WSOP 2024", "WSOPE 2024"
        r'WSOP[_\-](\d{4})',         # "WSOP_1983"
        r'WSOP\s*-\s*(\d{4})',       # "WSOP - 1973"
        r'(\d{4})\s*MPP',            # "2025 MPP"
        r'wsope?-(\d{4})-',          # "wsop-1973-"
    ]
    for pattern in path_patterns:
        match = re.search(pattern, path_cleaned, re.I)
        if match:
            year = int(match.group(1))
            if 1970 <= year <= 2030:
                return year

    # Priority 4: 2-digit year patterns
    patterns_2digit = [
        r'WSOPE?(\d{2})[_\-]',       # WSOPE08_, WS12-
        r'WS(\d{2})[_\-]',           # WS11_
        r'[_\-](\d{2})[_\-]',        # _08_, -12-
    ]
    for pattern in patterns_2digit:
        match = re.search(pattern, path_cleaned, re.I)
        if match:
            y = int(match.group(1))
            year = 2000 + y if y < 50 else 1900 + y
            return year

    # Priority 5: Folder year pattern (but not PRE-XXXX)
    # Pattern: .../1987/... or .../WSOP 1987/...
    folder_year = re.search(r'[/\\](\d{4})[/\\]', path_cleaned)
    if folder_year:
        year = int(folder_year.group(1))
        if 1970 <= year <= 2030:
            return year

    # Fallback: generic 4-digit year in filename only (not full path)
    match = re.search(r'\b(19[7-9]\d|20[0-2]\d)\b', filename)
    if match:
        return int(match.group(1))

    return None


def extract_stage_from_path(path: str) -> str | None:
    """Extract stage (Day 1A, Final Table, etc.) from path."""
    # Final Table first (to catch "Final Table Day X" before generic "Day X")
    if re.search(r'Final\s*Table', path, re.I):
        # Check for Final Table Day X
        ft_day = re.search(r'Final\s*Table\s*Day\s*(\d+)', path, re.I)
        if ft_day:
            return f"FT-D{ft_day.group(1)}"
        return "FT"

    # Day patterns: Day 1, Day 1A, Day 2B
    day_match = re.search(r'Day\s*(\d+)\s*([ABCD])?', path, re.I)
    if day_match:
        day = day_match.group(1)
        suffix = day_match.group(2) or ''
        return f"D{day}{suffix.upper()}"

    # Session patterns (MPP)
    session_match = re.search(r'Session\s*(\d+)', path, re.I)
    if session_match:
        return f"S{session_match.group(1)}"

    return None


def extract_event_num_from_path(path: str) -> int | None:
    """Extract event number (Event #13) from path."""
    match = re.search(r'Event\s*#?(\d+)', path, re.I)
    if match:
        return int(match.group(1))
    # Alternative: #10 in folder name
    match = re.search(r'#(\d+)\s', path)
    if match:
        return int(match.group(1))
    return None


def extract_buyin_from_path(path: str) -> str | None:
    """Extract buy-in amount from path."""
    # $100K, $5K, $1.5K, $10,000
    match = re.search(r'\$(\d+(?:[.,]\d+)?[KM]?)', path, re.I)
    if match:
        buyin = match.group(1).replace(',', '')
        return buyin
    return None


def extract_gtd_from_path(path: str) -> str | None:
    """Extract GTD amount from path."""
    match = re.search(r'\$(\d+[MK]?)\s*GTD', path, re.I)
    if match:
        return match.group(1)
    return None


def extract_version_from_path(path: str) -> str | None:
    """Extract version info (No Commentary, Clean, etc.) from path."""
    if re.search(r'NO\s*COMMENTARY', path, re.I):
        return "NC"
    if re.search(r'_NB[_\.]', path, re.I):
        return "NB"
    if re.search(r'CLEAN', path, re.I):
        return "CLEAN"
    return None


def extract_episode_from_day_part(path: str) -> int | None:
    """Extract episode number from Day/Part patterns.

    Day mapping (per MATCHING_RULES.md):
    - Day 1A, 1B, 1C, 1D → Episode 01
    - Day 2, 3, 4, ... → Episode 02, 03, 04, ...
    - Final Day → Episode 99

    Part mapping:
    - Part 1, Part 2, ... → Episode 01, 02, ...
    """
    path_lower = path.lower()

    # Final Day/Table → Episode 99
    if re.search(r'final\s*(day|table)', path_lower):
        return 99

    # Day X patterns: Day 1, Day 1A, Day 2B (ABCD variants = same episode)
    day_match = re.search(r'day\s*(\d+)\s*[abcd]?', path_lower)
    if day_match:
        return int(day_match.group(1))

    # Part X patterns: Part 1, Part 2
    part_match = re.search(r'part\s*(\d+)', path_lower)
    if part_match:
        return int(part_match.group(1))

    return None


def extract_part_from_path(path: str, year: int | None = None) -> int | None:
    """Extract Part number from path for CLASSIC era files.

    CLASSIC Era (1973-2002) files may have Part numbers that indicate
    different content (not just different formats of the same content).

    Patterns:
    - Part 1.mov, Part 2.mov
    - WSOP_2002_1.mxf, WSOP_2002_2.mxf
    - WSOP - 2002 - 1.mxf

    Returns:
        Part number (1, 2, etc.) or None if not found
    """
    path_lower = path.lower()
    filename = path.split('\\')[-1].split('/')[-1]
    filename_lower = filename.lower()

    # Pattern 1: Part N, Part_N, Part-N
    part_match = re.search(r'part[_\s\-]*(\d+)', path_lower)
    if part_match:
        return int(part_match.group(1))

    # Pattern 2: WSOP_YYYY_N.ext or WSOP-YYYY-N.ext (only for CLASSIC era)
    if year and year <= 2002:
        # WSOP_2002_1.mxf, WSOP_2002_2.mxf
        wsop_part = re.search(r'wsop[_\-]\d{4}[_\-](\d+)\.(?:mxf|mov|mp4)', filename_lower)
        if wsop_part:
            part_num = int(wsop_part.group(1))
            if part_num <= 10:  # Reasonable part number limit
                return part_num

        # WSOP - YYYY - N.ext (with spaces)
        wsop_space = re.search(r'wsop\s*-\s*\d{4}\s*-\s*(\d+)\.(?:mxf|mov|mp4)', filename_lower)
        if wsop_space:
            part_num = int(wsop_space.group(1))
            if part_num <= 10:
                return part_num

    # Pattern 3: Filename ending with _N or -N before extension (CLASSIC era only)
    if year and year <= 2002:
        trailing_num = re.search(r'[_\-](\d+)\.(?:mxf|mov|mp4)$', filename_lower)
        if trailing_num:
            part_num = int(trailing_num.group(1))
            # Only treat as Part if it's a small number (1-10)
            if 1 <= part_num <= 10:
                return part_num

    return None


def extract_episode_from_path(path: str, pattern_name: str) -> int | None:
    """Extract episode number based on pattern type."""
    # WS{YY}_{TYPE}{EP} format: WS11_ME01_NB.mp4, WS12_BR25.mxf
    if pattern_name == "WSOP_WS_FORMAT":
        match = re.search(r'WS\d{2}[_\-](?:ME|GM|HU|BR)(\d{2})', path, re.I)
        if match:
            return int(match.group(1))

    # WSOP{YY}_{TYPE}{EP} format: WSOP13_ME01.mp4, WSOP14_ME07-FINAL.mxf
    if pattern_name == "WSOP_YEAR_ME":
        match = re.search(r'WSOP\d{2}[_\-](?:ME|BR|HR)(\d{2})', path, re.I)
        if match:
            return int(match.group(1))
        # Alternative: WSOP13_APAC_ME01
        match = re.search(r'WSOP\d{2}_\w+_(?:ME|BR|HR)(\d{2})', path, re.I)
        if match:
            return int(match.group(1))

    # Path-based patterns: WSOP_2003-01.mxf, WSOP_2005_01.mxf
    if pattern_name in ("WSOP_YEAR_DASH_EP", "WSOP_YEAR_UNDERSCORE_EP"):
        # Extract episode from WSOP_YYYY-NN or WSOP_YYYY_NN format
        match = re.search(r'WSOP_\d{4}[_\-](\d+)\.(?:mxf|mov|mp4)', path, re.I)
        if match:
            return int(match.group(1))

    # BOOM Era: 2009 WSOP ME01.mov
    if pattern_name == "BOOM_YEAR_WSOP_ME":
        match = re.search(r'\d{4}\s+WSOP\s+ME(\d+)', path, re.I)
        if match:
            return int(match.group(1))

    # BOOM Era: WSOP 2005 Show 10_xxx.mov
    if pattern_name == "BOOM_WSOP_YEAR_SHOW":
        match = re.search(r'WSOP\s+\d{4}\s+Show\s+(\d+)', path, re.I)
        if match:
            return int(match.group(1))

    # ESPN: ESPN 2007 WSOP SEASON 5 SHOW 1.mov
    if pattern_name == "ESPN_WSOP_SHOW":
        match = re.search(r'ESPN\s+\d{4}\s+WSOP.*SHOW\s+(\d+)', path, re.I)
        if match:
            return int(match.group(1))

    # BOOM Era: 2004 WSOP Show 13 ME 01.mov
    if pattern_name == "BOOM_YEAR_WSOP_SHOW":
        match = re.search(r'\d{4}\s+WSOP\s+Show\s+(\d+)', path, re.I)
        if match:
            return int(match.group(1))

    # WCLA/WP Player Emotion: WCLA23-PE-01.mkv, WP23-EP-02.mp4
    if pattern_name == "WCLA_PE_ET":
        match = re.search(r'W(?:CLA|P)\d{2}-(?:PE|ET|EP)-(\d+)', path, re.I)
        if match:
            return int(match.group(1))

    # PAD: pad-s12-ep01 or PAD_S13_EP01
    if pattern_name == "PAD":
        match = re.search(r'[Ee][Pp]?(\d{2})', path)
        if match:
            return int(match.group(1))

    # GOG: E01_GOG
    if pattern_name == "GOG":
        match = re.search(r'E(\d{2})[_\-]', path)
        if match:
            return int(match.group(1))

    # WSOP Archive: Show 1, _01.mxf
    if pattern_name == "WSOP_ARCHIVE_PRE2016":
        # Show number
        match = re.search(r'Show\s*(\d+)', path, re.I)
        if match:
            return int(match.group(1))
        # File number: _01.mxf, _1.mov
        match = re.search(r'[_\-](\d{1,2})\.(?:mxf|mov|mp4)', path, re.I)
        if match:
            ep = int(match.group(1))
            if ep < 50:
                return ep

    # WSOP Circuit LA: WCLA24-01
    if pattern_name == "WSOP_CIRCUIT_LA":
        match = re.search(r'WCLA\d{2}-(\d+)', path)
        if match:
            return int(match.group(1))

    # WSOP Europe: Episode_1, ME01
    if pattern_name in ("WSOP_BR_EU", "WSOP_BR_EU_2025"):
        match = re.search(r'Episode[_\s]?(\d+)', path, re.I)
        if match:
            return int(match.group(1))
        match = re.search(r'[_\-]ME(\d{2})[_\-]', path, re.I)
        if match:
            return int(match.group(1))

    # WSOPE format: WSOPE08_Episode_1_H264.mov
    if pattern_name == "WSOPE_EPISODE":
        match = re.search(r'WSOPE\d{2}_Episode_(\d+)', path, re.I)
        if match:
            return int(match.group(1))

    # WSOPE lowercase: wsope-2021-10k-me-ft-004.mp4
    if pattern_name == "WSOPE_LOWERCASE":
        match = re.search(r'wsope-\d{4}-\d+k?-[a-z]+-ft-(\d+)', path, re.I)
        if match:
            return int(match.group(1))

    # WSOP Bracelet LV: WS11_ME01_NB.mp4, WSOP13_ME01.mp4 등
    # 경로로 매칭되지만 파일명에서 episode 추출
    if pattern_name in ("WSOP_BR_LV", "WSOP_BR_LV_2025_ME", "WSOP_BR_LV_2025_SIDE"):
        # WS{YY}_{TYPE}{EP} format
        match = re.search(r'WS\d{2}[_\-](?:ME|GM|HU|BR)(\d{2})', path, re.I)
        if match:
            return int(match.group(1))
        # WSOP{YY}_{TYPE}{EP} format
        match = re.search(r'WSOP\d{2}[_\-](?:ME|BR|HR)(\d{2})', path, re.I)
        if match:
            return int(match.group(1))
        # WSOP{YY}_{REGION}_{TYPE}{EP} format: WSOP14_APAC_ME01
        match = re.search(r'WSOP\d{2}_\w+_(?:ME|BR|HR)(\d{2})', path, re.I)
        if match:
            return int(match.group(1))
        # WS{YY}_Show_{EP} format: WS12_Show_17
        match = re.search(r'WS\d{2}_Show_(\d+)', path, re.I)
        if match:
            return int(match.group(1))

    # P04 fix: Generic episode extraction for any pattern
    # Episode N, Ep N, Episode_N
    match = re.search(r'Episode[_\s]?(\d+)', path, re.I)
    if match:
        return int(match.group(1))

    # _MExx_, _01_
    match = re.search(r'[_\-]ME(\d{2})[_\-\.]', path, re.I)
    if match:
        return int(match.group(1))

    # wsope-2021-10k-me-ft-004.mp4 -> 004 at end before extension (P04 fix)
    match = re.search(r'-(\d{3})\.(?:mp4|mov|mxf)$', path, re.I)
    if match:
        return int(match.group(1))

    # File ending with _N or -N before extension
    match = re.search(r'[_\-](\d{1,2})\.(?:mp4|mov|mxf)$', path, re.I)
    if match:
        ep = int(match.group(1))
        if ep < 50:
            return ep

    # Day/Part → Episode mapping (MATCHING_RULES.md P10-A)
    day_part_episode = extract_episode_from_day_part(path)
    if day_part_episode:
        return day_part_episode

    return None


def extract_season_from_path(path: str) -> int | None:
    """Extract season number (PAD S12)."""
    match = re.search(r'[Ss](\d{2})', path)
    if match:
        return int(match.group(1))
    return None


def extract_region_from_super_circuit(path: str) -> str | None:
    """Extract region from WSOP Super Circuit path (London, Cyprus)."""
    if re.search(r'London', path, re.I):
        return "LONDON"
    if re.search(r'Cyprus', path, re.I):
        return "CYPRUS"
    return None


def detect_event_type_from_path(path: str) -> str | None:
    """Detect event type from path keywords.

    Checks both filename patterns and folder structure.
    Folder structure examples:
    - Z:\\ARCHIVE\\WSOP\\WSOP 2003\\Main Event\\WSOP_2003-01.mxf
    - Z:\\ARCHIVE\\WSOP\\WSOP 2005\\Bracelet\\WSOP_2005_01.mxf
    """
    # Main Event patterns (P03 fix - more patterns)
    # Check folder structure: \\Main Event\\ or /Main Event/
    if re.search(r'[/\\]Main\s*Event[/\\]', path, re.I):
        return "ME"
    if re.search(r'Main\s*Event', path, re.I):
        return "ME"
    if re.search(r'-me-', path, re.I):  # wsop-1973-me-nobug.mp4
        return "ME"
    if re.search(r'[_\-]ME\d', path):  # _ME01, -ME25
        return "ME"

    # BOOM Era (2003-2010): WSOP_YYYY-XX.mxf = Main Event episodes
    # Pattern: WSOP_2003-01.mxf, WSOP_2005-03.mxf
    boom_me_match = re.search(r'WSOP_(200[3-9]|2010)-\d+\.mxf', path, re.I)
    if boom_me_match:
        return "ME"

    # "World Series of Poker" in filename = Main Event (all eras)
    if re.search(r'World\s+Series\s+of\s+Poker', path, re.I):
        return "ME"

    # High Roller patterns
    if re.search(r'[/\\]High\s*Roller[/\\]', path, re.I):
        return "HR"
    if re.search(r'High\s*Roller', path, re.I):
        return "HR"
    if re.search(r'[_\-]HR\d', path):  # _HR01
        return "HR"

    # Heads Up patterns
    if re.search(r'[/\\]Heads\s*Up[/\\]', path, re.I):
        return "HU"
    if re.search(r'Heads\s*Up', path, re.I):
        return "HU"
    if re.search(r'[_\-]HU\d', path):  # _HU01
        return "HU"

    # Grudge Match patterns
    if re.search(r'[/\\]Grudge\s*Match[/\\]', path, re.I):
        return "GM"
    if re.search(r'Grudge\s*Match', path, re.I):
        return "GM"
    if re.search(r'[_\-]GM\d', path):  # _GM01
        return "GM"

    # Final Table patterns
    if re.search(r'[/\\]Final\s*Table[/\\]', path, re.I):
        return "FT"
    if re.search(r'Final\s*Table', path, re.I):
        return "FT"
    if re.search(r'-ft-', path, re.I):  # wsope-2021-10k-me-ft-004.mp4
        return "FT"

    # Bracelet events
    if re.search(r'[/\\]Bracelet[/\\]', path, re.I):
        return "BR"
    if re.search(r'Bracelet', path, re.I):
        return "BR"
    if re.search(r'[_\-]BR\d', path):  # _BR01
        return "BR"

    # Best Of patterns
    if re.search(r'[/\\]Best\s*Of[/\\]', path, re.I):
        return "BEST"
    if re.search(r'Best\s*Of', path, re.I):
        return "BEST"

    # CLASSIC Era: WSOP_YYYY or WSOP - YYYY without event type = Main Event (P03 fix)
    # Patterns: WSOP_2002.mxf, WSOP_2002_1.mxf, WSOP - 2002.mxf, WSOP - 1973 (1).avi
    classic_patterns = [
        r'WSOP[_\-\s]+(\d{4})\.',           # WSOP_2002.mxf
        r'WSOP[_\-\s]+(\d{4})[_\-]\d+\.',   # WSOP_2002_1.mxf, WSOP_2002-1.mxf
        r'WSOP[_\-\s]+(\d{4})\s*\(\d+\)\.',  # WSOP - 1973 (1).avi (복사본 패턴)
        r'(\d{4})\s+World\s+Series\s+of\s+Poker',  # 2002 World Series of Poker
    ]
    for pattern in classic_patterns:
        year_match = re.search(pattern, path, re.I)
        if year_match:
            year = int(year_match.group(1))
            if year <= 2002:  # CLASSIC Era - only Main Event
                return "ME"

    # CLASSIC Era fallback: 경로에 연도만 있고 WSOP 키워드가 있으면 ME (P03-B)
    # 예: Y:\WSOP backup\PRE-2003\1973\WSOP - 1973 (1).avi
    if 'WSOP' in path.upper() or 'PRE-' in path.upper():
        year_match = re.search(r'\b(19[7-9]\d|200[0-2])\b', path)
        if year_match:
            return "ME"

    return None


def extract_metadata(db: Session, full_path: str, filename: str = None) -> ExtractionResult:
    """Extract metadata from full path using patterns.

    Args:
        db: Database session
        full_path: Full path to parse (directory + filename)
        filename: Optional filename (for backward compatibility)

    Returns:
        ExtractionResult with extracted metadata
    """
    # Use full_path for matching (primary)
    match_target = full_path if full_path else filename

    # Get active patterns ordered by priority
    patterns = db.query(Pattern).filter(
        Pattern.is_active
    ).order_by(Pattern.priority).all()

    for pattern in patterns:
        try:
            # Match against full path (not just filename)
            match = re.search(pattern.regex, match_target, re.IGNORECASE)
            if match:
                result = ExtractionResult(
                    matched=True,
                    pattern_id=pattern.id,
                    pattern_name=pattern.name,
                )

                # Extract year
                if pattern.extract_year:
                    result.year = extract_year_from_path(match_target)

                # Extract region (fixed from pattern or dynamic)
                result.region_code = pattern.extract_region
                if not result.region_code and pattern.name == "WSOP_CIRCUIT_SUPER":
                    result.region_code = extract_region_from_super_circuit(match_target)

                # CRITICAL: Override region based on filename keywords (APAC, PARADISE, EUROPE)
                # This handles cases like WSOP13_APAC_ME01 in WSOP-LAS VEGAS folder
                filename_upper = (filename or match_target.split('\\')[-1].split('/')[-1]).upper()
                if '_APAC_' in filename_upper or 'APAC' in filename_upper:
                    result.region_code = 'APAC'
                elif '_PARADISE_' in filename_upper or 'PARADISE' in filename_upper:
                    result.region_code = 'PARADISE'
                elif 'WSOPE' in filename_upper or '_EU_' in filename_upper:
                    result.region_code = 'EU'

                if result.region_code:
                    result.region_id = get_region_id(db, result.region_code)

                # Extract event type (fixed from pattern or dynamic)
                result.event_type_code = pattern.extract_type
                if not result.event_type_code:
                    result.event_type_code = detect_event_type_from_path(match_target)
                if result.event_type_code:
                    result.event_type_id = get_event_type_id(db, result.event_type_code)

                # Extract episode
                if pattern.extract_episode:
                    result.episode = extract_episode_from_path(match_target, pattern.name)

                # Extract extended metadata
                result.stage = extract_stage_from_path(match_target)
                result.event_num = extract_event_num_from_path(match_target)
                result.buyin = extract_buyin_from_path(match_target)
                result.gtd = extract_gtd_from_path(match_target)
                result.version = extract_version_from_path(match_target)

                # CLASSIC Era Part extraction (1973-2002)
                result.part = extract_part_from_path(match_target, result.year)

                # PAD specific: season
                if pattern.name == "PAD":
                    result.season = extract_season_from_path(match_target)

                # Calculate confidence
                filled_fields = sum([
                    result.year is not None,
                    result.region_id is not None,
                    result.event_type_id is not None,
                    result.episode is not None,
                    result.stage is not None,
                ])
                result.confidence = min(1.0, 0.5 + (filled_fields * 0.1))

                return result
        except re.error:
            continue

    # No pattern matched - try basic extraction
    return extract_basic(db, match_target)


def extract_basic(db: Session, path: str) -> ExtractionResult:
    """Basic extraction without patterns."""
    result = ExtractionResult(matched=False, confidence=0.3)

    # Try to find year
    result.year = extract_year_from_path(path)

    # Try to find region
    if 'APAC' in path.upper():
        result.region_code = 'APAC'
    elif 'PARADISE' in path.upper():
        result.region_code = 'PARADISE'
    elif 'EUROPE' in path.upper() or 'EU' in path.upper():
        result.region_code = 'EU'
    elif 'LAS' in path.upper() and 'VEGAS' in path.upper():
        result.region_code = 'LV'

    if result.region_code:
        result.region_id = get_region_id(db, result.region_code)

    # Try to find event type
    result.event_type_code = detect_event_type_from_path(path)
    if result.event_type_code:
        result.event_type_id = get_event_type_id(db, result.event_type_code)

    # Extract extended fields
    result.stage = extract_stage_from_path(path)
    result.event_num = extract_event_num_from_path(path)
    result.buyin = extract_buyin_from_path(path)
    result.gtd = extract_gtd_from_path(path)
    result.version = extract_version_from_path(path)

    # CLASSIC Era Part extraction (1973-2002)
    result.part = extract_part_from_path(path, result.year)

    return result


def process_unmatched_files(db: Session) -> dict:
    """Process files without pattern match.

    Returns:
        Statistics about processing
    """
    stats = {
        'processed': 0,
        'matched': 0,
        'updated': 0,
    }

    # Get files without pattern match
    files = db.query(NasFile).filter(
        NasFile.matched_pattern_id is None
    ).all()

    stats['processed'] = len(files)

    for file in files:
        # Use full_path for better matching
        result = extract_metadata(db, file.full_path or file.directory, file.filename)

        if result.matched or result.year:
            stats['matched'] += 1

            # Update file
            updated = False
            if result.pattern_id and file.matched_pattern_id != result.pattern_id:
                file.matched_pattern_id = result.pattern_id
                updated = True
            if result.year and file.year != result.year:
                file.year = result.year
                updated = True
            if result.region_id and file.region_id != result.region_id:
                file.region_id = result.region_id
                updated = True
            if result.event_type_id and file.event_type_id != result.event_type_id:
                file.event_type_id = result.event_type_id
                updated = True
            if result.episode and file.episode != result.episode:
                file.episode = result.episode
                updated = True

            # Update extended fields
            if result.stage and file.stage != result.stage:
                file.stage = result.stage
                updated = True
            if result.event_num and file.event_num != result.event_num:
                file.event_num = result.event_num
                updated = True
            if result.season and file.season != result.season:
                file.season = result.season
                updated = True
            if result.buyin and file.buyin != result.buyin:
                file.buyin = result.buyin
                updated = True
            if result.gtd and file.gtd != result.gtd:
                file.gtd = result.gtd
                updated = True
            if result.version and file.version != result.version:
                file.version = result.version
                updated = True

            if result.confidence:
                file.extraction_confidence = result.confidence
                updated = True

            if updated:
                stats['updated'] += 1

    db.commit()
    return stats


def reprocess_all_files(db: Session) -> dict:
    """Reprocess all files with new patterns (full path matching).

    Returns:
        Statistics about processing
    """
    stats = {
        'processed': 0,
        'matched': 0,
        'updated': 0,
    }

    # Get all files
    files = db.query(NasFile).all()
    stats['processed'] = len(files)

    for file in files:
        # Skip manually overridden files
        if file.is_manual_override:
            continue

        # Use full_path for matching
        result = extract_metadata(db, file.full_path or file.directory, file.filename)

        # Update if pattern matched OR basic extraction found useful data
        has_useful_data = result.matched or result.year or result.event_type_id
        if has_useful_data:
            if result.matched:
                stats['matched'] += 1

            updated = False
            # Update all fields from extraction
            if result.pattern_id != file.matched_pattern_id:
                file.matched_pattern_id = result.pattern_id
                updated = True
            if result.year != file.year:
                file.year = result.year
                updated = True
            if result.region_id != file.region_id:
                file.region_id = result.region_id
                updated = True
            if result.event_type_id != file.event_type_id:
                file.event_type_id = result.event_type_id
                updated = True
            if result.episode != file.episode:
                file.episode = result.episode
                updated = True
            if result.stage != file.stage:
                file.stage = result.stage
                updated = True
            if result.event_num != file.event_num:
                file.event_num = result.event_num
                updated = True
            if result.season != file.season:
                file.season = result.season
                updated = True
            if result.buyin != file.buyin:
                file.buyin = result.buyin
                updated = True
            if result.gtd != file.gtd:
                file.gtd = result.gtd
                updated = True
            if result.version != file.version:
                file.version = result.version
                updated = True

            file.extraction_confidence = result.confidence

            if updated:
                stats['updated'] += 1

    db.commit()
    return stats


def run_pattern_extraction() -> dict:
    """Run pattern extraction on all unmatched files."""
    with get_db_context() as db:
        return process_unmatched_files(db)


def run_full_reprocess() -> dict:
    """Run full reprocess on all files."""
    with get_db_context() as db:
        return reprocess_all_files(db)

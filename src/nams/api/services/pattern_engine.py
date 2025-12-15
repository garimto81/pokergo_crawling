"""Pattern matching engine for extracting metadata from full paths."""
import re
from dataclasses import dataclass
from typing import Optional
from sqlalchemy.orm import Session

from ..database import Pattern, NasFile, Region, EventType, get_db_context


@dataclass
class ExtractionResult:
    """Result of pattern extraction."""
    matched: bool
    pattern_id: Optional[int] = None
    pattern_name: Optional[str] = None
    year: Optional[int] = None
    region_id: Optional[int] = None
    region_code: Optional[str] = None
    event_type_id: Optional[int] = None
    event_type_code: Optional[str] = None
    episode: Optional[int] = None
    confidence: float = 0.0

    # Extended metadata (new fields)
    stage: Optional[str] = None        # D1A, D2, FT, FINAL, S1
    event_num: Optional[int] = None    # Event #13 -> 13
    season: Optional[int] = None       # PAD S12 -> 12
    buyin: Optional[str] = None        # $100K, $5K
    gtd: Optional[str] = None          # $5M GTD -> 5M
    version: Optional[str] = None      # NC (No Commentary), NB, CLEAN


def get_region_id(db: Session, code: str) -> Optional[int]:
    """Get region ID by code."""
    if not code:
        return None
    region = db.query(Region).filter(Region.code == code.upper()).first()
    return region.id if region else None


def get_event_type_id(db: Session, code: str) -> Optional[int]:
    """Get event type ID by code."""
    if not code:
        return None
    # Normalize code
    code = code.upper().replace('_', '-')
    event_type = db.query(EventType).filter(EventType.code == code).first()
    return event_type.id if event_type else None


def extract_year_from_path(path: str) -> Optional[int]:
    """Extract year from full path."""
    # Try 4-digit year patterns
    patterns = [
        r'(\d{4})\s*WSOP',           # "2024 WSOP"
        r'WSOP[E]?\s*(\d{4})',       # "WSOP 2024", "WSOPE 2024"
        r'(\d{4})\s*MPP',            # "2025 MPP"
        r'WSOP.*?(\d{4})',           # Any WSOP followed by year
    ]
    for pattern in patterns:
        match = re.search(pattern, path, re.I)
        if match:
            year = int(match.group(1))
            if 1970 <= year <= 2030:
                return year

    # Try 2-digit year patterns
    patterns_2digit = [
        r'WSOPE?(\d{2})[_\-]',       # WSOPE08_, WS12-
        r'[_\-](\d{2})[_\-]',        # _08_, -12-
    ]
    for pattern in patterns_2digit:
        match = re.search(pattern, path, re.I)
        if match:
            y = int(match.group(1))
            year = 2000 + y if y < 50 else 1900 + y
            return year

    return None


def extract_stage_from_path(path: str) -> Optional[str]:
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


def extract_event_num_from_path(path: str) -> Optional[int]:
    """Extract event number (Event #13) from path."""
    match = re.search(r'Event\s*#?(\d+)', path, re.I)
    if match:
        return int(match.group(1))
    # Alternative: #10 in folder name
    match = re.search(r'#(\d+)\s', path)
    if match:
        return int(match.group(1))
    return None


def extract_buyin_from_path(path: str) -> Optional[str]:
    """Extract buy-in amount from path."""
    # $100K, $5K, $1.5K, $10,000
    match = re.search(r'\$(\d+(?:[.,]\d+)?[KM]?)', path, re.I)
    if match:
        buyin = match.group(1).replace(',', '')
        return buyin
    return None


def extract_gtd_from_path(path: str) -> Optional[str]:
    """Extract GTD amount from path."""
    match = re.search(r'\$(\d+[MK]?)\s*GTD', path, re.I)
    if match:
        return match.group(1)
    return None


def extract_version_from_path(path: str) -> Optional[str]:
    """Extract version info (No Commentary, Clean, etc.) from path."""
    if re.search(r'NO\s*COMMENTARY', path, re.I):
        return "NC"
    if re.search(r'_NB[_\.]', path, re.I):
        return "NB"
    if re.search(r'CLEAN', path, re.I):
        return "CLEAN"
    return None


def extract_episode_from_path(path: str, pattern_name: str) -> Optional[int]:
    """Extract episode number based on pattern type."""
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

    return None


def extract_season_from_path(path: str) -> Optional[int]:
    """Extract season number (PAD S12)."""
    match = re.search(r'[Ss](\d{2})', path)
    if match:
        return int(match.group(1))
    return None


def extract_region_from_super_circuit(path: str) -> Optional[str]:
    """Extract region from WSOP Super Circuit path (London, Cyprus)."""
    if re.search(r'London', path, re.I):
        return "LONDON"
    if re.search(r'Cyprus', path, re.I):
        return "CYPRUS"
    return None


def detect_event_type_from_path(path: str) -> Optional[str]:
    """Detect event type from path keywords."""
    if re.search(r'Main\s*Event', path, re.I):
        return "ME"
    if re.search(r'High\s*Roller', path, re.I):
        return "HR"
    if re.search(r'Heads\s*Up', path, re.I):
        return "HU"
    if re.search(r'Final\s*Table', path, re.I):
        return "FT"
    # Default for bracelet events
    if re.search(r'Bracelet', path, re.I):
        return "BR"
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
        Pattern.is_active == True
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
        NasFile.matched_pattern_id == None
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

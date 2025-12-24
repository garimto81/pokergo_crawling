"""Column mapping for Archive Metadata → Iconik_Full_Metadata."""

import re
from typing import Any

# Target 35 columns (Iconik_Full_Metadata structure)
TARGET_COLUMNS = [
    "id", "title",
    "time_start_ms", "time_end_ms", "time_start_S", "time_end_S",
    "Description", "ProjectName", "ProjectNameTag", "SearchTag",
    "Year_", "Location", "Venue", "EpisodeEvent",
    "Source", "Scene", "GameType", "PlayersTags",
    "HandGrade", "HANDTag", "EPICHAND", "Tournament",
    "PokerPlayTags", "Adjective", "Emotion", "AppearanceOutfit",
    "SceneryObject", "_gcvi_tags", "Badbeat", "Bluff",
    "Suckout", "Cooler", "RUNOUTTag", "PostFlop", "All-in",
]

# Source column patterns for multi-column fields
PLAYER_TAG_PATTERN = re.compile(r"Tag \(Player\)", re.IGNORECASE)
POKER_PLAY_TAG_PATTERN = re.compile(r"Tag \(Poker Play\)", re.IGNORECASE)
EMOTION_TAG_PATTERN = re.compile(r"Tag \(Emotion\)", re.IGNORECASE)


def parse_timecode(timecode: str) -> tuple[float | None, int | None]:
    """Parse timecode string (H:MM:SS or M:SS) to seconds and milliseconds.

    Args:
        timecode: Timecode string like "0:03:22" or "1:23:45"

    Returns:
        Tuple of (seconds, milliseconds)
    """
    if not timecode or not isinstance(timecode, str):
        return None, None

    timecode = timecode.strip()
    if not timecode:
        return None, None

    try:
        parts = timecode.split(":")
        if len(parts) == 3:
            hours, minutes, seconds = int(parts[0]), int(parts[1]), float(parts[2])
            total_seconds = hours * 3600 + minutes * 60 + seconds
        elif len(parts) == 2:
            minutes, seconds = int(parts[0]), float(parts[1])
            total_seconds = minutes * 60 + seconds
        else:
            return None, None

        milliseconds = int(total_seconds * 1000)
        return total_seconds, milliseconds
    except (ValueError, IndexError):
        return None, None


def convert_hand_grade(grade: str) -> str:
    """Convert star rating to numeric or standardized format.

    Args:
        grade: Hand grade like "★★★" or "★"

    Returns:
        Standardized grade string
    """
    if not grade:
        return ""

    # Count stars
    star_count = grade.count("★")
    if star_count > 0:
        return str(star_count)

    return grade


def extract_year_from_tab(tab_name: str) -> str:
    """Extract year from tab name.

    Args:
        tab_name: Tab name like "2024 WSOPC LA" or "WSOPE 2008-2013"

    Returns:
        Year string or empty
    """
    match = re.search(r"\b(19|20)\d{2}\b", tab_name)
    return match.group(0) if match else ""


def extract_location_from_tab(tab_name: str) -> str:
    """Extract location from tab name.

    Args:
        tab_name: Tab name like "2024 WSOPC LA" or "2025 WSOP Las Vegas"

    Returns:
        Location string
    """
    # Known location mappings
    locations = {
        "LA": "Los Angeles",
        "Las Vegas": "Las Vegas",
        "CYPRUS": "Cyprus",
        "Paradise": "Paradise",
    }

    tab_upper = tab_name.upper()
    for key, value in locations.items():
        if key.upper() in tab_upper:
            return value

    return ""


def extract_tournament_from_tab(tab_name: str) -> str:
    """Extract tournament name from tab name.

    Args:
        tab_name: Tab name like "2024 WSOPC LA" or "PAD S12,13"

    Returns:
        Tournament name
    """
    # Known tournament patterns
    if "WSOP" in tab_name.upper():
        if "WSOPC" in tab_name.upper():
            return "WSOP Circuit"
        elif "WSOPE" in tab_name.upper():
            return "WSOP Europe"
        elif "WSOPSC" in tab_name.upper():
            return "WSOP Super Circuit"
        else:
            return "WSOP"
    elif "PAD" in tab_name.upper():
        return "Poker After Dark"
    elif "MPP" in tab_name.upper():
        return "MPP"

    return ""


class ColumnMapper:
    """Maps source columns to target Iconik_Full_Metadata structure."""

    def __init__(self) -> None:
        pass

    def map_row(
        self,
        source_row: dict[str, Any],
        tab_name: str = "",
    ) -> dict[str, Any]:
        """Map a single source row to target structure.

        Args:
            source_row: Dict with source column names as keys
            tab_name: Name of the source tab (for metadata extraction)

        Returns:
            Dict with target column names as keys
        """
        result = {col: "" for col in TARGET_COLUMNS}

        # Direct mappings
        result["id"] = source_row.get("File No.", "")
        result["title"] = source_row.get("File Name", "")
        result["Source"] = source_row.get("Nas Folder Link", "")
        result["HANDTag"] = source_row.get("Hands", "")

        # Hand Grade conversion
        result["HandGrade"] = convert_hand_grade(
            source_row.get("Hand Grade", "")
        )

        # Timecode parsing
        time_in = source_row.get("In", "")
        time_out = source_row.get("Out", "")

        time_start_s, time_start_ms = parse_timecode(time_in)
        time_end_s, time_end_ms = parse_timecode(time_out)

        result["time_start_S"] = str(time_start_s) if time_start_s is not None else ""
        result["time_start_ms"] = str(time_start_ms) if time_start_ms is not None else ""
        result["time_end_S"] = str(time_end_s) if time_end_s is not None else ""
        result["time_end_ms"] = str(time_end_ms) if time_end_ms is not None else ""

        # Multi-column fields: collect all matching columns
        player_tags = []
        poker_play_tags = []
        emotion_tags = []

        for col_name, value in source_row.items():
            if not value or not isinstance(value, str):
                continue

            value = value.strip()
            if not value:
                continue

            if PLAYER_TAG_PATTERN.search(col_name):
                player_tags.append(value)
            elif POKER_PLAY_TAG_PATTERN.search(col_name):
                poker_play_tags.append(value)
            elif EMOTION_TAG_PATTERN.search(col_name):
                emotion_tags.append(value)

        # Include Winner in PlayersTags if present
        winner = source_row.get("Winner", "")
        if winner and winner.strip():
            if winner.strip() not in player_tags:
                player_tags.insert(0, winner.strip())

        result["PlayersTags"] = ",".join(player_tags) if player_tags else ""
        result["PokerPlayTags"] = ",".join(poker_play_tags) if poker_play_tags else ""
        result["Emotion"] = ",".join(emotion_tags) if emotion_tags else ""

        # Tab-derived metadata
        if tab_name:
            result["Year_"] = extract_year_from_tab(tab_name)
            result["Location"] = extract_location_from_tab(tab_name)
            result["Tournament"] = extract_tournament_from_tab(tab_name)

            # Description combining tab name and hands info
            hands = source_row.get("Hands", "")
            result["Description"] = f"{tab_name}: {hands}" if hands else tab_name

        return result

    def map_all(
        self,
        source_data: dict[str, list[dict]],
    ) -> list[dict[str, Any]]:
        """Map all source data to target structure.

        Args:
            source_data: Dict mapping tab names to list of row dicts

        Returns:
            List of mapped row dicts
        """
        result = []

        for tab_name, rows in source_data.items():
            for row in rows:
                mapped = self.map_row(row, tab_name)
                result.append(mapped)

        return result

    def get_mapping_summary(
        self,
        source_headers: list[str],
    ) -> dict[str, Any]:
        """Get a summary of how source columns map to target.

        Args:
            source_headers: List of source column names

        Returns:
            Dict with mapping statistics
        """
        # Direct mappings
        direct_mappings = {
            "File No.": "id",
            "File Name": "title",
            "In": "time_start_S, time_start_ms",
            "Out": "time_end_S, time_end_ms",
            "Nas Folder Link": "Source",
            "Hand Grade": "HandGrade",
            "Hands": "HANDTag",
            "Winner": "PlayersTags (included)",
        }

        # Pattern mappings
        pattern_mappings = {
            "Tag (Player)*": "PlayersTags (joined)",
            "Tag (Poker Play)*": "PokerPlayTags (joined)",
            "Tag (Emotion)*": "Emotion (joined)",
        }

        # Tab-derived mappings
        tab_derived = ["Year_", "Location", "Tournament", "Description"]

        mapped = []
        unmapped = []

        for header in source_headers:
            if header in direct_mappings:
                mapped.append((header, direct_mappings[header]))
            elif PLAYER_TAG_PATTERN.search(header):
                mapped.append((header, "PlayersTags"))
            elif POKER_PLAY_TAG_PATTERN.search(header):
                mapped.append((header, "PokerPlayTags"))
            elif EMOTION_TAG_PATTERN.search(header):
                mapped.append((header, "Emotion"))
            else:
                unmapped.append(header)

        return {
            "direct_mappings": direct_mappings,
            "pattern_mappings": pattern_mappings,
            "tab_derived": tab_derived,
            "mapped": mapped,
            "unmapped": unmapped,
            "coverage": len(mapped) / len(source_headers) * 100 if source_headers else 0,
        }

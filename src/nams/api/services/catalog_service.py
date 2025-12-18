"""Catalog service for generating standard titles for NAS groups."""
import re
from typing import Optional
from sqlalchemy.orm import Session

from ..database import AssetGroup, Region, EventType, get_db_context


# Event type display names
EVENT_TYPE_NAMES = {
    "ME": "Main Event",
    "GM": "Grudge Match",
    "HU": "Heads Up",
    "BR": "Bracelet Event",
    "HR": "High Roller",
    "FT": "Final Table",
    "TOC": "Tournament of Champions",
    "ONEDR": "One Drop",
    "PLO": "Pot Limit Omaha",
    "NLH": "No Limit Hold'em",
    "NLH6MAX": "No Limit Hold'em 6-Max",
    "PLATINUM": "Platinum High Roller",
    "DIAMOND": "Diamond High Roller",
}

# Region display names
REGION_NAMES = {
    "LV": "",  # Las Vegas is default, no suffix
    "EU": "Europe",
    "APAC": "APAC",
    "PARADISE": "Paradise",
    "ASIA": "Asia",
    "LONDON": "London",
    "CYPRUS": "Cyprus",
}

# D01 fix: Historic content without PokerGO data - auto-generate standard titles
HISTORIC_CONTENT_PATTERNS = {
    # WSOPE08 series (2008)
    r"WSOPE08_Episode_(\d+)": lambda m: f"WSOP Europe 2008 | Episode {int(m.group(1))}",
    # WSOPE09-10 series
    r"WSOPE(\d{2})_Episode_(\d+)": lambda m: f"WSOP Europe 20{m.group(1)} | Episode {int(m.group(2))}",
    # wsope-YYYY-XXk-type-ft-NNN pattern
    r"wsope-(\d{4})-(\d+k?)-([a-z]+)-ft-(\d+)": lambda m: f"WSOP Europe {m.group(1)} €{m.group(2).upper()} {m.group(3).upper()} | Final Table {int(m.group(4))}",
    # WSOP_YYYY for CLASSIC era
    r"WSOP[_\-](\d{4})\.": lambda m: f"WSOP {m.group(1)} Main Event" if int(m.group(1)) <= 2002 else None,
    # wsop-YYYY-me pattern
    r"wsop-(\d{4})-me": lambda m: f"WSOP {m.group(1)} Main Event",
}


def generate_title_from_filename(filename: str) -> Optional[str]:
    """Generate catalog title directly from filename patterns (D01 fix).

    This handles historic content that doesn't have PokerGO metadata.

    Args:
        filename: The filename to parse

    Returns:
        Generated title or None if no pattern matches
    """
    for pattern, generator in HISTORIC_CONTENT_PATTERNS.items():
        match = re.search(pattern, filename, re.I)
        if match:
            title = generator(match)
            if title:
                return title
    return None


def parse_group_id(group_id: str) -> dict:
    """Parse group_id into components.

    Formats:
    - 2011_ME_25 → year=2011, event_type=ME, episode=25
    - 2011_EU_01 → year=2011, region=EU, episode=1
    - 2013_APAC-ME_01 → year=2013, region=APAC, event_type=ME, episode=1
    - 1973_ME → year=1973, event_type=ME, episode=None (historic)
    - 2003_BEST-ALLINS → year=2003, event_type=BEST, subtype=ALLINS
    - 2024_BR_01 → year=2024, event_type=BR, episode=1
    """
    result = {
        "year": None,
        "region": None,
        "event_type": None,
        "episode": None,
        "subtype": None,
        "raw": group_id,
    }

    if not group_id:
        return result

    parts = group_id.split("_")

    # First part is always year
    if parts and parts[0].isdigit():
        result["year"] = int(parts[0])
        parts = parts[1:]

    if not parts:
        return result

    # Check for region-type pattern (APAC-ME)
    if "-" in parts[0] and not parts[0].startswith("BEST"):
        region_type = parts[0].split("-")
        result["region"] = region_type[0]
        if len(region_type) > 1:
            result["event_type"] = region_type[1]
        parts = parts[1:]
    # Check for BEST-* pattern
    elif parts[0].startswith("BEST-"):
        result["event_type"] = "BEST"
        result["subtype"] = parts[0].replace("BEST-", "")
        parts = parts[1:]
    # Check for region code (EU, APAC)
    elif parts[0] in REGION_NAMES:
        result["region"] = parts[0]
        parts = parts[1:]
    # Otherwise it's event type
    elif parts[0] in EVENT_TYPE_NAMES or parts[0] in ["BR", "ME", "GM", "HU"]:
        result["event_type"] = parts[0]
        parts = parts[1:]

    # Check for event type in remaining parts
    if parts and parts[0] in EVENT_TYPE_NAMES:
        result["event_type"] = parts[0]
        parts = parts[1:]

    # Remaining part is episode
    if parts:
        try:
            result["episode"] = int(parts[0])
        except ValueError:
            # Not a number, might be subtype
            if not result["subtype"]:
                result["subtype"] = parts[0]

    return result


def generate_catalog_title(group: AssetGroup, db: Session = None, filename: str = None) -> str:
    """Generate a standard catalog title for an asset group.

    Title patterns:
    - WSOP {YYYY} Main Event | Episode {N}
    - WSOP {YYYY} Main Event (historic, no episode)
    - WSOP Europe {YYYY} | Episode {N}
    - WSOP APAC {YYYY} Main Event | Show {N}
    - WSOP {YYYY} Best Of All-Ins
    - WSOP {YYYY} Bracelet Event #{N}

    Args:
        group: AssetGroup to generate title for
        db: Optional database session
        filename: Optional filename for D01 historic content patterns
    """
    # D01 fix: Try filename-based generation first for historic content
    if filename:
        title_from_filename = generate_title_from_filename(filename)
        if title_from_filename:
            return title_from_filename

    # Parse the group_id for components
    parsed = parse_group_id(group.group_id)

    year = group.year or parsed["year"]
    region = None
    event_type = None
    episode = group.episode or parsed["episode"]

    # Get region name from DB or parsed
    if db and group.region_id:
        region_obj = db.query(Region).filter(Region.id == group.region_id).first()
        if region_obj:
            region = REGION_NAMES.get(region_obj.code, region_obj.code)
    elif parsed["region"]:
        region = REGION_NAMES.get(parsed["region"], parsed["region"])

    # Get event type name from DB or parsed
    if db and group.event_type_id:
        event_type_obj = db.query(EventType).filter(EventType.id == group.event_type_id).first()
        if event_type_obj:
            event_type = EVENT_TYPE_NAMES.get(event_type_obj.code, event_type_obj.name)
    elif parsed["event_type"]:
        event_type = EVENT_TYPE_NAMES.get(parsed["event_type"], parsed["event_type"])

    # Build the title
    title_parts = ["WSOP"]

    # Add region if not LV
    if region:
        title_parts.append(region)

    # Add year
    if year:
        title_parts.append(str(year))

    # Handle BEST type specially
    if parsed["event_type"] == "BEST":
        subtype = parsed["subtype"] or "Highlights"
        # Convert subtype to readable form
        subtype_readable = subtype.replace("-", " ").replace("ALLINS", "All-Ins").title()
        title_parts.append(f"Best Of {subtype_readable}")
        return " ".join(title_parts)

    # Add event type
    if event_type:
        title_parts.append(event_type)

    # Build base title
    base_title = " ".join(title_parts)

    # Add episode/show number
    if episode:
        # APAC uses "Show" instead of "Episode"
        if parsed["region"] == "APAC":
            return f"{base_title} | Show {episode}"
        else:
            return f"{base_title} | Episode {episode}"

    return base_title


def generate_titles_for_unmatched(db: Session) -> dict:
    """Generate catalog titles for all unmatched groups (no PokerGO match).

    Returns:
        dict with statistics
    """
    # Get unmatched groups without catalog_title
    unmatched = db.query(AssetGroup).filter(
        AssetGroup.pokergo_episode_id == None,
        (AssetGroup.catalog_title == None) | (AssetGroup.catalog_title == ""),
        AssetGroup.catalog_title_manual == False
    ).all()

    generated = 0
    errors = []

    for group in unmatched:
        try:
            title = generate_catalog_title(group, db)
            if title:
                group.catalog_title = title
                generated += 1
        except Exception as e:
            errors.append({"group_id": group.group_id, "error": str(e)})

    db.commit()

    return {
        "total_unmatched": len(unmatched),
        "generated": generated,
        "errors": errors
    }


def generate_titles_for_all(db: Session, overwrite: bool = False) -> dict:
    """Generate catalog titles for all groups.

    Args:
        db: Database session
        overwrite: If True, overwrite existing titles (except manual)

    Returns:
        dict with statistics
    """
    if overwrite:
        groups = db.query(AssetGroup).filter(
            AssetGroup.catalog_title_manual == False
        ).all()
    else:
        groups = db.query(AssetGroup).filter(
            (AssetGroup.catalog_title == None) | (AssetGroup.catalog_title == ""),
            AssetGroup.catalog_title_manual == False
        ).all()

    generated = 0
    skipped = 0
    errors = []

    for group in groups:
        try:
            title = generate_catalog_title(group, db)
            if title:
                group.catalog_title = title
                generated += 1
            else:
                skipped += 1
        except Exception as e:
            errors.append({"group_id": group.group_id, "error": str(e)})

    db.commit()

    return {
        "total": len(groups),
        "generated": generated,
        "skipped": skipped,
        "errors": errors
    }


def update_catalog_title(db: Session, group_id: int, title: str, manual: bool = True) -> AssetGroup:
    """Update catalog title for a specific group.

    Args:
        db: Database session
        group_id: AssetGroup primary key ID
        title: New title
        manual: Mark as manually edited

    Returns:
        Updated AssetGroup
    """
    group = db.query(AssetGroup).filter(AssetGroup.id == group_id).first()
    if not group:
        raise ValueError(f"Group with id {group_id} not found")

    group.catalog_title = title
    group.catalog_title_manual = manual
    db.commit()
    db.refresh(group)

    return group

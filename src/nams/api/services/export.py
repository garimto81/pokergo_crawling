"""Export service for NAMS - Google Sheets and CSV export."""
import csv
import json
import re
from datetime import datetime
from io import StringIO
from pathlib import Path

from sqlalchemy.orm import Session

from ..database import AssetGroup, EventType, NasFile, PokergoEpisode, Region, get_db_context

# Export directory
EXPORT_DIR = Path("D:/AI/claude01/pokergo_crawling/data/exports")


def format_size(bytes_size: int) -> str:
    """Format bytes to human readable."""
    if not bytes_size:
        return "0 B"
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_size < 1024:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024
    return f"{bytes_size:.1f} PB"


def _generate_match_reason(group: AssetGroup) -> str:
    """Generate match reason based on group status."""
    year = group.year or 0

    # MATCHED - PokerGO 매칭됨
    if group.pokergo_episode_id:
        score = group.pokergo_match_score or 0
        if score >= 0.9:
            return f"[{year}] Exact key match (year+episode)"
        elif score >= 0.7:
            return f"[{year}] Fuzzy title match ({score:.0%})"
        else:
            return f"[{year}] Low confidence match ({score:.0%})"

    # NAS_ONLY_HISTORIC - 2011년 이전 (PokerGO 데이터 없음)
    if year and year < 2011:
        return f"[{year}] D01: PokerGO data not available (pre-2011)"

    # NAS_ONLY_MODERN - 2011년 이후인데 PokerGO 없음
    if year and year >= 2011:
        # 특수 케이스 확인
        region_id = group.region_id

        # Europe/APAC/Paradise 등은 PokerGO에 없을 수 있음
        if region_id and region_id > 1:  # LV가 아닌 경우
            return f"[{year}] D01: Non-LV region (limited PokerGO data)"

        return f"[{year}] M02: Match not found (review needed)"

    # 연도 정보 없음
    return "P02: Year extraction failed"


def get_groups_data(db: Session) -> list[dict]:
    """Get all groups with their files for export."""
    groups = db.query(AssetGroup).order_by(
        AssetGroup.year.desc(),
        AssetGroup.group_id
    ).all()

    # Get regions and event types for lookup
    regions = {r.id: r.code for r in db.query(Region).all()}
    event_types = {e.id: e.code for e in db.query(EventType).all()}

    result = []
    for g in groups:
        # Get files for this group
        files = db.query(NasFile).filter(
            NasFile.asset_group_id == g.id
        ).order_by(NasFile.role_priority).all()

        primary_file = next((f for f in files if f.role == 'primary'), None)
        backup_files = [f for f in files if f.role == 'backup']

        # Generate match reason
        match_reason = _generate_match_reason(g)

        result.append({
            "group_id": g.group_id,
            "year": g.year,
            "region": regions.get(g.region_id, ""),
            "event_type": event_types.get(g.event_type_id, ""),
            "episode": g.episode,
            "catalog_title": g.catalog_title or "",
            "match_category": g.match_category or "",
            "match_reason": match_reason,
            "primary_filename": primary_file.filename if primary_file else "",
            "primary_size": format_size(primary_file.size_bytes) if primary_file else "",
            "primary_path": primary_file.full_path if primary_file else "",
            "backup_count": len(backup_files),
            "backup_filenames": ", ".join(f.filename for f in backup_files),
            "total_size": format_size(g.total_size_bytes),
            "pokergo_matched": "Yes" if g.pokergo_episode_id else "No",
            "pokergo_title": g.pokergo_title or "",
            "pokergo_score": f"{g.pokergo_match_score:.2f}" if g.pokergo_match_score else "",
        })

    return result


def get_unmatched_pokergo_data(db: Session) -> list[dict]:
    """Get PokerGO episodes that are not matched to any NAS group."""
    # Get all matched episode IDs
    matched_ids = set(
        g.pokergo_episode_id
        for g in db.query(AssetGroup).filter(
            AssetGroup.pokergo_episode_id.isnot(None)
        ).all()
    )

    # Get unmatched episodes
    if matched_ids:
        unmatched = db.query(PokergoEpisode).filter(
            ~PokergoEpisode.id.in_(matched_ids)
        ).order_by(PokergoEpisode.collection_title, PokergoEpisode.title).all()
    else:
        unmatched = db.query(PokergoEpisode).order_by(
            PokergoEpisode.collection_title, PokergoEpisode.title
        ).all()

    result = []
    for ep in unmatched:
        # Extract year from title or collection
        year = None
        import re
        for text in [ep.title, ep.collection_title]:
            if text:
                match = re.search(r'\b(19|20)\d{2}\b', text)
                if match:
                    year = int(match.group())
                    break

        # Generate match reason for PokerGO Only
        if year and year < 2019:
            match_reason = f"[{year}] D02: PokerGO pre-2019 (collection may exist)"
        elif year and year >= 2019:
            match_reason = f"[{year}] D02: NAS file not available (collection needed)"
        else:
            match_reason = "D02: NAS file not available"

        result.append({
            "group_id": "",  # No NAS group
            "year": year or "",
            "region": "",
            "event_type": "",
            "episode": "",
            "catalog_title": "",  # No catalog title for unmatched PokerGO
            "match_category": "POKERGO_ONLY",
            "match_reason": match_reason,
            "primary_filename": "",
            "primary_size": "",
            "primary_path": "",
            "backup_count": "",
            "backup_filenames": "",
            "total_size": "",
            "pokergo_matched": "No NAS",  # Mark as no NAS file
            "pokergo_title": (ep.title or "").strip(),  # Remove trailing spaces
            "pokergo_score": "",
            # Additional PokerGO info
            "pokergo_id": ep.id,
            "pokergo_collection": ep.collection_title or "",
            "pokergo_season": ep.season_title or "",
            "pokergo_duration": f"{int(ep.duration_sec // 60)}min" if ep.duration_sec else "",
        })

    return result


def get_combined_export_data(db: Session) -> tuple[list[dict], list[dict]]:
    """Get combined NAS groups and unmatched PokerGO data.

    Returns:
        Tuple of (nas_groups, unmatched_pokergo)
    """
    nas_groups = get_groups_data(db)
    unmatched_pokergo = get_unmatched_pokergo_data(db)
    return nas_groups, unmatched_pokergo


def export_to_csv() -> str:
    """Export NAS groups + unmatched PokerGO to CSV file.

    Returns:
        Path to the exported CSV file
    """
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = EXPORT_DIR / f"nams_combined_{timestamp}.csv"

    with get_db_context() as db:
        nas_groups, unmatched_pokergo = get_combined_export_data(db)

    if not nas_groups and not unmatched_pokergo:
        return ""

    # Extended fieldnames for combined data
    fieldnames = [
        "group_id", "year", "region", "event_type", "episode", "catalog_title",
        "match_category", "match_reason",
        "primary_filename", "primary_size", "primary_path",
        "backup_count", "backup_filenames", "total_size",
        "pokergo_matched", "pokergo_title", "pokergo_score",
        "pokergo_id", "pokergo_collection", "pokergo_season", "pokergo_duration"
    ]

    # Write CSV
    with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()

        # Write NAS groups
        for g in nas_groups:
            writer.writerow(g)

        # Write separator
        if unmatched_pokergo:
            f.write("--- UNMATCHED POKERGO EPISODES ---\n")

        # Write unmatched PokerGO
        for p in unmatched_pokergo:
            writer.writerow(p)

    return str(output_path)


def export_to_json() -> str:
    """Export NAS groups + unmatched PokerGO to JSON file.

    Returns:
        Path to the exported JSON file
    """
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = EXPORT_DIR / f"nams_combined_{timestamp}.json"

    with get_db_context() as db:
        nas_groups, unmatched_pokergo = get_combined_export_data(db)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump({
            "exported_at": datetime.now().isoformat(),
            "summary": {
                "total_nas_groups": len(nas_groups),
                "nas_matched": sum(1 for g in nas_groups if g["pokergo_matched"] == "Yes"),
                "nas_unmatched": sum(1 for g in nas_groups if g["pokergo_matched"] == "No"),
                "pokergo_unmatched": len(unmatched_pokergo),
            },
            "nas_groups": nas_groups,
            "unmatched_pokergo": unmatched_pokergo,
        }, f, indent=2, ensure_ascii=False)

    return str(output_path)


def get_csv_content() -> str:
    """Get CSV content as string (for download) - NAS groups + unmatched PokerGO combined.

    Returns:
        CSV content as string
    """
    with get_db_context() as db:
        nas_groups, unmatched_pokergo = get_combined_export_data(db)

    if not nas_groups and not unmatched_pokergo:
        return ""

    # Extended fieldnames for combined data
    fieldnames = [
        "group_id", "year", "region", "event_type", "episode", "catalog_title",
        "match_category", "match_reason",
        "primary_filename", "primary_size", "primary_path",
        "backup_count", "backup_filenames", "total_size",
        "pokergo_matched", "pokergo_title", "pokergo_score",
        "pokergo_id", "pokergo_collection", "pokergo_season", "pokergo_duration"
    ]

    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction='ignore')
    writer.writeheader()

    # Write NAS groups
    for g in nas_groups:
        writer.writerow(g)

    # Write separator
    if unmatched_pokergo:
        output.write("--- UNMATCHED POKERGO EPISODES ---\n")

    # Write unmatched PokerGO
    for p in unmatched_pokergo:
        writer.writerow(p)

    return output.getvalue()


def get_google_sheets_data() -> list[list]:
    """Get data formatted for Google Sheets (NAS Groups + Unmatched PokerGO combined).

    Returns:
        List of rows (each row is a list of values)
    """
    with get_db_context() as db:
        nas_groups, unmatched_pokergo = get_combined_export_data(db)

    # Header row with additional PokerGO columns
    headers = [
        "Group ID", "Year", "Region", "Event Type", "Episode", "Catalog Title",
        "Match Category", "Match Reason",  # 4분류 + 원인 코드
        "Primary File", "Primary Size", "Primary Path",
        "Backup Count", "Backup Files", "Total Size",
        "PokerGO Matched", "PokerGO Title", "Match Score",
        "PokerGO ID", "PokerGO Collection", "PokerGO Season", "PokerGO Duration"
    ]

    rows = [headers]

    # Add NAS Groups
    for g in nas_groups:
        rows.append([
            g["group_id"],
            g["year"],
            g["region"],
            g["event_type"],
            g["episode"] or "",
            g["catalog_title"],
            g["match_category"],  # 4분류 카테고리
            g.get("match_reason", ""),  # 원인 코드
            g["primary_filename"],
            g["primary_size"],
            g["primary_path"],
            g["backup_count"],
            g["backup_filenames"],
            g["total_size"],
            g["pokergo_matched"],
            g["pokergo_title"],
            g["pokergo_score"],
            "",  # pokergo_id (only for unmatched)
            "",  # pokergo_collection
            "",  # pokergo_season
            "",  # pokergo_duration
        ])

    # Add separator row
    if unmatched_pokergo:
        rows.append(["--- UNMATCHED POKERGO EPISODES ---"] + [""] * (len(headers) - 1))

    # Add Unmatched PokerGO
    for p in unmatched_pokergo:
        rows.append([
            p["group_id"],
            p["year"],
            p["region"],
            p["event_type"],
            p["episode"],
            p["catalog_title"],  # Empty for unmatched PokerGO
            p["match_category"],  # POKERGO_ONLY
            p["match_reason"],  # D02: NAS file not available
            p["primary_filename"],
            p["primary_size"],
            p["primary_path"],
            p["backup_count"],
            p["backup_filenames"],
            p["total_size"],
            p["pokergo_matched"],
            p["pokergo_title"],
            p["pokergo_score"],
            p["pokergo_id"],
            p["pokergo_collection"],
            p["pokergo_season"],
            p["pokergo_duration"],
        ])

    return rows


def _is_origin_path(path: str) -> bool:
    """Check if path is Origin (Y: drive or 'origin' in directory)."""
    if not path:
        return False
    path_upper = path.upper()
    # Y: drive or 'ORIGIN' keyword (but not if ARCHIVE is also present)
    if 'ARCHIVE' in path_upper:
        return False
    return path_upper.startswith('Y:') or 'ORIGIN' in path_upper


def _is_archive_path(path: str) -> bool:
    """Check if path is Archive (Z: drive or 'archive' in path)."""
    if not path:
        return False
    path_upper = path.upper()
    return path_upper.startswith('Z:') or 'ARCHIVE' in path_upper


# Pre-compiled regex for year extraction
_YEAR_PATTERN = re.compile(r'\b(19|20)\d{2}\b')


def _extract_year_from_text(*texts: str) -> int | None:
    """Extract 4-digit year from text strings.

    Args:
        *texts: Variable text strings to search

    Returns:
        Year as int or None if not found
    """
    for text in texts:
        if text:
            match = _YEAR_PATTERN.search(text)
            if match:
                return int(match.group())
    return None


def get_full_matching_data(db: Session) -> tuple[list[dict], list[dict]]:
    """Get comprehensive matching data with Origin/Archive separation.

    Returns:
        Tuple of (nas_groups, unmatched_pokergo)
    """
    groups = db.query(AssetGroup).order_by(
        AssetGroup.year.desc(),
        AssetGroup.group_id
    ).all()

    # Get lookup tables
    regions = {r.id: r.code for r in db.query(Region).all()}
    event_types = {e.id: e.code for e in db.query(EventType).all()}

    # Get PokerGO episodes for collection info
    pokergo_episodes = {ep.id: ep for ep in db.query(PokergoEpisode).all()}

    nas_groups = []
    for g in groups:
        # Get files for this group
        files = db.query(NasFile).filter(
            NasFile.asset_group_id == g.id
        ).order_by(NasFile.role_priority).all()

        # Separate Origin and Archive files
        origin_files = []
        archive_files = []

        for f in files:
            file_info = {
                "filename": f.filename,
                "path": f.full_path,
                "size_bytes": f.size_bytes,
                "size_formatted": format_size(f.size_bytes),
                "role": f.role,
            }
            if _is_origin_path(f.full_path):
                origin_files.append(file_info)
            elif _is_archive_path(f.full_path):
                archive_files.append(file_info)

        # Get primary/backup for each location
        # Origin: use actual primary role
        origin_primary = next((f for f in origin_files if f["role"] == "primary"), None)
        origin_backups = [f for f in origin_files if f["role"] == "backup"]

        # Archive: all files are backup (primary was moved to Origin)
        # Use first file as representative, rest as backups
        archive_primary = archive_files[0] if archive_files else None
        archive_backups = archive_files[1:] if len(archive_files) > 1 else []

        # Get PokerGO info
        pokergo_collection = ""
        pokergo_season = ""
        pokergo_title = (g.pokergo_title or "").strip()

        if g.pokergo_episode_id and g.pokergo_episode_id in pokergo_episodes:
            ep = pokergo_episodes[g.pokergo_episode_id]
            pokergo_collection = (ep.collection_title or "").strip()
            pokergo_season = (ep.season_title or "").strip()
            pokergo_title = (ep.title or g.pokergo_title or "").strip()

        # Generate match reason
        match_reason = _generate_match_reason(g)

        nas_groups.append({
            "group_id": g.group_id,
            "year": g.year,
            "region": regions.get(g.region_id, ""),
            "event_type": event_types.get(g.event_type_id, ""),
            "episode": g.episode or "",
            "match_category": g.match_category or "",
            "match_reason": match_reason,
            # Origin files
            "origin_primary_path": origin_primary["path"] if origin_primary else "",
            "origin_primary_filename": origin_primary["filename"] if origin_primary else "",
            "origin_primary_size": origin_primary["size_formatted"] if origin_primary else "",
            "origin_backup_count": len(origin_backups),
            "origin_backup_files": ", ".join(f["filename"] for f in origin_backups),
            # Archive files
            "archive_primary_path": archive_primary["path"] if archive_primary else "",
            "archive_primary_filename": archive_primary["filename"] if archive_primary else "",
            "archive_primary_size": archive_primary["size_formatted"] if archive_primary else "",
            "archive_backup_count": len(archive_backups),
            "archive_backup_files": ", ".join(f["filename"] for f in archive_backups),
            # PokerGO info
            "pokergo_matched": "Yes" if g.pokergo_episode_id else "No",
            "pokergo_collection": pokergo_collection,
            "pokergo_season": pokergo_season,
            "pokergo_title": pokergo_title,
            "pokergo_score": f"{g.pokergo_match_score:.2f}" if g.pokergo_match_score else "",
            # Catalog
            "catalog_title": g.catalog_title or "",
            "total_size": format_size(g.total_size_bytes),
        })

    # Get unmatched PokerGO episodes
    matched_ids = set(
        g.pokergo_episode_id
        for g in db.query(AssetGroup).filter(
            AssetGroup.pokergo_episode_id.isnot(None)
        ).all()
    )

    if matched_ids:
        unmatched_episodes = db.query(PokergoEpisode).filter(
            ~PokergoEpisode.id.in_(matched_ids)
        ).order_by(PokergoEpisode.collection_title, PokergoEpisode.title).all()
    else:
        unmatched_episodes = db.query(PokergoEpisode).order_by(
            PokergoEpisode.collection_title, PokergoEpisode.title
        ).all()

    unmatched_pokergo = []
    for ep in unmatched_episodes:
        # Extract year from title or collection
        year = _extract_year_from_text(ep.title, ep.collection_title)

        # Generate match reason
        if year and year < 2019:
            match_reason = f"[{year}] D02: PokerGO pre-2019 (collection may exist)"
        elif year and year >= 2019:
            match_reason = f"[{year}] D02: NAS file not available (collection needed)"
        else:
            match_reason = "D02: NAS file not available"

        unmatched_pokergo.append({
            "group_id": "",
            "year": year or "",
            "region": "",
            "event_type": "",
            "episode": "",
            "match_category": "POKERGO_ONLY",
            "match_reason": match_reason,
            # Origin (empty)
            "origin_primary_path": "",
            "origin_primary_filename": "",
            "origin_primary_size": "",
            "origin_backup_count": "",
            "origin_backup_files": "",
            # Archive (empty)
            "archive_primary_path": "",
            "archive_primary_filename": "",
            "archive_primary_size": "",
            "archive_backup_count": "",
            "archive_backup_files": "",
            # PokerGO info
            "pokergo_matched": "No NAS",
            "pokergo_collection": (ep.collection_title or "").strip(),
            "pokergo_season": (ep.season_title or "").strip(),
            "pokergo_title": (ep.title or "").strip(),
            "pokergo_score": "",
            # Catalog
            "catalog_title": "",
            "total_size": "",
            # Additional
            "pokergo_id": ep.id,
            "pokergo_duration": f"{int(ep.duration_sec // 60)}min" if ep.duration_sec else "",
        })

    return nas_groups, unmatched_pokergo


def get_full_matching_sheets_data() -> list[list]:
    """Get data formatted for Google Sheets with Origin/Archive separation.

    Returns:
        List of rows (each row is a list of values)
    """
    with get_db_context() as db:
        nas_groups, unmatched_pokergo = get_full_matching_data(db)

    # Header row
    headers = [
        "Group ID", "Year", "Region", "Event Type", "Episode",
        "Match Category", "Match Reason",
        "Origin Primary Path", "Origin Primary Filename", "Origin Primary Size",
        "Origin Backup Count", "Origin Backup Files",
        "Archive Primary Path", "Archive Primary Filename", "Archive Primary Size",
        "Archive Backup Count", "Archive Backup Files",
        "PokerGO Matched", "PokerGO Collection", "PokerGO Season", "PokerGO Title",
        "Match Score", "Catalog Title", "Total Size",
    ]

    rows = [headers]

    # Add NAS Groups
    for g in nas_groups:
        rows.append([
            g["group_id"],
            g["year"],
            g["region"],
            g["event_type"],
            g["episode"],
            g["match_category"],
            g["match_reason"],
            g["origin_primary_path"],
            g["origin_primary_filename"],
            g["origin_primary_size"],
            g["origin_backup_count"],
            g["origin_backup_files"],
            g["archive_primary_path"],
            g["archive_primary_filename"],
            g["archive_primary_size"],
            g["archive_backup_count"],
            g["archive_backup_files"],
            g["pokergo_matched"],
            g["pokergo_collection"],
            g["pokergo_season"],
            g["pokergo_title"],
            g["pokergo_score"],
            g["catalog_title"],
            g["total_size"],
        ])

    # Add separator
    if unmatched_pokergo:
        rows.append(["--- UNMATCHED POKERGO EPISODES ---"] + [""] * (len(headers) - 1))

    # Add Unmatched PokerGO
    for p in unmatched_pokergo:
        rows.append([
            p["group_id"],
            p["year"],
            p["region"],
            p["event_type"],
            p["episode"],
            p["match_category"],
            p["match_reason"],
            p["origin_primary_path"],
            p["origin_primary_filename"],
            p["origin_primary_size"],
            p["origin_backup_count"],
            p["origin_backup_files"],
            p["archive_primary_path"],
            p["archive_primary_filename"],
            p["archive_primary_size"],
            p["archive_backup_count"],
            p["archive_backup_files"],
            p["pokergo_matched"],
            p["pokergo_collection"],
            p["pokergo_season"],
            p["pokergo_title"],
            p["pokergo_score"],
            p["catalog_title"],
            p["total_size"],
        ])

    return rows


def export_full_matching_to_sheets(sheet_name: str = "NAMS Full Matching") -> dict:
    """Export full matching data to Google Sheets.

    Args:
        sheet_name: Name of the sheet to create/update

    Returns:
        Dictionary with export result
    """
    if not GOOGLE_SHEETS_AVAILABLE:
        return {
            "success": False,
            "error": "Google Sheets API not available"
        }

    if not CREDENTIALS_PATH.exists():
        return {
            "success": False,
            "error": f"Credentials file not found: {CREDENTIALS_PATH}"
        }

    try:
        creds = Credentials.from_service_account_file(
            str(CREDENTIALS_PATH),
            scopes=['https://www.googleapis.com/auth/spreadsheets']
        )

        service = build('sheets', 'v4', credentials=creds)
        sheets = service.spreadsheets()

        # Get data
        data = get_full_matching_sheets_data()

        if not data:
            return {"success": False, "error": "No data to export"}

        # Check if sheet exists, create if not
        spreadsheet = sheets.get(spreadsheetId=GOOGLE_SHEETS_ID).execute()
        existing_sheets = [s['properties']['title'] for s in spreadsheet['sheets']]

        if sheet_name not in existing_sheets:
            sheets.batchUpdate(
                spreadsheetId=GOOGLE_SHEETS_ID,
                body={
                    "requests": [{
                        "addSheet": {
                            "properties": {"title": sheet_name}
                        }
                    }]
                }
            ).execute()

        # Clear existing data
        sheets.values().clear(
            spreadsheetId=GOOGLE_SHEETS_ID,
            range=f"'{sheet_name}'!A:Z"
        ).execute()

        # Write data
        result = sheets.values().update(
            spreadsheetId=GOOGLE_SHEETS_ID,
            range=f"'{sheet_name}'!A1",
            valueInputOption="RAW",
            body={"values": data}
        ).execute()

        return {
            "success": True,
            "spreadsheet_id": GOOGLE_SHEETS_ID,
            "sheet_name": sheet_name,
            "rows_updated": result.get("updatedRows", 0),
            "url": f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEETS_ID}/edit"
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


# Google Sheets API integration (requires credentials)
try:
    from google.oauth2.service_account import Credentials
    from googleapiclient.discovery import build
    GOOGLE_SHEETS_AVAILABLE = True
except ImportError:
    GOOGLE_SHEETS_AVAILABLE = False


GOOGLE_SHEETS_ID = "1h27Ha7pR-iYK_Gik8F4FfSvsk4s89sxk49CsU3XP_m4"
CREDENTIALS_PATH = Path("D:/AI/claude01/json/service_account_key.json")


def export_to_google_sheets(sheet_name: str = "NAMS Export") -> dict:
    """Export data to Google Sheets.

    Args:
        sheet_name: Name of the sheet to create/update

    Returns:
        Dictionary with export result
    """
    if not GOOGLE_SHEETS_AVAILABLE:
        return {
            "success": False,
            "error": (
                "Google Sheets API not available. "
                "Install: pip install google-api-python-client google-auth"
            )
        }

    if not CREDENTIALS_PATH.exists():
        return {
            "success": False,
            "error": f"Credentials file not found: {CREDENTIALS_PATH}",
            "help": "Create a service account and download credentials from Google Cloud Console"
        }

    try:
        # Load credentials
        creds = Credentials.from_service_account_file(
            str(CREDENTIALS_PATH),
            scopes=['https://www.googleapis.com/auth/spreadsheets']
        )

        # Build service
        service = build('sheets', 'v4', credentials=creds)
        sheets = service.spreadsheets()

        # Get data
        data = get_google_sheets_data()

        if not data:
            return {"success": False, "error": "No data to export"}

        # Check if sheet exists, create if not
        spreadsheet = sheets.get(spreadsheetId=GOOGLE_SHEETS_ID).execute()
        existing_sheets = [s['properties']['title'] for s in spreadsheet['sheets']]

        if sheet_name not in existing_sheets:
            # Create new sheet
            sheets.batchUpdate(
                spreadsheetId=GOOGLE_SHEETS_ID,
                body={
                    "requests": [{
                        "addSheet": {
                            "properties": {"title": sheet_name}
                        }
                    }]
                }
            ).execute()

        # Clear existing data
        sheets.values().clear(
            spreadsheetId=GOOGLE_SHEETS_ID,
            range=f"'{sheet_name}'!A:Z"
        ).execute()

        # Write data
        result = sheets.values().update(
            spreadsheetId=GOOGLE_SHEETS_ID,
            range=f"'{sheet_name}'!A1",
            valueInputOption="RAW",
            body={"values": data}
        ).execute()

        return {
            "success": True,
            "spreadsheet_id": GOOGLE_SHEETS_ID,
            "sheet_name": sheet_name,
            "rows_updated": result.get("updatedRows", 0),
            "url": f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEETS_ID}/edit#gid=0"
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

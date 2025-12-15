"""Export service for NAMS - Google Sheets and CSV export."""
import csv
import json
from pathlib import Path
from datetime import datetime
from io import StringIO

from sqlalchemy.orm import Session
from sqlalchemy import func

from ..database import (
    NasFile, AssetGroup, PokergoEpisode, Region, EventType,
    get_db_context
)


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

        result.append({
            "group_id": g.group_id,
            "year": g.year,
            "region": regions.get(g.region_id, ""),
            "event_type": event_types.get(g.event_type_id, ""),
            "episode": g.episode,
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


def export_to_csv() -> str:
    """Export groups data to CSV file.

    Returns:
        Path to the exported CSV file
    """
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = EXPORT_DIR / f"nams_groups_{timestamp}.csv"

    with get_db_context() as db:
        groups = get_groups_data(db)

    if not groups:
        return ""

    # Write CSV
    with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=groups[0].keys())
        writer.writeheader()
        writer.writerows(groups)

    return str(output_path)


def export_to_json() -> str:
    """Export groups data to JSON file.

    Returns:
        Path to the exported JSON file
    """
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = EXPORT_DIR / f"nams_groups_{timestamp}.json"

    with get_db_context() as db:
        groups = get_groups_data(db)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump({
            "exported_at": datetime.now().isoformat(),
            "total_groups": len(groups),
            "groups": groups
        }, f, indent=2, ensure_ascii=False)

    return str(output_path)


def get_csv_content() -> str:
    """Get CSV content as string (for download).

    Returns:
        CSV content as string
    """
    with get_db_context() as db:
        groups = get_groups_data(db)

    if not groups:
        return ""

    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=groups[0].keys())
    writer.writeheader()
    writer.writerows(groups)

    return output.getvalue()


def get_google_sheets_data() -> list[list]:
    """Get data formatted for Google Sheets.

    Returns:
        List of rows (each row is a list of values)
    """
    with get_db_context() as db:
        groups = get_groups_data(db)

    if not groups:
        return []

    # Header row
    headers = [
        "Group ID", "Year", "Region", "Event Type", "Episode",
        "Primary File", "Primary Size", "Primary Path",
        "Backup Count", "Backup Files", "Total Size",
        "PokerGO Matched", "PokerGO Title", "Match Score"
    ]

    rows = [headers]

    for g in groups:
        rows.append([
            g["group_id"],
            g["year"],
            g["region"],
            g["event_type"],
            g["episode"] or "",
            g["primary_filename"],
            g["primary_size"],
            g["primary_path"],
            g["backup_count"],
            g["backup_filenames"],
            g["total_size"],
            g["pokergo_matched"],
            g["pokergo_title"],
            g["pokergo_score"],
        ])

    return rows


# Google Sheets API integration (requires credentials)
try:
    from google.oauth2.service_account import Credentials
    from googleapiclient.discovery import build
    GOOGLE_SHEETS_AVAILABLE = True
except ImportError:
    GOOGLE_SHEETS_AVAILABLE = False


GOOGLE_SHEETS_ID = "1h27Ha7pR-iYK_Gik8F4FfSvsk4s89sxk49CsU3XP_m4"
CREDENTIALS_PATH = Path("D:/AI/claude01/pokergo_crawling/credentials/google-sheets-credentials.json")


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
            "error": "Google Sheets API not available. Install: pip install google-api-python-client google-auth"
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

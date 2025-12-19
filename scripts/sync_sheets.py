"""Google Sheets sync script for NAMS Validator.

변경사항만 Google Sheets에 부분 업데이트하는 스크립트.

Usage:
    python scripts/sync_sheets.py
    python scripts/sync_sheets.py --full  # 전체 재동기화
    python scripts/sync_sheets.py --sheet "Master_Catalog"
"""
import argparse
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Google Sheets API
try:
    from google.oauth2.service_account import Credentials
    from googleapiclient.discovery import build
    GOOGLE_SHEETS_AVAILABLE = True
except ImportError:
    GOOGLE_SHEETS_AVAILABLE = False

from sqlalchemy import func  # noqa: E402

from src.nams.api.database import (  # noqa: E402
    AuditLog,
    CategoryEntry,
    ScanHistory,
    get_db_context,
)
from src.nams.api.services.export import (  # noqa: E402
    CREDENTIALS_PATH,
    GOOGLE_SHEETS_ID,
    get_google_sheets_data,
)


def get_sheets_service():
    """Get Google Sheets API service."""
    if not GOOGLE_SHEETS_AVAILABLE:
        raise RuntimeError(
            "Google Sheets API not available. "
            "Install: pip install google-api-python-client google-auth"
        )

    if not CREDENTIALS_PATH.exists():
        raise RuntimeError(f"Credentials file not found: {CREDENTIALS_PATH}")

    creds = Credentials.from_service_account_file(
        str(CREDENTIALS_PATH),
        scopes=['https://www.googleapis.com/auth/spreadsheets']
    )
    service = build('sheets', 'v4', credentials=creds)
    return service.spreadsheets()


def get_recent_changes(db, since: datetime = None) -> dict:
    """Get recently changed entries for incremental sync.

    Args:
        db: Database session
        since: Cutoff datetime (default: last 24h)

    Returns:
        Dict with changed entries info
    """
    if since is None:
        # Default to last scan completion time
        last_scan = db.query(ScanHistory).filter(
            ScanHistory.status == 'completed'
        ).order_by(ScanHistory.completed_at.desc()).first()

        if last_scan and last_scan.completed_at:
            since = last_scan.completed_at
        else:
            # Fallback to 24h ago
            since = datetime.utcnow().replace(hour=0, minute=0, second=0)

    # Get changed entries from audit log
    changed_entry_ids = db.query(AuditLog.entity_id).filter(
        AuditLog.entity_type == 'category_entry',
        AuditLog.changed_at >= since,
    ).distinct().all()

    # Get changed file IDs
    changed_file_ids = db.query(AuditLog.entity_id).filter(
        AuditLog.entity_type == 'nas_file',
        AuditLog.changed_at >= since,
    ).distinct().all()

    return {
        'since': since.isoformat() if since else None,
        'changed_entries': [id[0] for id in changed_entry_ids],
        'changed_files': [id[0] for id in changed_file_ids],
        'total_changes': len(changed_entry_ids) + len(changed_file_ids),
    }


def sync_changes_to_sheets(
    sheet_name: str = "Master_Catalog",
    full_sync: bool = False
) -> dict:
    """Sync changes to Google Sheets.

    Args:
        sheet_name: Name of the sheet to update
        full_sync: If True, do full resync instead of incremental

    Returns:
        Sync result dict
    """
    print(f"[Sync Sheets] Starting {'full' if full_sync else 'incremental'} sync to '{sheet_name}'")

    result = {
        'status': 'pending',
        'sheet_name': sheet_name,
        'sync_type': 'full' if full_sync else 'incremental',
        'rows_updated': 0,
        'started_at': datetime.utcnow().isoformat(),
    }

    try:
        sheets = get_sheets_service()

        with get_db_context() as db:
            if not full_sync:
                # Check if there are any changes
                changes = get_recent_changes(db)
                if changes['total_changes'] == 0:
                    print("[Sync Sheets] No changes detected, skipping sync")
                    result['status'] = 'skipped'
                    result['reason'] = 'No changes since last sync'
                    return result

                total = changes['total_changes']
                since = changes['since']
                print(f"[Sync Sheets] Found {total} changes since {since}")

            # Get data for export
            print("[Sync Sheets] Fetching data...")
            data = get_google_sheets_data()

            if not data:
                result['status'] = 'failed'
                result['error'] = 'No data to export'
                return result

        # Check/create sheet
        spreadsheet = sheets.get(spreadsheetId=GOOGLE_SHEETS_ID).execute()
        existing_sheets = [s['properties']['title'] for s in spreadsheet['sheets']]

        if sheet_name not in existing_sheets:
            print(f"[Sync Sheets] Creating new sheet: {sheet_name}")
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

        # Clear and update
        print(f"[Sync Sheets] Updating {len(data)} rows...")
        sheets.values().clear(
            spreadsheetId=GOOGLE_SHEETS_ID,
            range=f"'{sheet_name}'!A:Z"
        ).execute()

        update_result = sheets.values().update(
            spreadsheetId=GOOGLE_SHEETS_ID,
            range=f"'{sheet_name}'!A1",
            valueInputOption="RAW",
            body={"values": data}
        ).execute()

        result['status'] = 'completed'
        result['rows_updated'] = update_result.get('updatedRows', 0)
        result['completed_at'] = datetime.utcnow().isoformat()
        result['url'] = f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEETS_ID}/edit"

        print(f"[Sync Sheets] Completed: {result['rows_updated']} rows updated")

    except Exception as e:
        result['status'] = 'failed'
        result['error'] = str(e)
        print(f"[Sync Sheets] Failed: {e}")

    return result


def sync_multiple_sheets(sheets_config: list[dict], full_sync: bool = False) -> list[dict]:
    """Sync multiple sheets.

    Args:
        sheets_config: List of sheet configs [{"name": "Sheet1", "data_fn": callable}, ...]
        full_sync: If True, do full resync

    Returns:
        List of sync results
    """
    results = []

    for config in sheets_config:
        sheet_name = config.get('name', 'Unnamed')
        result = sync_changes_to_sheets(sheet_name=sheet_name, full_sync=full_sync)
        results.append(result)

    return results


def get_sync_status() -> dict:
    """Get current sync status and stats."""
    with get_db_context() as db:
        # Last successful sync (from scan history)
        last_scan = db.query(ScanHistory).filter(
            ScanHistory.status == 'completed'
        ).order_by(ScanHistory.completed_at.desc()).first()

        # Pending changes
        changes = get_recent_changes(db) if last_scan else {'total_changes': 0}

        # Total entries
        total_entries = db.query(func.count(CategoryEntry.id)).scalar() or 0
        verified_entries = db.query(func.count(CategoryEntry.id)).filter(
            CategoryEntry.verified.is_(True)
        ).scalar() or 0

        last_sync_time = None
        if last_scan and last_scan.completed_at:
            last_sync_time = last_scan.completed_at.isoformat()

        rate = 0
        if total_entries > 0:
            rate = round(verified_entries / total_entries * 100, 1)

        return {
            'last_sync': last_sync_time,
            'pending_changes': changes['total_changes'],
            'total_entries': total_entries,
            'verified_entries': verified_entries,
            'verification_rate': rate,
        }


def main():
    parser = argparse.ArgumentParser(description='NAMS Google Sheets Sync Script')
    parser.add_argument(
        '--full',
        action='store_true',
        help='Do full resync instead of incremental'
    )
    parser.add_argument(
        '--sheet',
        default='Master_Catalog',
        help='Sheet name to sync (default: Master_Catalog)'
    )
    parser.add_argument(
        '--status',
        action='store_true',
        help='Show sync status and exit'
    )

    args = parser.parse_args()

    if args.status:
        status = get_sync_status()
        print("\n" + "=" * 50)
        print("[Sync Status]")
        print("=" * 50)
        print(f"  Last sync: {status['last_sync'] or 'Never'}")
        print(f"  Pending changes: {status['pending_changes']}")
        print(f"  Total entries: {status['total_entries']}")
        print(f"  Verified: {status['verified_entries']} ({status['verification_rate']}%)")
        print("=" * 50)
        return

    try:
        result = sync_changes_to_sheets(
            sheet_name=args.sheet,
            full_sync=args.full,
        )

        print("\n" + "=" * 50)
        print("[Sync Result]")
        print("=" * 50)
        print(f"  Status: {result['status']}")
        print(f"  Sheet: {result['sheet_name']}")
        print(f"  Type: {result['sync_type']}")
        if result.get('rows_updated'):
            print(f"  Rows updated: {result['rows_updated']}")
        if result.get('url'):
            print(f"  URL: {result['url']}")
        if result.get('error'):
            print(f"  Error: {result['error']}")
        print("=" * 50)

        sys.exit(0 if result['status'] in ('completed', 'skipped') else 1)

    except Exception as e:
        print(f"[Sync Sheets] Fatal error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()

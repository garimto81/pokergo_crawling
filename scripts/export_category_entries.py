#!/usr/bin/env python
"""Export CategoryEntry data to Google Sheets.

Phase 5: Category 기반 내보내기
- Sheet 1: Category 목록
- Sheet 2: Entry 목록 (전체)
- Sheet 3: PARTIAL (검증 필요)
- Sheet 4: NONE (NAS Only)
"""
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

from src.nams.api.database import get_db_context
from src.nams.api.database.models import Category, CategoryEntry, NasFile
from sqlalchemy import func

GOOGLE_SHEETS_ID = '1h27Ha7pR-iYK_Gik8F4FfSvsk4s89sxk49CsU3XP_m4'
CREDENTIALS_PATH = Path('D:/AI/claude01/json/service_account_key.json')


def format_size(bytes_size: int) -> str:
    """Format bytes to GB."""
    if not bytes_size:
        return ""
    gb = bytes_size / (1024**3)
    return f"{gb:.2f}"


def get_sheets_service():
    """Get Google Sheets API service."""
    credentials = Credentials.from_service_account_file(
        str(CREDENTIALS_PATH),
        scopes=['https://www.googleapis.com/auth/spreadsheets']
    )
    return build('sheets', 'v4', credentials=credentials)


def ensure_sheet_exists(service, sheet_name: str):
    """Ensure sheet exists, create if not."""
    try:
        # Get spreadsheet metadata
        spreadsheet = service.spreadsheets().get(spreadsheetId=GOOGLE_SHEETS_ID).execute()
        sheets = [s['properties']['title'] for s in spreadsheet.get('sheets', [])]

        if sheet_name not in sheets:
            # Create new sheet
            service.spreadsheets().batchUpdate(
                spreadsheetId=GOOGLE_SHEETS_ID,
                body={
                    'requests': [{
                        'addSheet': {
                            'properties': {'title': sheet_name}
                        }
                    }]
                }
            ).execute()
            print(f"  [Created] Sheet: {sheet_name}")
    except Exception as e:
        print(f"  [WARN] Sheet check failed: {e}")


def clear_and_write_sheet(service, sheet_name: str, data: list[list]):
    """Clear sheet and write data."""
    ensure_sheet_exists(service, sheet_name)

    try:
        service.spreadsheets().values().clear(
            spreadsheetId=GOOGLE_SHEETS_ID,
            range=f"'{sheet_name}'!A:Z"
        ).execute()
    except Exception:
        pass  # Sheet might be empty

    service.spreadsheets().values().update(
        spreadsheetId=GOOGLE_SHEETS_ID,
        range=f"'{sheet_name}'!A1",
        valueInputOption='RAW',
        body={'values': data}
    ).execute()

    print(f"  [OK] {sheet_name}: {len(data) - 1} rows")


def main():
    """Main export function."""
    print("=" * 60)
    print("Phase 5: Category Entry Export to Google Sheets")
    print("=" * 60)

    service = get_sheets_service()

    with get_db_context() as db:
        # KPI Summary
        total_entries = db.query(CategoryEntry).count()
        total_files = db.query(NasFile).count()
        exact = db.query(CategoryEntry).filter(CategoryEntry.match_type == 'EXACT').count()
        partial = db.query(CategoryEntry).filter(CategoryEntry.match_type == 'PARTIAL').count()
        none = db.query(CategoryEntry).filter(CategoryEntry.match_type == 'NONE').count()
        pokergo = db.query(CategoryEntry).filter(CategoryEntry.source == 'POKERGO').count()

        print(f"\n[Summary]")
        print(f"  Total Entries: {total_entries}")
        print(f"  EXACT: {exact}, PARTIAL: {partial}, NONE: {none}")
        print(f"  PokerGO: {pokergo} ({pokergo/total_entries*100:.1f}%)")

        # Sheet 1: Categories
        print("\n[Sheet 1] Categories")
        categories = db.query(Category).order_by(Category.year.desc()).all()
        cat_data = [['ID', 'Code', 'Name', 'Year', 'Region', 'Source', 'PokerGO Category', 'Entries', 'Files']]
        for cat in categories:
            entry_count = db.query(CategoryEntry).filter(CategoryEntry.category_id == cat.id).count()
            file_count = db.query(NasFile).join(CategoryEntry).filter(CategoryEntry.category_id == cat.id).count()
            cat_data.append([
                cat.id,
                cat.code,
                cat.name,
                cat.year,
                cat.region or '',
                cat.source or '',
                cat.pokergo_category or '',
                entry_count,
                file_count,
            ])
        clear_and_write_sheet(service, 'Categories', cat_data)

        # Sheet 2: All Entries
        print("\n[Sheet 2] All Entries")
        entries = db.query(CategoryEntry).order_by(
            CategoryEntry.year.desc(),
            CategoryEntry.sequence
        ).all()

        entry_data = [[
            'ID', 'Entry Code', 'Display Title', 'PokerGO Title',
            'Year', 'Event Type', 'Sequence', 'Match Type', 'Score',
            'Source', 'Verified', 'Files', 'Size (GB)'
        ]]
        for e in entries:
            entry_data.append([
                e.id,
                e.entry_code,
                e.display_title or '',
                e.pokergo_title or '',
                e.year,
                e.event_type or '',
                e.sequence or '',
                e.match_type or '',
                f"{e.match_score:.2f}" if e.match_score else '',
                e.source or '',
                'Yes' if e.verified else 'No',
                e.file_count or 0,
                format_size(e.total_size_bytes),
            ])
        clear_and_write_sheet(service, 'All_Entries', entry_data)

        # Sheet 3: PARTIAL (Needs Review)
        print("\n[Sheet 3] PARTIAL (Needs Review)")
        partial_entries = db.query(CategoryEntry).filter(
            CategoryEntry.match_type == 'PARTIAL',
            CategoryEntry.verified == False
        ).order_by(CategoryEntry.match_score.desc()).all()

        partial_data = [[
            'ID', 'Entry Code', 'NAS Title', 'PokerGO Title',
            'Year', 'Score', 'Files', 'Action'
        ]]
        for e in partial_entries:
            partial_data.append([
                e.id,
                e.entry_code,
                e.display_title or '',
                e.pokergo_title or '',
                e.year,
                f"{e.match_score:.2f}" if e.match_score else '',
                e.file_count or 0,
                '',  # Action column for manual review
            ])
        clear_and_write_sheet(service, 'PARTIAL_Review', partial_data)

        # Sheet 4: NONE (NAS Only)
        print("\n[Sheet 4] NONE (NAS Only)")
        none_entries = db.query(CategoryEntry).filter(
            CategoryEntry.match_type == 'NONE'
        ).order_by(CategoryEntry.year.desc()).all()

        none_data = [[
            'ID', 'Entry Code', 'Generated Title', 'Year', 'Event Type',
            'Sequence', 'Files', 'Size (GB)'
        ]]
        for e in none_entries:
            none_data.append([
                e.id,
                e.entry_code,
                e.display_title or '',
                e.year,
                e.event_type or '',
                e.sequence or '',
                e.file_count or 0,
                format_size(e.total_size_bytes),
            ])
        clear_and_write_sheet(service, 'NONE_NAS_Only', none_data)

        # Sheet 5: Files with Entry
        print("\n[Sheet 5] Files with Entry")
        files = db.query(NasFile).filter(
            NasFile.entry_id.isnot(None),
            NasFile.is_excluded == False
        ).limit(1000).all()  # Limit for performance

        file_data = [[
            'File ID', 'Filename', 'Drive', 'Folder', 'Size (GB)',
            'Entry Code', 'Display Title', 'Match Type', 'Role'
        ]]
        for f in files:
            entry = db.query(CategoryEntry).filter(CategoryEntry.id == f.entry_id).first()
            file_data.append([
                f.file_id or '',
                f.filename,
                f.drive or '',
                f.folder or '',
                format_size(f.size_bytes),
                entry.entry_code if entry else '',
                entry.display_title if entry else '',
                entry.match_type if entry else '',
                f.role or '',
            ])
        clear_and_write_sheet(service, 'Files_Mapped', file_data)

    print("\n" + "=" * 60)
    print(f"[SUCCESS] Export complete!")
    print(f"Sheet URL: https://docs.google.com/spreadsheets/d/{GOOGLE_SHEETS_ID}")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())

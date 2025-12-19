"""Daily NAS scan script for NAMS Validator.

Windows Task Scheduler로 매일 03:00에 실행되는 일일 스캔 스크립트.

Usage:
    python scripts/daily_scan.py --mode daily
    python scripts/daily_scan.py --mode full --drives Y:,Z:,X:
    python scripts/daily_scan.py --mode daily --sync-sheets
"""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.nams.api.database import NasFile, ScanHistory, get_db_context  # noqa: E402
from src.nams.api.services.scanner import (  # noqa: E402
    FolderType,
    ScanConfig,
    ScanMode,
    run_scan,
    scan_directory,
)


def create_scan_history(db, scan_type: str, drives: str) -> ScanHistory:
    """Create a new ScanHistory record."""
    scan_history = ScanHistory(
        scan_type=scan_type,
        started_at=datetime.utcnow(),
        status='running',
        scanned_drives=drives,
    )
    db.add(scan_history)
    db.commit()
    db.refresh(scan_history)
    return scan_history


def update_scan_history(
    db, scan_history: ScanHistory, stats: dict,
    status: str = 'completed', error: str = None
):
    """Update ScanHistory with results."""
    scan_history.completed_at = datetime.utcnow()
    scan_history.status = status
    scan_history.new_files = stats.get('new_files', 0)
    scan_history.updated_files = stats.get('updated_files', 0)
    scan_history.missing_files = stats.get('missing_files', 0)
    scan_history.path_changes = stats.get('path_changes', 0)
    scan_history.total_files_scanned = stats.get('total_scanned', 0)
    scan_history.total_size_scanned = stats.get('total_size_bytes', 0)
    if error:
        scan_history.error_message = error
    db.commit()


def detect_path_changes(db, scanned_files: dict[str, dict]) -> dict:
    """Detect path changes for existing files.

    Args:
        db: Database session
        scanned_files: Dict of {file_id: file_info} from current scan

    Returns:
        Stats dict with path_changes count
    """
    stats = {'path_changes': 0, 'changes': []}

    # Get existing files by file_id
    existing_files = db.query(NasFile).filter(
        NasFile.file_id.in_(scanned_files.keys())
    ).all()

    for nas_file in existing_files:
        current_scan = scanned_files.get(nas_file.file_id)
        if not current_scan:
            continue

        new_path = current_scan.get('full_path')
        if nas_file.full_path != new_path:
            # Path changed - update history
            old_history = []
            if nas_file.path_history:
                try:
                    old_history = json.loads(nas_file.path_history)
                except json.JSONDecodeError:
                    old_history = []

            change_record = {
                'old_path': nas_file.full_path,
                'new_path': new_path,
                'changed_at': datetime.utcnow().isoformat(),
            }
            old_history.append(change_record)

            nas_file.path_history = json.dumps(old_history)
            nas_file.full_path = new_path
            nas_file.directory = current_scan.get('directory', '')

            stats['path_changes'] += 1
            if len(stats['changes']) < 10:
                stats['changes'].append({
                    'file_id': nas_file.file_id,
                    'old': change_record['old_path'],
                    'new': new_path,
                })

    db.commit()
    return stats


def detect_missing_files(db, current_scan_paths: set[str]) -> dict:
    """Detect files that are no longer present on disk.

    Args:
        db: Database session
        current_scan_paths: Set of full_path values from current scan

    Returns:
        Stats dict with missing_files count
    """
    stats = {'missing_files': 0, 'missing': []}

    # Get files not in current scan (and not already marked as missing/excluded)
    all_db_files = db.query(NasFile).filter(
        NasFile.is_excluded.is_(False)
    ).all()

    for nas_file in all_db_files:
        if nas_file.full_path not in current_scan_paths:
            # File is missing - update last_seen_at if not already set
            if nas_file.last_seen_at is None:
                nas_file.last_seen_at = datetime.utcnow()
                stats['missing_files'] += 1
                if len(stats['missing']) < 10:
                    stats['missing'].append({
                        'file_id': nas_file.file_id,
                        'path': nas_file.full_path,
                    })

    db.commit()
    return stats


def run_daily_scan(
    mode: str = 'daily',
    drives: str = 'Y:,Z:,X:',
    sync_sheets: bool = False
) -> dict:
    """Run daily scan with change tracking.

    Args:
        mode: 'daily' (incremental) or 'full'
        drives: Comma-separated drive list
        sync_sheets: Whether to sync to Google Sheets after scan

    Returns:
        Scan statistics
    """
    print(f"[Daily Scan] Starting {mode} scan at {datetime.now().isoformat()}")
    print(f"[Daily Scan] Drives: {drives}")

    # Parse drives
    drive_list = [d.strip() for d in drives.split(',')]
    folder_type = FolderType.ALL
    if set(drive_list) == {'Y:', 'Z:'}:
        folder_type = FolderType.BOTH
    elif drive_list == ['X:']:
        folder_type = FolderType.POKERGO

    # Configure scan
    scan_mode = ScanMode.FULL if mode == 'full' else ScanMode.INCREMENTAL
    config = ScanConfig(
        mode=scan_mode,
        folder_type=folder_type,
    )

    combined_stats = {
        'mode': mode,
        'drives': drives,
        'new_files': 0,
        'updated_files': 0,
        'missing_files': 0,
        'path_changes': 0,
        'total_scanned': 0,
        'total_size_bytes': 0,
        'errors': [],
    }

    with get_db_context() as db:
        # Create scan history record
        scan_history = create_scan_history(db, mode, drives)
        print(f"[Daily Scan] Created ScanHistory #{scan_history.id}")

        try:
            # Step 1: Run standard scan
            print("[Daily Scan] Step 1: Running file scan...")
            scan_stats = run_scan(config)
            combined_stats['new_files'] = scan_stats.get('new_files', 0)
            combined_stats['total_scanned'] = (
                scan_stats.get('origin_files', 0) +
                scan_stats.get('archive_files', 0) +
                scan_stats.get('pokergo_files', 0)
            )
            combined_stats['total_size_bytes'] = scan_stats.get('total_size_bytes', 0)
            combined_stats['errors'].extend(scan_stats.get('errors', []))

            # Step 2: Detect missing files (for incremental mode)
            if mode == 'daily':
                print("[Daily Scan] Step 2: Detecting missing files...")
                # Get all current paths from scan
                current_paths = set()
                if config.folder_type in (FolderType.ORIGIN, FolderType.BOTH, FolderType.ALL):
                    origin_files = scan_directory(Path(config.origin_path), "origin")
                    current_paths.update(f.get('full_path') for f in origin_files)
                if config.folder_type in (FolderType.ARCHIVE, FolderType.BOTH, FolderType.ALL):
                    archive_files = scan_directory(Path(config.archive_path), "archive")
                    current_paths.update(f.get('full_path') for f in archive_files)
                if config.folder_type in (FolderType.POKERGO, FolderType.ALL):
                    pokergo_files = scan_directory(Path(config.pokergo_path), "pokergo")
                    current_paths.update(f.get('full_path') for f in pokergo_files)

                missing_stats = detect_missing_files(db, current_paths)
                combined_stats['missing_files'] = missing_stats.get('missing_files', 0)

            # Update scan history with success
            update_scan_history(db, scan_history, combined_stats, status='completed')
            print("[Daily Scan] Completed successfully")

        except Exception as e:
            error_msg = str(e)
            combined_stats['errors'].append(error_msg)
            update_scan_history(db, scan_history, combined_stats, status='failed', error=error_msg)
            print(f"[Daily Scan] Failed: {error_msg}")
            raise

    # Step 3: Sync to Google Sheets (optional)
    if sync_sheets:
        print("[Daily Scan] Step 3: Syncing to Google Sheets...")
        try:
            from scripts.sync_sheets import sync_changes_to_sheets
            sync_result = sync_changes_to_sheets()
            print(f"[Daily Scan] Sheets sync: {sync_result.get('status', 'unknown')}")
        except ImportError:
            print("[Daily Scan] Warning: sync_sheets module not found, skipping")
        except Exception as e:
            print(f"[Daily Scan] Warning: Sheets sync failed: {e}")

    # Print summary
    print("\n" + "=" * 50)
    print("[Daily Scan] Summary")
    print("=" * 50)
    print(f"  Mode: {combined_stats['mode']}")
    print(f"  Drives: {combined_stats['drives']}")
    print(f"  New files: {combined_stats['new_files']}")
    print(f"  Missing files: {combined_stats['missing_files']}")
    print(f"  Path changes: {combined_stats['path_changes']}")
    print(f"  Total scanned: {combined_stats['total_scanned']}")
    print(f"  Total size: {combined_stats['total_size_bytes']:,} bytes")
    if combined_stats['errors']:
        print(f"  Errors: {len(combined_stats['errors'])}")
        for err in combined_stats['errors'][:5]:
            print(f"    - {err}")
    print("=" * 50)

    return combined_stats


def main():
    parser = argparse.ArgumentParser(description='NAMS Daily Scan Script')
    parser.add_argument(
        '--mode',
        choices=['daily', 'full'],
        default='daily',
        help='Scan mode: daily (incremental) or full'
    )
    parser.add_argument(
        '--drives',
        default='Y:,Z:,X:',
        help='Comma-separated list of drives to scan (default: Y:,Z:,X:)'
    )
    parser.add_argument(
        '--sync-sheets',
        action='store_true',
        help='Sync changes to Google Sheets after scan'
    )

    args = parser.parse_args()

    try:
        stats = run_daily_scan(
            mode=args.mode,
            drives=args.drives,
            sync_sheets=args.sync_sheets,
        )
        sys.exit(0 if not stats.get('errors') else 1)
    except Exception as e:
        print(f"[Daily Scan] Fatal error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()

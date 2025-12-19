"""Change tracking service for NAMS Validator.

파일 경로 변경 및 상태 변경을 추적하는 서비스.
"""
import json
from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import AuditLog, NasFile


def add_path_change(
    db: Session,
    nas_file: NasFile,
    old_path: str,
    new_path: str,
    changed_by: str = 'system'
) -> dict:
    """Record a path change for a NAS file.

    Args:
        db: Database session
        nas_file: NasFile object to update
        old_path: Previous file path
        new_path: New file path
        changed_by: Who/what made the change

    Returns:
        Change record dict
    """
    # Parse existing history
    history = []
    if nas_file.path_history:
        try:
            history = json.loads(nas_file.path_history)
        except json.JSONDecodeError:
            history = []

    # Create change record
    change_record = {
        'old_path': old_path,
        'new_path': new_path,
        'changed_at': datetime.utcnow().isoformat(),
        'changed_by': changed_by,
    }
    history.append(change_record)

    # Update file
    nas_file.path_history = json.dumps(history)
    nas_file.full_path = new_path
    nas_file.updated_at = datetime.utcnow()

    # Create audit log
    audit_log = AuditLog(
        entity_type='nas_file',
        entity_id=nas_file.id,
        action='path_change',
        old_values=json.dumps({'full_path': old_path}),
        new_values=json.dumps({'full_path': new_path}),
        changed_by=changed_by,
    )
    db.add(audit_log)

    return change_record


def get_path_history(nas_file: NasFile) -> list[dict]:
    """Get path change history for a file.

    Args:
        nas_file: NasFile object

    Returns:
        List of change records
    """
    if not nas_file.path_history:
        return []

    try:
        return json.loads(nas_file.path_history)
    except json.JSONDecodeError:
        return []


def mark_file_missing(
    db: Session,
    nas_file: NasFile,
    reason: str = 'Not found in scan'
) -> None:
    """Mark a file as missing (not found in latest scan).

    Args:
        db: Database session
        nas_file: NasFile object
        reason: Reason for marking as missing
    """
    if nas_file.last_seen_at is None:
        nas_file.last_seen_at = datetime.utcnow()

        # Create audit log
        audit_log = AuditLog(
            entity_type='nas_file',
            entity_id=nas_file.id,
            action='mark_missing',
            old_values=json.dumps({'last_seen_at': None}),
            new_values=json.dumps({
                'last_seen_at': nas_file.last_seen_at.isoformat(),
                'reason': reason,
            }),
            changed_by='system',
        )
        db.add(audit_log)


def mark_file_found(db: Session, nas_file: NasFile) -> None:
    """Mark a previously missing file as found again.

    Args:
        db: Database session
        nas_file: NasFile object
    """
    if nas_file.last_seen_at is not None:
        old_last_seen = nas_file.last_seen_at.isoformat() if nas_file.last_seen_at else None
        nas_file.last_seen_at = None

        # Create audit log
        audit_log = AuditLog(
            entity_type='nas_file',
            entity_id=nas_file.id,
            action='mark_found',
            old_values=json.dumps({'last_seen_at': old_last_seen}),
            new_values=json.dumps({'last_seen_at': None, 'status': 'found'}),
            changed_by='system',
        )
        db.add(audit_log)


def get_missing_files(db: Session, limit: int = 100) -> list[NasFile]:
    """Get list of files marked as missing.

    Args:
        db: Database session
        limit: Maximum number of files to return

    Returns:
        List of NasFile objects marked as missing
    """
    return db.query(NasFile).filter(
        NasFile.last_seen_at.isnot(None)
    ).order_by(
        NasFile.last_seen_at.desc()
    ).limit(limit).all()


def get_recent_path_changes(db: Session, days: int = 7, limit: int = 100) -> list[dict]:
    """Get recent path changes from audit log.

    Args:
        db: Database session
        days: Number of days to look back
        limit: Maximum number of changes to return

    Returns:
        List of change records with file info
    """
    cutoff = datetime.utcnow().replace(hour=0, minute=0, second=0)

    changes = db.query(AuditLog).filter(
        AuditLog.entity_type == 'nas_file',
        AuditLog.action == 'path_change',
        AuditLog.changed_at >= cutoff,
    ).order_by(
        AuditLog.changed_at.desc()
    ).limit(limit).all()

    results = []
    for change in changes:
        try:
            old_values = json.loads(change.old_values) if change.old_values else {}
            new_values = json.loads(change.new_values) if change.new_values else {}
            results.append({
                'file_id': change.entity_id,
                'old_path': old_values.get('full_path'),
                'new_path': new_values.get('full_path'),
                'changed_at': change.changed_at.isoformat() if change.changed_at else None,
                'changed_by': change.changed_by,
            })
        except json.JSONDecodeError:
            continue

    return results


def get_change_stats(db: Session, scan_history_id: int | None = None) -> dict:
    """Get change statistics.

    Args:
        db: Database session
        scan_history_id: Optional scan history ID to filter by

    Returns:
        Dict with change statistics
    """
    # Total missing files
    missing_count = db.query(func.count(NasFile.id)).filter(
        NasFile.last_seen_at.isnot(None)
    ).scalar() or 0

    # Files with path history
    path_changed_count = db.query(func.count(NasFile.id)).filter(
        NasFile.path_history.isnot(None),
        NasFile.path_history != '[]',
    ).scalar() or 0

    # Recent changes (last 24h)
    yesterday = datetime.utcnow().replace(hour=0, minute=0, second=0)
    recent_changes = db.query(func.count(AuditLog.id)).filter(
        AuditLog.entity_type == 'nas_file',
        AuditLog.action.in_(['path_change', 'mark_missing', 'mark_found']),
        AuditLog.changed_at >= yesterday,
    ).scalar() or 0

    return {
        'missing_files': missing_count,
        'files_with_path_changes': path_changed_count,
        'recent_changes_24h': recent_changes,
    }


def sync_file_metadata(
    db: Session,
    nas_file: NasFile,
    scanned_data: dict,
    changed_by: str = 'system'
) -> dict:
    """Sync file metadata from scan results.

    Args:
        db: Database session
        nas_file: NasFile object to update
        scanned_data: Dict with scanned file data
        changed_by: Who/what made the change

    Returns:
        Dict with changes made
    """
    changes = {}

    # Check for path change
    new_path = scanned_data.get('full_path')
    if new_path and nas_file.full_path != new_path:
        add_path_change(db, nas_file, nas_file.full_path, new_path, changed_by)
        changes['path'] = {'old': nas_file.full_path, 'new': new_path}

    # Check for size change
    new_size = scanned_data.get('size_bytes')
    if new_size and nas_file.size_bytes != new_size:
        changes['size'] = {'old': nas_file.size_bytes, 'new': new_size}
        nas_file.size_bytes = new_size

    # Mark as found if was missing
    if nas_file.last_seen_at is not None:
        mark_file_found(db, nas_file)
        changes['status'] = {'old': 'missing', 'new': 'found'}

    if changes:
        nas_file.updated_at = datetime.utcnow()

    return changes

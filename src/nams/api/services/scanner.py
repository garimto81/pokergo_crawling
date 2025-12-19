"""NAS Scanner service for NAMS."""
import os
import re
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from ..database import ExclusionRule, NasFile, get_db_context


class ScanMode(str, Enum):
    """Scan mode."""
    INCREMENTAL = "incremental"  # 추가분만
    FULL = "full"  # 전체 재스캔


class FolderType(str, Enum):
    """NAS folder type."""
    ORIGIN = "origin"
    ARCHIVE = "archive"
    POKERGO = "pokergo"  # X: PokerGO source
    BOTH = "both"  # Origin + Archive
    ALL = "all"  # Origin + Archive + PokerGO


@dataclass
class ScanConfig:
    """Scan configuration."""
    origin_path: str = "Y:/WSOP backup"
    archive_path: str = "Z:/"
    pokergo_path: str = "X:/GGP Footage/POKERGO"  # PokerGO source
    mode: ScanMode = ScanMode.INCREMENTAL
    folder_type: FolderType = FolderType.BOTH


# Video extensions
VIDEO_EXTENSIONS = {'.mp4', '.mkv', '.mov', '.avi', '.wmv', '.m4v', '.mxf'}


@dataclass
class ExclusionCheckResult:
    """Result of exclusion check."""
    excluded: bool
    reason: Optional[str] = None
    rule_id: Optional[int] = None


def get_active_exclusion_rules(db: Session) -> list[ExclusionRule]:
    """Get all active exclusion rules from database."""
    return db.query(ExclusionRule).filter(ExclusionRule.is_active == True).all()


def check_exclusion_rules(
    rules: list[ExclusionRule],
    filename: str,
    size_bytes: int,
    full_path: str,
    duration_sec: Optional[int] = None
) -> ExclusionCheckResult:
    """Check if a file should be excluded based on active rules.

    Args:
        rules: List of active exclusion rules
        filename: File name
        size_bytes: File size in bytes
        full_path: Full path for keyword matching
        duration_sec: Optional duration in seconds (if available)

    Returns:
        ExclusionCheckResult with excluded status and reason
    """
    filename_lower = filename.lower()
    full_path_lower = full_path.lower()

    for rule in rules:
        # Size rules
        if rule.rule_type == "size":
            threshold = int(rule.value)
            if rule.operator == "lt" and size_bytes < threshold:
                return ExclusionCheckResult(
                    excluded=True,
                    reason=f"Size {size_bytes:,} bytes < {threshold:,} bytes",
                    rule_id=rule.id
                )
            elif rule.operator == "gt" and size_bytes > threshold:
                return ExclusionCheckResult(
                    excluded=True,
                    reason=f"Size {size_bytes:,} bytes > {threshold:,} bytes",
                    rule_id=rule.id
                )

        # Duration rules (only if duration is available)
        elif rule.rule_type == "duration" and duration_sec is not None:
            threshold = int(rule.value)
            if rule.operator == "lt" and duration_sec < threshold:
                return ExclusionCheckResult(
                    excluded=True,
                    reason=f"Duration {duration_sec}s < {threshold}s",
                    rule_id=rule.id
                )
            elif rule.operator == "gt" and duration_sec > threshold:
                return ExclusionCheckResult(
                    excluded=True,
                    reason=f"Duration {duration_sec}s > {threshold}s",
                    rule_id=rule.id
                )

        # Keyword rules (check both filename and full path)
        elif rule.rule_type == "keyword":
            keyword_lower = rule.value.lower()
            if rule.operator == "contains":
                if keyword_lower in filename_lower or keyword_lower in full_path_lower:
                    return ExclusionCheckResult(
                        excluded=True,
                        reason=f"Contains keyword '{rule.value}'",
                        rule_id=rule.id
                    )

    return ExclusionCheckResult(excluded=False)


def parse_filename(filepath: Path) -> dict:
    """Extract metadata from filename."""
    filename = filepath.stem

    metadata = {
        "filename": filepath.name,
        "extension": filepath.suffix.lower(),
        "size_bytes": filepath.stat().st_size if filepath.exists() else 0,
        "modified_at": datetime.fromtimestamp(filepath.stat().st_mtime).isoformat() if filepath.exists() else None,
    }

    # Pattern: WSOP14_APAC_ME_01 or similar
    wsop_pattern = re.match(
        r'WSOP?(\d{2,4})[_-]?([A-Z]+)?[_-]?([A-Z]+)?[_-]?(\d+)?',
        filename, re.I
    )
    if wsop_pattern:
        year = wsop_pattern.group(1)
        if len(year) == 2:
            year = f"20{year}" if int(year) < 50 else f"19{year}"
        metadata.update({
            "year": int(year),
            "region": wsop_pattern.group(2),
            "event_type": wsop_pattern.group(3),
            "episode": int(wsop_pattern.group(4)) if wsop_pattern.group(4) else None,
        })
        return metadata

    # Generic
    metadata["year"] = None
    metadata["region"] = None
    metadata["event_type"] = None
    metadata["episode"] = None

    return metadata


def scan_directory(root_path: Path, base_path: str = "") -> list[dict]:
    """Recursively scan directory and collect file info."""
    files = []

    if not root_path.exists():
        return files

    try:
        for entry in os.scandir(root_path):
            if entry.name.startswith('.') or entry.name in ('Thumbs.db', 'desktop.ini'):
                continue

            relative_path = os.path.join(base_path, entry.name) if base_path else entry.name

            if entry.is_dir():
                files.extend(scan_directory(Path(entry.path), relative_path))
            elif entry.is_file():
                ext = os.path.splitext(entry.name)[1].lower()
                if ext in VIDEO_EXTENSIONS:
                    filepath = Path(entry.path)
                    file_info = parse_filename(filepath)
                    file_info["relative_path"] = relative_path
                    file_info["full_path"] = str(filepath)
                    file_info["directory"] = base_path
                    files.append(file_info)
    except PermissionError:
        pass

    return files


def get_existing_paths(db: Session) -> set[str]:
    """Get all existing file paths from database."""
    paths = db.query(NasFile.full_path).all()
    return {p[0] for p in paths if p[0]}


def run_scan(config: ScanConfig) -> dict:
    """Run NAS scan with given configuration.

    Args:
        config: Scan configuration

    Returns:
        Dictionary with scan statistics
    """
    stats = {
        "mode": config.mode.value,
        "folder_type": config.folder_type.value,
        "origin_files": 0,
        "archive_files": 0,
        "pokergo_files": 0,
        "new_files": 0,
        "skipped_files": 0,
        "excluded_files": 0,
        "total_size_bytes": 0,
        "errors": [],
        "exclusion_reasons": [],
    }

    all_files = []

    # Scan origin folder
    if config.folder_type in (FolderType.ORIGIN, FolderType.BOTH, FolderType.ALL):
        origin_path = Path(config.origin_path)
        if origin_path.exists():
            print(f"[Scan] Scanning origin: {origin_path}")
            origin_files = scan_directory(origin_path, "origin")
            for f in origin_files:
                f["source_folder"] = "origin"
            all_files.extend(origin_files)
            stats["origin_files"] = len(origin_files)
            print(f"  Found {len(origin_files)} files")
        else:
            stats["errors"].append(f"Origin path not found: {origin_path}")

    # Scan archive folder
    if config.folder_type in (FolderType.ARCHIVE, FolderType.BOTH, FolderType.ALL):
        archive_path = Path(config.archive_path)
        if archive_path.exists():
            print(f"[Scan] Scanning archive: {archive_path}")
            archive_files = scan_directory(archive_path, "archive")
            for f in archive_files:
                f["source_folder"] = "archive"
            all_files.extend(archive_files)
            stats["archive_files"] = len(archive_files)
            print(f"  Found {len(archive_files)} files")
        else:
            stats["errors"].append(f"Archive path not found: {archive_path}")

    # Scan PokerGO source folder
    if config.folder_type in (FolderType.POKERGO, FolderType.ALL):
        pokergo_path = Path(config.pokergo_path)
        if pokergo_path.exists():
            print(f"[Scan] Scanning PokerGO source: {pokergo_path}")
            pokergo_files = scan_directory(pokergo_path, "pokergo")
            for f in pokergo_files:
                f["source_folder"] = "pokergo"
            all_files.extend(pokergo_files)
            stats["pokergo_files"] = len(pokergo_files)
            print(f"  Found {len(pokergo_files)} files")
        else:
            stats["errors"].append(f"PokerGO path not found: {pokergo_path}")

    # Save to database
    with get_db_context() as db:
        existing_paths = set()

        if config.mode == ScanMode.INCREMENTAL:
            existing_paths = get_existing_paths(db)
            print(f"[Scan] Incremental mode: {len(existing_paths)} existing files")
        elif config.mode == ScanMode.FULL:
            # Clear existing files for full rescan
            print("[Scan] Full mode: clearing existing files...")
            db.query(NasFile).delete()
            db.commit()

        # Get active exclusion rules
        exclusion_rules = get_active_exclusion_rules(db)
        print(f"[Scan] Active exclusion rules: {len(exclusion_rules)}")

        for file_data in all_files:
            full_path = file_data.get("full_path")
            filename = file_data["filename"]
            size_bytes = file_data["size_bytes"]

            # Skip existing files in incremental mode
            if config.mode == ScanMode.INCREMENTAL and full_path in existing_paths:
                stats["skipped_files"] += 1
                continue

            # Check exclusion rules (for flagging, not skipping)
            exclusion_result = check_exclusion_rules(
                rules=exclusion_rules,
                filename=filename,
                size_bytes=size_bytes,
                full_path=full_path,
                duration_sec=None  # Duration not available from file scan
            )

            # Determine role based on source folder
            source_folder = file_data["source_folder"]
            if source_folder == "origin":
                role = "primary"
            elif source_folder == "pokergo":
                role = "pokergo_source"
            else:
                role = "backup"

            # Create new file record (ALL files are stored, excluded ones are flagged)
            nas_file = NasFile(
                filename=file_data["filename"],
                extension=file_data["extension"],
                size_bytes=file_data["size_bytes"],
                directory=file_data["directory"],
                full_path=full_path,
                year=file_data.get("year"),
                role=role,
                # Exclusion flags (checkbox display)
                is_excluded=exclusion_result.excluded,
                exclusion_reason=exclusion_result.reason if exclusion_result.excluded else None,
                exclusion_rule_id=exclusion_result.rule_id if exclusion_result.excluded else None,
            )
            db.add(nas_file)
            stats["new_files"] += 1
            stats["total_size_bytes"] += file_data["size_bytes"]

            if exclusion_result.excluded:
                stats["excluded_files"] += 1
                if len(stats["exclusion_reasons"]) < 10:
                    stats["exclusion_reasons"].append({
                        "file": filename,
                        "reason": exclusion_result.reason
                    })

        db.commit()

    print(f"[Scan] Flagged {stats['excluded_files']} files as excluded (stored with is_excluded=True)")
    return stats


def format_size(bytes_size: int) -> str:
    """Format bytes to human readable."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_size < 1024:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024
    return f"{bytes_size:.1f} PB"

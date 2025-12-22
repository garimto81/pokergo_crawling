"""Checksum utilities for incremental sync."""

import hashlib
import json
from typing import Any


def calculate_dict_checksum(
    data: dict[str, Any],
    exclude_keys: list[str] | None = None,
) -> str:
    """Calculate MD5 checksum of a dictionary.

    Args:
        data: Dictionary to calculate checksum for
        exclude_keys: Keys to exclude from checksum calculation

    Returns:
        MD5 hex digest string
    """
    exclude = set(exclude_keys or [])
    filtered = {k: v for k, v in data.items() if k not in exclude}
    content = json.dumps(filtered, sort_keys=True, default=str)
    return hashlib.md5(content.encode()).hexdigest()


def calculate_asset_checksum(
    metadata: dict[str, Any] | None,
    segments: list[dict[str, Any]] | None,
) -> str:
    """Calculate checksum for asset metadata and segments.

    Args:
        metadata: Asset metadata dictionary
        segments: List of segment dictionaries

    Returns:
        MD5 hex digest string
    """
    content = {
        "metadata": metadata or {},
        "segments": sorted(
            segments or [],
            key=lambda s: s.get("time_start_milliseconds", 0),
        ),
    }
    return calculate_dict_checksum(content)


def calculate_row_checksum(
    row: dict[str, Any],
    exclude_keys: list[str] | None = None,
) -> str:
    """Calculate checksum for a sheet row.

    Args:
        row: Row data dictionary
        exclude_keys: Keys to exclude (default: ['id'])

    Returns:
        MD5 hex digest string
    """
    default_exclude = ["id"]
    exclude = (exclude_keys or []) + default_exclude
    return calculate_dict_checksum(row, exclude_keys=exclude)


def calculate_file_fingerprint(mtime: float, size: int) -> str:
    """Calculate file fingerprint from mtime and size.

    Args:
        mtime: File modification time (timestamp)
        size: File size in bytes

    Returns:
        Fingerprint string in format "mtime:size"
    """
    return f"{mtime}:{size}"

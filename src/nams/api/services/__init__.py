"""Services for NAMS API."""
from .catalog_service import (
    generate_catalog_title,
    generate_titles_for_all,
    generate_titles_for_unmatched,
    update_catalog_title,
)
from .export import export_to_csv, export_to_google_sheets, export_to_json
from .grouping import run_grouping
from .matching import (
    MATCH_CATEGORY_MATCHED,
    MATCH_CATEGORY_NAS_ONLY_HISTORIC,
    MATCH_CATEGORY_NAS_ONLY_MODERN,
    MATCH_CATEGORY_POKERGO_ONLY,
    get_matching_summary,
    get_pokergo_only_episodes,
    run_matching,
    update_match_categories,
)
from .migration import run_migration
from .pattern_engine import run_pattern_extraction
from .scanner import FolderType, ScanConfig, ScanMode, run_scan

__all__ = [
    "run_migration",
    "run_scan", "ScanConfig", "ScanMode", "FolderType",
    "run_pattern_extraction",
    "run_grouping",
    "run_matching", "update_match_categories", "get_pokergo_only_episodes", "get_matching_summary",
    "MATCH_CATEGORY_MATCHED", "MATCH_CATEGORY_NAS_ONLY_HISTORIC",
    "MATCH_CATEGORY_NAS_ONLY_MODERN", "MATCH_CATEGORY_POKERGO_ONLY",
    "export_to_csv", "export_to_json", "export_to_google_sheets",
    "generate_catalog_title", "generate_titles_for_unmatched",
    "generate_titles_for_all", "update_catalog_title",
]

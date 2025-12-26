"""Subclip metadata validator for data quality checks.

Validates Iconik_Subclips_Metadata against Iconik_General_Metadata.
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sheets.writer import SheetsWriter


@dataclass
class ValidationResult:
    """Subclip validation results."""

    # Parent relationship issues
    orphan_subclips: list[dict] = field(default_factory=list)
    missing_parent: list[dict] = field(default_factory=list)
    self_reference: list[dict] = field(default_factory=list)

    # Timecode issues
    missing_timecode: list[dict] = field(default_factory=list)
    round_timecode: list[dict] = field(default_factory=list)
    invalid_range: list[dict] = field(default_factory=list)

    # Summary
    total_count: int = 0
    valid_count: int = 0

    @property
    def issue_count(self) -> int:
        """Total number of issues found."""
        return (
            len(self.orphan_subclips)
            + len(self.missing_parent)
            + len(self.self_reference)
            + len(self.missing_timecode)
            + len(self.round_timecode)
            + len(self.invalid_range)
        )

    def to_report(self) -> dict:
        """Generate summary report."""
        total_issues = self.issue_count
        valid_pct = (self.valid_count / self.total_count * 100) if self.total_count else 0

        return {
            "summary": {
                "total_subclips": self.total_count,
                "valid": self.valid_count,
                "valid_percentage": f"{valid_pct:.1f}%",
                "issues": total_issues,
            },
            "issues_breakdown": {
                "orphan_subclip": len(self.orphan_subclips),
                "missing_parent": len(self.missing_parent),
                "self_reference": len(self.self_reference),
                "missing_timecode": len(self.missing_timecode),
                "round_timecode": len(self.round_timecode),
                "invalid_range": len(self.invalid_range),
            },
        }

    def get_all_issues(self) -> list[dict]:
        """Get all issues as a flat list for Sheets export."""
        all_issues = []

        for item in self.orphan_subclips:
            all_issues.append({**item, "issue_type": "orphan_subclip"})

        for item in self.missing_parent:
            all_issues.append({**item, "issue_type": "missing_parent"})

        for item in self.self_reference:
            all_issues.append({**item, "issue_type": "self_reference"})

        for item in self.missing_timecode:
            all_issues.append({**item, "issue_type": "missing_timecode"})

        for item in self.round_timecode:
            all_issues.append({**item, "issue_type": "round_timecode"})

        for item in self.invalid_range:
            all_issues.append({**item, "issue_type": "invalid_range"})

        return all_issues


class SubclipValidator:
    """Validates Iconik_Subclips_Metadata quality.

    Checks:
    1. Parent relationship: original_asset_id must exist in Iconik_General_Metadata
    2. Self-reference: id != original_asset_id
    3. Missing parent: original_asset_id should not be empty
    4. Timecode quality: not round numbers, valid range
    """

    GENERAL_SHEET = "Iconik_General_Metadata"
    SUBCLIPS_SHEET = "Iconik_Subclips_Metadata"
    ROUND_NUMBER_THRESHOLD_MS = 10000  # 10 seconds

    def __init__(self, sheets: "SheetsWriter | None" = None) -> None:
        from sheets.writer import SheetsWriter

        self.sheets = sheets or SheetsWriter()
        self.result = ValidationResult()

    def validate(self) -> ValidationResult:
        """Run all validations.

        Returns:
            ValidationResult with all issues found.
        """
        # Load data from sheets
        general_ids = self._load_general_ids()
        subclips = self._load_subclips()

        self.result.total_count = len(subclips)

        # Validate each subclip
        for subclip in subclips:
            issues = self._validate_subclip(subclip, general_ids)
            if not issues:
                self.result.valid_count += 1

        return self.result

    def validate_all_with_flags(self) -> list[dict]:
        """Validate all subclips and return with issue flags.

        Returns:
            List of all subclips with issue type columns as TRUE/empty.
        """
        general_ids = self._load_general_ids()
        subclips = self._load_subclips()

        self.result.total_count = len(subclips)
        all_with_flags = []

        for subclip in subclips:
            row_info = self._extract_row_info(subclip)

            # Initialize all issue flags as empty
            flags = {
                "orphan_subclip": "",
                "missing_parent": "",
                "self_reference": "",
                "missing_timecode": "",
                "round_timecode": "",
                "invalid_range": "",
            }

            # Check each issue type
            original_id = subclip.get("original_asset_id", "")

            # 1. Missing parent
            if not original_id:
                flags["missing_parent"] = "TRUE"
            else:
                # 2. Self-reference
                subclip_id = subclip.get("id", "")
                if subclip_id and subclip_id == original_id:
                    flags["self_reference"] = "TRUE"

                # 3. Orphan (parent not in General)
                if original_id not in general_ids:
                    flags["orphan_subclip"] = "TRUE"

            # 4. Timecode validations
            start_str = subclip.get("time_start_ms", "")
            end_str = subclip.get("time_end_ms", "")

            if not start_str or not end_str:
                flags["missing_timecode"] = "TRUE"
            else:
                try:
                    start = int(start_str)
                    end = int(end_str)

                    if start >= end:
                        flags["invalid_range"] = "TRUE"
                    elif self._is_round_number(start) or self._is_round_number(end):
                        flags["round_timecode"] = "TRUE"
                except (ValueError, TypeError):
                    flags["missing_timecode"] = "TRUE"

            # Count valid
            has_issues = any(v == "TRUE" for v in flags.values())
            if not has_issues:
                self.result.valid_count += 1

            # Combine row info with flags
            all_with_flags.append({**row_info, **flags})

        return all_with_flags

    def _load_general_ids(self) -> set[str]:
        """Load all IDs from Iconik_General_Metadata sheet."""
        _, data = self.sheets.get_sheet_data(self.GENERAL_SHEET)
        if not data:
            print(f"Warning: No data loaded from {self.GENERAL_SHEET}")
        return {row.get("id", "") for row in data if row.get("id")}

    def _load_subclips(self) -> list[dict]:
        """Load all rows from Iconik_Subclips_Metadata sheet."""
        _, data = self.sheets.get_sheet_data(self.SUBCLIPS_SHEET)
        if not data:
            print(f"Warning: No data loaded from {self.SUBCLIPS_SHEET}")
        return data

    def _validate_subclip(self, subclip: dict, general_ids: set[str]) -> list[str]:
        """Validate a single subclip.

        Args:
            subclip: Subclip row data.
            general_ids: Set of valid General asset IDs.

        Returns:
            List of issue types found for this subclip.
        """
        issues = []
        row_info = self._extract_row_info(subclip)

        # 1. Check missing parent (original_asset_id is empty)
        original_id = subclip.get("original_asset_id", "")
        if not original_id:
            self.result.missing_parent.append(row_info)
            issues.append("missing_parent")
        else:
            # 2. Check self-reference
            subclip_id = subclip.get("id", "")
            if subclip_id and subclip_id == original_id:
                self.result.self_reference.append(row_info)
                issues.append("self_reference")

            # 3. Check orphan (parent not in General)
            if original_id not in general_ids:
                self.result.orphan_subclips.append(row_info)
                issues.append("orphan_subclip")

        # 4. Timecode validations
        timecode_issue = self._check_timecode(subclip, row_info)
        if timecode_issue:
            issues.append(timecode_issue)

        return issues

    def _extract_row_info(self, subclip: dict) -> dict:
        """Extract key fields for reporting."""
        return {
            "id": subclip.get("id", ""),
            "title": subclip.get("title", ""),
            "original_asset_id": subclip.get("original_asset_id", ""),
            "parent_title": subclip.get("parent_title", ""),
            "time_start_ms": subclip.get("time_start_ms", ""),
            "time_end_ms": subclip.get("time_end_ms", ""),
        }

    def _check_timecode(self, subclip: dict, row_info: dict) -> str | None:
        """Check timecode validity.

        Args:
            subclip: Subclip row data.
            row_info: Extracted row info for reporting.

        Returns:
            Issue type if found, None otherwise.
        """
        start_str = subclip.get("time_start_ms", "")
        end_str = subclip.get("time_end_ms", "")

        # 1. Missing timecode
        if not start_str or not end_str:
            self.result.missing_timecode.append(row_info)
            return "missing_timecode"

        try:
            start = int(start_str)
            end = int(end_str)
        except (ValueError, TypeError):
            self.result.missing_timecode.append(row_info)
            return "missing_timecode"

        # 2. Invalid range (start >= end)
        if start >= end:
            self.result.invalid_range.append(row_info)
            return "invalid_range"

        # 3. Round number detection (10 second multiple)
        if self._is_round_number(start) or self._is_round_number(end):
            self.result.round_timecode.append(row_info)
            return "round_timecode"

        return None

    def _is_round_number(self, ms: int) -> bool:
        """Check if milliseconds is a 10-second exact multiple.

        Args:
            ms: Milliseconds value.

        Returns:
            True if exactly divisible by 10000ms (10 seconds).
        """
        threshold = self.ROUND_NUMBER_THRESHOLD_MS
        if ms < threshold:
            return False

        return ms % threshold == 0

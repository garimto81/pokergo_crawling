"""Sheet migration orchestrator."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from sheets.reader import SheetsReader
from sheets.writer import SheetsWriter
from mapping.column_mapper import ColumnMapper, TARGET_COLUMNS
from config.settings import get_settings


@dataclass
class MigrationResult:
    """Result of a migration run."""

    success: bool = False
    mode: str = ""
    total_tabs: int = 0
    total_source_rows: int = 0
    total_mapped_rows: int = 0
    total_written_rows: int = 0
    existing_rows: int = 0
    dry_run: bool = True
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: datetime | None = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    tabs_processed: list[dict[str, Any]] = field(default_factory=list)

    def to_report(self) -> str:
        """Generate a text report of the migration result."""
        lines = [
            "=" * 60,
            "Migration Report",
            "=" * 60,
            "",
            f"Status: {'SUCCESS' if self.success else 'FAILED'}",
            f"Mode: {self.mode}",
            f"Dry Run: {self.dry_run}",
            "",
            "Source Stats:",
            f"  Tabs processed: {self.total_tabs}",
            f"  Total source rows: {self.total_source_rows}",
            f"  Total mapped rows: {self.total_mapped_rows}",
            "",
            "Target Stats:",
            f"  Existing rows: {self.existing_rows}",
            f"  Written rows: {self.total_written_rows}",
            "",
        ]

        if self.tabs_processed:
            lines.append("Tabs Breakdown:")
            for tab in self.tabs_processed:
                lines.append(f"  - {tab['name']}: {tab['rows']} rows")

        if self.warnings:
            lines.append("")
            lines.append("Warnings:")
            for warning in self.warnings:
                lines.append(f"  [WARN] {warning}")

        if self.errors:
            lines.append("")
            lines.append("Errors:")
            for error in self.errors:
                lines.append(f"  [ERROR] {error}")

        duration = (self.completed_at or datetime.now()) - self.started_at
        lines.extend([
            "",
            f"Duration: {duration.total_seconds():.2f}s",
            f"Started: {self.started_at.isoformat()}",
            f"Completed: {self.completed_at.isoformat() if self.completed_at else 'N/A'}",
            "=" * 60,
        ])

        return "\n".join(lines)


class SheetMigrator:
    """Orchestrates sheet-to-sheet migration."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.reader = SheetsReader()
        self.writer = SheetsWriter()
        self.mapper = ColumnMapper()

    def run(
        self,
        dry_run: bool = True,
        mode: str | None = None,
    ) -> MigrationResult:
        """Run the migration.

        Args:
            dry_run: If True, preview changes without writing
            mode: 'append' or 'overwrite' (defaults to settings.mode)

        Returns:
            MigrationResult with stats and status
        """
        if mode is None:
            mode = self.settings.mode

        result = MigrationResult(
            mode=mode,
            dry_run=dry_run,
        )

        try:
            # Step 1: Check connections
            print("Checking API connections...")
            if not self.reader.health_check():
                result.errors.append("Failed to connect to source spreadsheet")
                return result

            if not self.writer.health_check():
                result.errors.append("Failed to connect to target spreadsheet")
                return result

            print("  [OK] Source and target connections verified")

            # Step 2: Read source data
            print("\nReading source data...")
            source_data = self.reader.read_source()

            if not source_data:
                result.warnings.append("No data found in source spreadsheet")
                result.success = True
                result.completed_at = datetime.now()
                return result

            result.total_tabs = len(source_data)
            for tab_name, rows in source_data.items():
                tab_info = {"name": tab_name, "rows": len(rows)}
                result.tabs_processed.append(tab_info)
                result.total_source_rows += len(rows)
                print(f"  - {tab_name}: {len(rows)} rows")

            # Step 3: Map data
            print("\nMapping columns...")
            mapped_data = self.mapper.map_all(source_data)
            result.total_mapped_rows = len(mapped_data)
            print(f"  Total mapped rows: {result.total_mapped_rows}")

            # Step 4: Get existing row count
            result.existing_rows = self.writer.get_existing_row_count(
                self.settings.target_sheet_name
            )
            print(f"\nTarget sheet existing rows: {result.existing_rows}")

            # Step 5: Preview or write
            if dry_run:
                print("\n[DRY RUN] Preview mode - no changes will be written")
                print(f"\nWould write {result.total_mapped_rows} rows to {self.settings.target_sheet_name}")
                print(f"Mode: {mode}")

                if mode == "overwrite":
                    print(f"  - Would clear {result.existing_rows} existing rows")
                    print(f"  - Would write {result.total_mapped_rows + 1} rows (header + data)")
                else:
                    print(f"  - Would append {result.total_mapped_rows} rows")
                    print(f"  - Total rows after: {result.existing_rows + result.total_mapped_rows}")

                # Show sample data
                if mapped_data:
                    print("\nSample output (first 3 rows):")
                    for i, row in enumerate(mapped_data[:3], 1):
                        print(f"\n  Row {i}:")
                        for col in ["id", "title", "time_start_S", "time_end_S", "PlayersTags", "Tournament"]:
                            if row.get(col):
                                print(f"    {col}: {row[col][:50]}..." if len(str(row[col])) > 50 else f"    {col}: {row[col]}")

                result.success = True
            else:
                print(f"\nWriting to {self.settings.target_sheet_name}...")
                written = self.writer.write_full_metadata(mapped_data, mode=mode)
                result.total_written_rows = written
                print(f"  Written {written} rows")
                result.success = True

            result.completed_at = datetime.now()

        except Exception as e:
            result.errors.append(str(e))
            result.completed_at = datetime.now()

        return result

    def get_mapping_preview(self) -> dict[str, Any]:
        """Get a preview of how columns will be mapped.

        Returns:
            Dict with mapping information
        """
        # Read first tab to get sample headers
        tab_names = self.reader.get_tab_names(self.settings.source_spreadsheet_id)
        if not tab_names:
            return {"error": "No tabs found"}

        sample_data = self.reader.read_sheet(
            self.settings.source_spreadsheet_id,
            tab_names[0],
            self.settings.header_row,
        )

        if not sample_data:
            return {"error": "No data found"}

        source_headers = list(sample_data[0].keys())
        return self.mapper.get_mapping_summary(source_headers)

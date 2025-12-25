"""XMP Sidecar Generator for Backup Assets.

Generates XMP sidecar files for Backup files in NAS.
ISG reads these XMP files and applies metadata to Iconik assets.
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.progress import Progress
from rich.table import Table

from .backup_loader import get_backup_loader


# XMP Template with Iconik namespace
XMP_TEMPLATE = '''<?xml version="1.0" encoding="UTF-8"?>
<x:xmpmeta xmlns:x="adobe:ns:meta/" x:xmptk="XMP Core 5.6.0">
  <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
    <rdf:Description rdf:about=""
      xmlns:dc="http://purl.org/dc/elements/1.1/"
      xmlns:iconik="http://iconik.io/ns/1.0/">
      <iconik:BackupStatus>{backup_status}</iconik:BackupStatus>
      <dc:description>Backup file - auto-tagged by NAMS</dc:description>
    </rdf:Description>
  </rdf:RDF>
</x:xmpmeta>
'''


@dataclass
class GenerationResult:
    """Result of XMP generation operation."""

    # Counts from Master_Catalog
    total_backup_rows: int = 0
    unique_backup_files: int = 0

    # File system results
    files_found: int = 0
    files_not_found: int = 0

    # Generation results
    generated: list[tuple[str, str]] = field(default_factory=list)  # (source_path, xmp_path)
    skipped_exists: list[str] = field(default_factory=list)
    failed: list[tuple[str, str]] = field(default_factory=list)  # (path, error)

    # Timing
    start_time: datetime | None = None
    end_time: datetime | None = None

    @property
    def generated_count(self) -> int:
        return len(self.generated)

    @property
    def failed_count(self) -> int:
        return len(self.failed)

    @property
    def duration_seconds(self) -> float:
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0


class XmpGenerator:
    """Generate XMP sidecar files for Backup assets.

    Creates .xmp files next to Backup files in NAS.
    ISG reads these files and applies BackupStatus metadata to Iconik.
    """

    BACKUP_STATUS_FIELD = "BackupStatus"
    BACKUP_HIDDEN_VALUE = "backup_hidden"

    def __init__(self) -> None:
        self.loader = get_backup_loader()
        self.console = Console()

    def generate_xmp_content(self) -> str:
        """Generate XMP content with backup_hidden status."""
        return XMP_TEMPLATE.format(backup_status=self.BACKUP_HIDDEN_VALUE)

    def get_xmp_path(self, source_path: Path) -> Path:
        """Get XMP sidecar path for a source file.

        Example: video.mp4 -> video.mp4.xmp
        """
        return source_path.with_suffix(source_path.suffix + ".xmp")

    def run(
        self,
        dry_run: bool = True,
        skip_existing: bool = True,
        folder_filter: str | None = None,
    ) -> GenerationResult:
        """Generate XMP files for all Backup files.

        Args:
            dry_run: If True, only report what would be generated (default)
            skip_existing: If True, skip files that already have XMP (default)
            folder_filter: Only process files in this folder (optional)

        Returns:
            GenerationResult with statistics
        """
        result = GenerationResult()
        result.start_time = datetime.now()

        # 1. Load backup files from Master_Catalog
        self.console.print("\n[bold]Step 1: Loading backup files from Master_Catalog[/bold]")
        backup_data = self.loader.load_backup_data()
        stats = self.loader.get_stats()

        result.total_backup_rows = stats["total_backup_rows"]
        result.unique_backup_files = len(backup_data)

        self.console.print(f"  Backup rows: {result.total_backup_rows}")
        self.console.print(f"  Unique files: {result.unique_backup_files}")

        if not backup_data:
            self.console.print("[yellow]No backup files found.[/yellow]")
            result.end_time = datetime.now()
            return result

        # 2. Check file existence and filter
        self.console.print("\n[bold]Step 2: Checking file existence[/bold]")

        to_generate: list[tuple[Path, Path]] = []  # (source_path, xmp_path)

        with Progress() as progress:
            task = progress.add_task("Checking files...", total=len(backup_data))

            for item in backup_data:
                full_path = item.get("full_path", "")
                if not full_path:
                    progress.update(task, advance=1)
                    continue

                source_path = Path(full_path)

                # Apply folder filter
                if folder_filter and folder_filter not in str(source_path):
                    progress.update(task, advance=1)
                    continue

                # Check if source file exists
                if not source_path.exists():
                    result.files_not_found += 1
                    progress.update(task, advance=1)
                    continue

                result.files_found += 1

                # Check if XMP already exists
                xmp_path = self.get_xmp_path(source_path)
                if skip_existing and xmp_path.exists():
                    result.skipped_exists.append(str(source_path))
                    progress.update(task, advance=1)
                    continue

                to_generate.append((source_path, xmp_path))
                progress.update(task, advance=1)

        self.console.print(f"  Files found: {result.files_found}")
        self.console.print(f"  Files not found: {result.files_not_found}")
        self.console.print(f"  Already have XMP: {len(result.skipped_exists)}")
        self.console.print(f"  [green]To generate: {len(to_generate)}[/green]")

        if not to_generate:
            self.console.print("[yellow]No XMP files to generate.[/yellow]")
            result.end_time = datetime.now()
            return result

        # 3. Show preview
        self.console.print("\n[bold]Step 3: Generation preview[/bold]")
        self._show_preview(to_generate[:10])

        if len(to_generate) > 10:
            self.console.print(f"  ... and {len(to_generate) - 10} more")

        # 4. Dry run or execute
        if dry_run:
            self.console.print("\n[yellow]DRY RUN mode - no XMP files created[/yellow]")
            self.console.print(f"Would generate {len(to_generate)} XMP files")
            self.console.print("\nTo execute, run with --execute flag")
            result.end_time = datetime.now()
            return result

        # 5. Generate XMP files
        self.console.print("\n[bold]Step 4: Generating XMP files[/bold]")
        result = self._execute_generation(to_generate, result)

        result.end_time = datetime.now()
        return result

    def _show_preview(self, items: list[tuple[Path, Path]]) -> None:
        """Show preview of XMP files to be generated."""
        self.console.print("\nXMP files to be generated:")
        self.console.print("-" * 80)

        for i, (source_path, xmp_path) in enumerate(items, 1):
            source_name = source_path.name[:40]
            self.console.print(f"  {i:3}. {source_name} -> .xmp")

    def _execute_generation(
        self,
        to_generate: list[tuple[Path, Path]],
        result: GenerationResult,
    ) -> GenerationResult:
        """Execute XMP file generation."""
        xmp_content = self.generate_xmp_content()

        with Progress() as progress:
            task = progress.add_task("Generating XMP files...", total=len(to_generate))

            for source_path, xmp_path in to_generate:
                try:
                    # Write XMP file
                    xmp_path.write_text(xmp_content, encoding="utf-8")
                    result.generated.append((str(source_path), str(xmp_path)))
                    progress.update(task, advance=1)

                except PermissionError as e:
                    result.failed.append((str(source_path), f"Permission denied: {e}"))
                    progress.update(task, advance=1)

                except OSError as e:
                    result.failed.append((str(source_path), str(e)))
                    progress.update(task, advance=1)

        self.console.print(f"\n[green]Generated: {result.generated_count}[/green]")
        if result.failed:
            self.console.print(f"[red]Failed: {result.failed_count}[/red]")

        return result

    def print_summary(self, result: GenerationResult) -> None:
        """Print summary of generation operation."""
        self.console.print("\n" + "=" * 60)
        self.console.print("[bold]XMP Generation Summary[/bold]")
        self.console.print("=" * 60)

        table = Table(show_header=False, box=None)
        table.add_column("Label", width=30)
        table.add_column("Value", width=20)

        table.add_row("Master_Catalog Backup Rows", str(result.total_backup_rows))
        table.add_row("Unique Backup Files", str(result.unique_backup_files))
        table.add_row("", "")
        table.add_row("Files Found in NAS", str(result.files_found))
        table.add_row("Files Not Found", f"[yellow]{result.files_not_found}[/yellow]")
        table.add_row("Already Have XMP", str(len(result.skipped_exists)))
        table.add_row("", "")
        table.add_row("XMP Generated", f"[green]{result.generated_count}[/green]")
        table.add_row("Failed", f"[red]{result.failed_count}[/red]")
        table.add_row("", "")
        table.add_row("Duration", f"{result.duration_seconds:.1f} seconds")

        self.console.print(table)
        self.console.print("=" * 60)

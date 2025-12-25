"""Generate XMP Sidecar Files for Backup Assets.

Creates .xmp files next to Backup files in NAS.
ISG reads these files and applies BackupStatus=backup_hidden metadata.

Usage:
    # Dry run (default)
    python -m scripts.generate_backup_xmp

    # Execute
    python -m scripts.generate_backup_xmp --execute

    # Filter by folder
    python -m scripts.generate_backup_xmp --execute --folder "Y:\\WSOP"

    # Include files that already have XMP
    python -m scripts.generate_backup_xmp --execute --overwrite
"""

import argparse
import csv
import sys
from datetime import datetime
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sync.xmp_generator import XmpGenerator, GenerationResult


def save_report(result: GenerationResult, output_path: str) -> None:
    """Save generation result to CSV file."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Source Path", "XMP Path", "Status", "Error"])

        for source_path, xmp_path in result.generated:
            writer.writerow([source_path, xmp_path, "GENERATED", ""])

        for source_path in result.skipped_exists:
            writer.writerow([source_path, "", "SKIPPED_EXISTS", ""])

        for source_path, error in result.failed:
            writer.writerow([source_path, "", "FAILED", error])

    print(f"\nReport saved to: {path}")


def save_markdown_report(result: GenerationResult, output_path: str) -> None:
    """Save generation result to Markdown file."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        f.write("# XMP Sidecar Generation Report\n\n")
        f.write(f"**Executed**: {result.start_time.strftime('%Y-%m-%d %H:%M:%S') if result.start_time else 'N/A'}\n")
        f.write(f"**Duration**: {result.duration_seconds:.1f} seconds\n\n")

        f.write("## Summary\n\n")
        f.write("| Item | Count |\n")
        f.write("|------|-------|\n")
        f.write(f"| Master_Catalog Backup Rows | {result.total_backup_rows} |\n")
        f.write(f"| Unique Backup Files | {result.unique_backup_files} |\n")
        f.write(f"| Files Found in NAS | {result.files_found} |\n")
        f.write(f"| Files Not Found | {result.files_not_found} |\n")
        f.write(f"| Already Have XMP | {len(result.skipped_exists)} |\n")
        f.write(f"| **XMP Generated** | **{result.generated_count}** |\n")
        f.write(f"| Failed | {result.failed_count} |\n\n")

        if result.generated:
            f.write("## Generated XMP Files\n\n")
            f.write("| # | Source File | XMP File |\n")
            f.write("|---|-------------|----------|\n")
            for i, (source_path, xmp_path) in enumerate(result.generated[:50], 1):
                source_name = Path(source_path).name
                f.write(f"| {i} | {source_name} | {Path(xmp_path).name} |\n")

            if len(result.generated) > 50:
                f.write(f"\n*... and {len(result.generated) - 50} more*\n")

        if result.failed:
            f.write("\n## Failed Files\n\n")
            f.write("| Source Path | Error |\n")
            f.write("|-------------|-------|\n")
            for source_path, error in result.failed:
                f.write(f"| {Path(source_path).name} | {error} |\n")

    print(f"\nMarkdown report saved to: {path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate XMP Sidecar Files for Backup Assets"
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Execute XMP generation (default: dry run)",
    )
    parser.add_argument(
        "--folder",
        type=str,
        help="Only process files in this folder path",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing XMP files (default: skip)",
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        help="Output CSV file path for results",
    )
    parser.add_argument(
        "--markdown", "-m",
        type=str,
        help="Output Markdown file path for report",
    )
    args = parser.parse_args()

    generator = XmpGenerator()

    result = generator.run(
        dry_run=not args.execute,
        skip_existing=not args.overwrite,
        folder_filter=args.folder,
    )

    generator.print_summary(result)

    # Save reports if requested
    if args.output and result.generated_count > 0:
        save_report(result, args.output)

    if args.markdown and result.generated_count > 0:
        save_markdown_report(result, args.markdown)

    # Generate default report on execute
    if args.execute and result.generated_count > 0:
        timestamp = datetime.now().strftime("%Y%m%d")
        default_md = f"docs/reports/xmp-generated-{timestamp}.md"
        save_markdown_report(result, default_md)


if __name__ == "__main__":
    main()

"""Cleanup Backup Assets from Iconik.

Deletes Backup assets from Iconik based on Master_Catalog Role column.
Only deletes General Assets (type=ASSET), preserves Subclips.

Usage:
    python -m scripts.cleanup_backups              # Dry run (default)
    python -m scripts.cleanup_backups --execute    # Execute deletion
    python -m scripts.cleanup_backups --output report.csv  # Save report
"""

import argparse
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from rich.console import Console

from sync.backup_cleanup import BackupCleanupService
from sync.cleanup_report import CleanupReportGenerator, setup_logging


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Iconik Backup 파일 정리 - Master_Catalog 기반"
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="실제 삭제 실행 (기본: dry run)",
    )
    parser.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="확인 프롬프트 건너뛰기 (위험!)",
    )
    parser.add_argument(
        "--skip-with-subclips",
        action="store_true",
        help="Subclip이 연결된 Asset 건너뛰기 (안전 모드) ★",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        help="결과 CSV 파일 경로 (예: cleanup_report.csv)",
    )
    parser.add_argument(
        "--summary",
        "-s",
        type=str,
        help="요약 CSV 파일 경로 (예: cleanup_summary.csv)",
    )
    args = parser.parse_args()

    console = Console()

    # Setup logging
    log_file = setup_logging()
    console.print(f"[dim]Log file: {log_file}[/dim]")

    # Banner
    console.print("\n" + "=" * 60)
    console.print("[bold]Iconik Backup Cleanup[/bold]")
    console.print("Master_Catalog에서 Role='Backup' 파일을 Iconik에서 삭제")
    console.print("=" * 60)

    if args.execute:
        console.print("\n[bold red]EXECUTE MODE - 실제 삭제 실행[/bold red]")
    else:
        console.print("\n[bold yellow]DRY RUN MODE - 삭제 미리보기[/bold yellow]")

    if args.skip_with_subclips:
        console.print("[bold cyan]SAFE MODE - Subclip 연결된 Asset 건너뛰기[/bold cyan]")

    # Run cleanup
    service = BackupCleanupService()
    result = service.run(
        dry_run=not args.execute,
        skip_confirmation=args.yes,
        skip_with_subclips=args.skip_with_subclips,
    )

    # Print summary
    service.print_summary(result)

    # Generate reports
    reporter = CleanupReportGenerator(result)
    reporter.log_result()

    if args.output:
        reporter.to_csv(args.output)

    if args.summary:
        reporter.to_summary_csv(args.summary)

    # Exit code
    if result.failed_count > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()

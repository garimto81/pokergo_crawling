"""Check Iconik Jobs - ISG 인제스트 작업 조회.

Usage:
    python -m scripts.check_jobs                    # 최근 7일 전체
    python -m scripts.check_jobs --status failed    # 실패한 작업만
    python -m scripts.check_jobs --days 3           # 최근 3일
    python -m scripts.check_jobs --type transfer    # Transfer 작업만
    python -m scripts.check_jobs --output csv       # CSV 출력
    python -m scripts.check_jobs --output json      # JSON 출력
"""

import argparse
import csv
import json
import sys
from datetime import datetime
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from rich.console import Console
from rich.table import Table

from iconik import IconikClient
from iconik.models import IconikJob, IconikJobSummary


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Iconik Jobs 조회 - ISG 인제스트 작업 모니터링"
    )
    parser.add_argument(
        "--status",
        choices=["all", "started", "finished", "failed", "aborted"],
        default="all",
        help="Filter by job status (default: all)",
    )
    parser.add_argument(
        "--type",
        choices=["all", "transfer", "transcode", "delete", "analyze"],
        default="all",
        help="Filter by job type (default: all)",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="Days to look back (default: 7)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of jobs to retrieve",
    )
    parser.add_argument(
        "--output",
        choices=["table", "csv", "json"],
        default="table",
        help="Output format (default: table)",
    )
    parser.add_argument(
        "--output-file",
        type=str,
        default=None,
        help="Output file path (for csv/json)",
    )
    args = parser.parse_args()

    console = Console()

    # Status/Type 매핑
    status_filter = None if args.status == "all" else args.status.upper()
    type_filter = None if args.type == "all" else args.type.upper()

    console.print("[bold]Iconik Jobs 조회[/bold]")
    console.print(f"  기간: 최근 {args.days}일")
    console.print(f"  상태: {args.status}")
    console.print(f"  타입: {args.type}")
    if args.limit:
        console.print(f"  제한: {args.limit}개")
    console.print()

    jobs: list[IconikJob] = []
    summary = IconikJobSummary()

    with IconikClient() as client:
        # 연결 테스트
        if not client.health_check():
            console.print("[red]Iconik API 연결 실패[/red]")
            sys.exit(1)

        console.print("Jobs 조회 중...")

        for job in client.get_all_jobs(
            status=status_filter,
            job_type=type_filter,
            days=args.days,
        ):
            jobs.append(job)

            # Summary 업데이트
            summary.total += 1
            if job.status == "STARTED":
                summary.started += 1
            elif job.status == "FINISHED":
                summary.finished += 1
            elif job.status == "FAILED":
                summary.failed += 1
            elif job.status == "ABORTED":
                summary.aborted += 1

            summary.by_type[job.type] = summary.by_type.get(job.type, 0) + 1

            if job.storage_id:
                summary.by_storage[job.storage_id] = (
                    summary.by_storage.get(job.storage_id, 0) + 1
                )

            # 진행 상황 표시 (100개마다)
            if len(jobs) % 100 == 0:
                print(f"  ... {len(jobs)}개 조회됨", end="\r")

            if args.limit and len(jobs) >= args.limit:
                break

        print(f"  총 {len(jobs)}개 조회 완료")

    # 출력
    if args.output == "table":
        print_table(console, jobs, summary)
    elif args.output == "csv":
        export_csv(jobs, args.output_file)
        console.print(f"[green]CSV 저장 완료[/green]")
    elif args.output == "json":
        export_json(jobs, summary, args.output_file)
        console.print(f"[green]JSON 저장 완료[/green]")


def print_table(
    console: Console, jobs: list[IconikJob], summary: IconikJobSummary
) -> None:
    """Rich table로 출력."""
    # Summary
    console.print("\n[bold]Summary[/bold]")
    console.print(f"  Total: {summary.total}")
    if summary.started:
        console.print(f"  Started: [yellow]{summary.started}[/yellow]")
    if summary.finished:
        console.print(f"  Finished: [green]{summary.finished}[/green]")
    if summary.failed:
        console.print(f"  Failed: [red]{summary.failed}[/red]")
    if summary.aborted:
        console.print(f"  Aborted: [dim]{summary.aborted}[/dim]")

    # Type breakdown
    if summary.by_type:
        console.print("\n  By Type:")
        for job_type, count in sorted(
            summary.by_type.items(), key=lambda x: x[1], reverse=True
        ):
            console.print(f"    {job_type}: {count}")

    # Failed jobs detail
    failed_jobs = [j for j in jobs if j.status == "FAILED"]
    if failed_jobs:
        console.print(f"\n[bold red]Failed Jobs ({len(failed_jobs)})[/bold red]")

        table = Table(show_header=True, header_style="bold")
        table.add_column("ID", width=12, no_wrap=True)
        table.add_column("Type", width=12)
        table.add_column("Title", width=50)
        table.add_column("Error", width=40)
        table.add_column("Created", width=16)

        for job in failed_jobs[:30]:  # 최대 30개
            table.add_row(
                job.id[:12] + "...",
                job.type,
                (job.title or "")[:50],
                (job.error_message or "")[:40],
                (
                    job.date_created.strftime("%Y-%m-%d %H:%M")
                    if job.date_created
                    else ""
                ),
            )

        console.print(table)

        if len(failed_jobs) > 30:
            console.print(f"  [dim]... {len(failed_jobs) - 30}개 더 있음[/dim]")

    # Recent started jobs (in progress)
    started_jobs = [j for j in jobs if j.status == "STARTED"]
    if started_jobs:
        console.print(f"\n[bold yellow]In Progress Jobs ({len(started_jobs)})[/bold yellow]")

        table = Table(show_header=True, header_style="bold")
        table.add_column("ID", width=12, no_wrap=True)
        table.add_column("Type", width=12)
        table.add_column("Title", width=50)
        table.add_column("Progress", width=10)
        table.add_column("Started", width=16)

        for job in started_jobs[:20]:  # 최대 20개
            table.add_row(
                job.id[:12] + "...",
                job.type,
                (job.title or "")[:50],
                f"{job.progress}%",
                (
                    job.started_at.strftime("%Y-%m-%d %H:%M")
                    if job.started_at
                    else ""
                ),
            )

        console.print(table)


def export_csv(jobs: list[IconikJob], output_file: str | None) -> None:
    """CSV 내보내기."""
    filepath = output_file or f"jobs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "id",
                "status",
                "type",
                "title",
                "object_id",
                "progress",
                "error_message",
                "date_created",
                "completed_at",
            ],
        )
        writer.writeheader()
        for job in jobs:
            writer.writerow(
                {
                    "id": job.id,
                    "status": job.status,
                    "type": job.type,
                    "title": job.title,
                    "object_id": job.object_id,
                    "progress": job.progress,
                    "error_message": job.error_message,
                    "date_created": (
                        job.date_created.isoformat() if job.date_created else ""
                    ),
                    "completed_at": (
                        job.completed_at.isoformat() if job.completed_at else ""
                    ),
                }
            )

    print(f"CSV saved: {filepath}")


def export_json(
    jobs: list[IconikJob], summary: IconikJobSummary, output_file: str | None
) -> None:
    """JSON 내보내기."""
    filepath = output_file or f"jobs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    data = {
        "summary": summary.model_dump(),
        "jobs": [job.model_dump() for job in jobs],
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)

    print(f"JSON saved: {filepath}")


if __name__ == "__main__":
    main()

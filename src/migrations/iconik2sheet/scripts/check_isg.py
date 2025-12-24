"""Check ISG Status - Iconik Storage Gateway 상태 조회.

Usage:
    python -m scripts.check_isg              # ISG 상태 요약
    python -m scripts.check_isg --detail     # 상세 정보
    python -m scripts.check_isg --jobs       # 진행 중인 작업 포함
"""

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from iconik import IconikClient


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="ISG 상태 조회 - Iconik Storage Gateway 모니터링"
    )
    parser.add_argument(
        "--detail",
        action="store_true",
        help="상세 정보 표시",
    )
    parser.add_argument(
        "--jobs",
        action="store_true",
        help="진행 중인 작업 목록 포함",
    )
    args = parser.parse_args()

    console = Console()

    with IconikClient() as client:
        # 연결 테스트
        if not client.health_check():
            console.print("[red]Iconik API 연결 실패[/red]")
            sys.exit(1)

        # 1. Storage 목록 조회
        console.print("\n[bold]Iconik Storage (ISG) 상태[/bold]\n")

        storages = client._get("/files/v1/storages/")
        storage_list = storages.get("objects", [])

        # Storage 테이블
        table = Table(show_header=True, header_style="bold")
        table.add_column("Name", width=20)
        table.add_column("Method", width=8)
        table.add_column("Status", width=10)
        table.add_column("Scanner", width=10)
        table.add_column("Purpose", width=10)
        table.add_column("Last Scanned", width=20)

        for storage in storage_list:
            status = storage.get("status", "N/A")
            scanner = storage.get("scanner_status", "N/A")
            last_scanned = storage.get("last_scanned")

            # 상태에 따른 색상
            status_str = f"[green]{status}[/green]" if status == "ACTIVE" else f"[red]{status}[/red]"
            scanner_str = f"[green]{scanner}[/green]" if scanner == "ACTIVE" else f"[dim]{scanner}[/dim]"

            # Last Scanned 포맷
            if last_scanned:
                last_scanned_dt = datetime.fromisoformat(last_scanned.replace("+00:00", ""))
                last_scanned_str = last_scanned_dt.strftime("%Y-%m-%d %H:%M")
            else:
                last_scanned_str = "-"

            table.add_row(
                storage.get("name", "N/A"),
                storage.get("method", "N/A"),
                status_str,
                scanner_str,
                storage.get("purpose", "N/A"),
                last_scanned_str,
            )

        console.print(table)

        # 2. Jobs 통계
        console.print("\n[bold]Jobs 통계[/bold]\n")

        # 전체 통계
        total_resp = client._get("/jobs/v1/jobs/", params={"per_page": 1})
        started_resp = client._get("/jobs/v1/jobs/", params={"status": "STARTED", "per_page": 1})
        finished_resp = client._get("/jobs/v1/jobs/", params={"status": "FINISHED", "per_page": 1})
        failed_resp = client._get("/jobs/v1/jobs/", params={"status": "FAILED", "per_page": 1})

        total = total_resp.get("total", 0)
        started = started_resp.get("total", 0)
        finished = finished_resp.get("total", 0)
        failed = failed_resp.get("total", 0)

        stats_table = Table(show_header=False, box=None)
        stats_table.add_column("Label", width=20)
        stats_table.add_column("Value", width=10)

        stats_table.add_row("Total Jobs", str(total))
        stats_table.add_row("In Progress", f"[yellow]{started}[/yellow]" if started > 0 else "0")
        stats_table.add_row("Completed", f"[green]{finished}[/green]")
        stats_table.add_row("Failed", f"[red]{failed}[/red]" if failed > 0 else "0")

        console.print(stats_table)

        # 3. 진행 중인 작업 (--jobs 옵션)
        if args.jobs and started > 0:
            console.print("\n[bold yellow]진행 중인 작업[/bold yellow]\n")

            started_jobs = client._get("/jobs/v1/jobs/", params={"status": "STARTED", "per_page": 20})
            jobs = started_jobs.get("objects", [])

            jobs_table = Table(show_header=True, header_style="bold")
            jobs_table.add_column("Type", width=12)
            jobs_table.add_column("Title", width=50)
            jobs_table.add_column("Progress", width=10)
            jobs_table.add_column("Started", width=16)

            for job in jobs:
                started_at = job.get("started_at", "")[:16] if job.get("started_at") else "-"
                jobs_table.add_row(
                    job.get("type", "N/A"),
                    (job.get("title") or "")[:50],
                    f"{job.get('progress', 0)}%",
                    started_at,
                )

            console.print(jobs_table)

        # 4. 상세 정보 (--detail 옵션)
        if args.detail:
            console.print("\n[bold]Storage 상세 정보[/bold]\n")

            for storage in storage_list:
                if storage.get("method") == "FILE":  # ISG만 상세 표시
                    console.print(f"[bold cyan]{storage.get('name')}[/bold cyan]")
                    console.print(f"  ID: {storage.get('id')}")
                    console.print(f"  Method: {storage.get('method')}")
                    console.print(f"  Status: {storage.get('status')}")
                    console.print(f"  Scanner: {storage.get('scanner_status')}")
                    console.print(f"  Purpose: {storage.get('purpose')}")
                    console.print(f"  Last Scanned: {storage.get('last_scanned')}")

                    # Storage 경로 정보 (있는 경우)
                    if storage.get("path"):
                        console.print(f"  Path: {storage.get('path')}")
                    console.print()

        # 5. 실패 작업 요약
        if failed > 0:
            console.print(f"\n[bold red]실패한 작업 {failed}건[/bold red]")
            console.print("  상세 확인: python -m scripts.check_jobs --status failed")

        console.print()


if __name__ == "__main__":
    main()

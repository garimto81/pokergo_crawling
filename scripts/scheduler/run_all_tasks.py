"""
통합 실행 스크립트 - 모든 작업 순차 실행

PRD-0010: 세 가지 작업을 순차적으로 실행하고 결과 요약 제공

Usage:
    python scripts/scheduler/run_all_tasks.py              # 전체 실행
    python scripts/scheduler/run_all_tasks.py --task 1     # 작업 1만 실행
    python scripts/scheduler/run_all_tasks.py --task 1,2   # 작업 1, 2 실행
    python scripts/scheduler/run_all_tasks.py --dry-run    # 실행 없이 계획만 출력
"""

from __future__ import annotations

import argparse
import io
import sys
import time
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.scheduler.notifier import NotificationStatus, get_notifier  # noqa: E402


def run_all_tasks(
    tasks_to_run: list[int] | None = None,
    dry_run: bool = False,
) -> dict:
    """모든 작업 실행

    Args:
        tasks_to_run: 실행할 작업 번호 리스트 (None이면 전체 실행)
        dry_run: True면 실제 실행 없이 계획만 출력
    """
    start_time = time.time()
    notifier = get_notifier()

    # 로그 설정
    log_dir = PROJECT_ROOT / "logs" / "scheduler"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"{datetime.now().strftime('%Y-%m-%d')}_all_tasks.log"

    def log(msg: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        line = f"[{timestamp}] {msg}"
        print(line)
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(line + "\n")

    # 작업 정의
    tasks = [
        {
            "id": 1,
            "name": "NAMS_Task1_NAS_Scan",
            "description": "NAS 스캔 → Sheets",
            "module": "scripts.scheduler.task_nas_scan",
            "function": "run_task",
            "scheduled_time": "08:00",
        },
        {
            "id": 2,
            "name": "NAMS_Task2_Iconik_Export",
            "description": "Iconik → Sheets",
            "module": "scripts.scheduler.task_iconik_to_sheet",
            "function": "run_task",
            "scheduled_time": "08:30",
        },
        {
            "id": 3,
            "name": "NAMS_Task3_Iconik_Import",
            "description": "Sheets → Iconik",
            "module": "scripts.scheduler.task_sheet_to_iconik",
            "function": "run_task",
            "scheduled_time": "09:00",
        },
    ]

    # 실행할 작업 필터링
    if tasks_to_run:
        tasks = [t for t in tasks if t["id"] in tasks_to_run]

    log("=" * 60)
    log("NAMS 스케줄러 - 통합 실행")
    log("=" * 60)
    log(f"시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log(f"실행 모드: {'DRY RUN' if dry_run else 'LIVE'}")
    log(f"실행 작업: {[t['id'] for t in tasks]}")
    log("")

    results = {
        "start_time": datetime.now().isoformat(),
        "mode": "dry_run" if dry_run else "live",
        "tasks": [],
    }

    for task in tasks:
        log("-" * 40)
        log(f"[Task {task['id']}] {task['description']}")
        log(f"  스케줄: {task['scheduled_time']}")

        if dry_run:
            log("  상태: SKIP (dry-run)")
            results["tasks"].append(
                {"id": task["id"], "name": task["name"], "status": "skipped"}
            )
            continue

        try:
            # 동적 모듈 로드
            import importlib

            module = importlib.import_module(task["module"])
            run_func: Callable = getattr(module, task["function"])

            log("  실행 중...")
            task_result = run_func()

            status = task_result.get("status", "unknown")
            duration = task_result.get("duration", 0)

            results["tasks"].append(
                {
                    "id": task["id"],
                    "name": task["name"],
                    "status": status,
                    "duration": duration,
                    "result": task_result,
                }
            )

            if status == "success":
                log(f"  상태: SUCCESS ({duration:.1f}초)")
            else:
                log(f"  상태: FAILED - {task_result.get('error', 'Unknown')}")

        except Exception as e:
            error_msg = str(e)
            log(f"  상태: ERROR - {error_msg}")
            results["tasks"].append(
                {
                    "id": task["id"],
                    "name": task["name"],
                    "status": "error",
                    "error": error_msg,
                }
            )

    # 요약
    total_duration = time.time() - start_time
    success_count = sum(1 for t in results["tasks"] if t.get("status") == "success")
    failed_count = sum(1 for t in results["tasks"] if t.get("status") in ("failed", "error"))

    log("")
    log("=" * 60)
    log("실행 결과 요약")
    log("=" * 60)
    log(f"총 소요 시간: {total_duration:.1f}초")
    log(f"성공: {success_count} / 실패: {failed_count} / 전체: {len(results['tasks'])}")

    for t in results["tasks"]:
        status = t.get("status")
        if status == "success":
            status_icon = "O"
        elif status in ("failed", "error"):
            status_icon = "X"
        else:
            status_icon = "-"
        log(f"  [{status_icon}] Task {t['id']}: {t['name']}")

    results["end_time"] = datetime.now().isoformat()
    results["total_duration"] = total_duration
    results["summary"] = {"success": success_count, "failed": failed_count}

    # 전체 결과 알림
    if not dry_run:
        if failed_count == 0:
            notifier.send(
                "NAMS_Scheduler_All",
                NotificationStatus.SUCCESS,
                {
                    "Duration": f"{total_duration / 60:.1f}분",
                    "Tasks": f"{success_count}/{len(results['tasks'])} 성공",
                },
            )
        else:
            notifier.send(
                "NAMS_Scheduler_All",
                NotificationStatus.WARNING if success_count > 0 else NotificationStatus.FAILED,
                {
                    "Duration": f"{total_duration / 60:.1f}분",
                    "Success": success_count,
                    "Failed": failed_count,
                },
            )

    return results


def main():
    parser = argparse.ArgumentParser(description="NAMS 스케줄러 통합 실행")
    parser.add_argument(
        "--task",
        type=str,
        default=None,
        help="실행할 작업 번호 (콤마 구분, 예: 1,2,3)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="실행 없이 계획만 출력",
    )
    args = parser.parse_args()

    tasks_to_run = None
    if args.task:
        tasks_to_run = [int(t.strip()) for t in args.task.split(",")]

    results = run_all_tasks(tasks_to_run=tasks_to_run, dry_run=args.dry_run)

    # 실패 시 exit code 1
    failed = results.get("summary", {}).get("failed", 0)
    sys.exit(1 if failed > 0 else 0)


if __name__ == "__main__":
    main()

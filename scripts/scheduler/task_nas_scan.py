"""
작업 1: NAS 스캔 → Sheets (08:00)

PRD-0010: Y:/Z:/X: 드라이브 스캔 후 NAMS 시트 업데이트
"""

from __future__ import annotations

import sys
import time
from datetime import datetime
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.scheduler.notifier import get_notifier  # noqa: E402


def check_drives_available() -> tuple[bool, list[str]]:
    """드라이브 연결 상태 확인"""
    drives = ["Y:", "Z:", "X:"]
    missing = []
    for drive in drives:
        if not Path(drive).exists():
            missing.append(drive)
    return len(missing) == 0, missing


def create_lock_file() -> Path | None:
    """중복 실행 방지용 락 파일 생성"""
    lock_dir = PROJECT_ROOT / "logs" / "scheduler"
    lock_dir.mkdir(parents=True, exist_ok=True)
    lock_file = lock_dir / "task_nas_scan.lock"

    if lock_file.exists():
        # 락 파일이 1시간 이상 오래된 경우 삭제 (stuck된 경우 대비)
        lock_age = time.time() - lock_file.stat().st_mtime
        if lock_age > 3600:  # 1시간
            lock_file.unlink()
        else:
            return None

    lock_file.write_text(str(datetime.now()))
    return lock_file


def remove_lock_file(lock_file: Path):
    """락 파일 삭제"""
    if lock_file and lock_file.exists():
        lock_file.unlink()


def run_task() -> dict:
    """NAS 스캔 작업 실행"""
    task_name = "NAMS_Task1_NAS_Scan"
    start_time = time.time()
    notifier = get_notifier()

    # 로그 파일 설정
    log_dir = PROJECT_ROOT / "logs" / "scheduler"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"{datetime.now().strftime('%Y-%m-%d')}_task1.log"

    def log(msg: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        line = f"[{timestamp}] {msg}"
        print(line)
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(line + "\n")

    log(f"=== {task_name} 시작 ===")

    # 락 파일 확인
    lock_file = create_lock_file()
    if lock_file is None:
        log("ERROR: 이미 실행 중인 작업이 있습니다.")
        notifier.send_failure(
            task_name,
            error_message="Lock file exists - another instance is running",
        )
        return {"status": "skipped", "reason": "already_running"}

    try:
        # 드라이브 연결 확인
        available, missing = check_drives_available()
        if not available:
            log(f"ERROR: 드라이브 미연결: {missing}")
            notifier.send_failure(
                task_name,
                error_message=f"Drives not available: {missing}",
            )
            return {"status": "failed", "reason": "drives_not_available", "missing": missing}

        log("드라이브 연결 확인 완료: Y:, Z:, X:")

        # daily_scan.py 호출
        from scripts.daily_scan import run_daily_scan

        log("일일 스캔 시작...")
        stats = run_daily_scan(
            mode="daily",
            drives="Y:,Z:,X:",
            sync_sheets=True,
        )

        duration = time.time() - start_time
        log(f"스캔 완료: {stats}")

        # 성공 알림
        notifier.send_success(
            task_name,
            duration_seconds=duration,
            New_Files=stats.get("new_files", 0),
            Updated=stats.get("updated_files", 0),
            Missing=stats.get("missing_files", 0),
            Total=stats.get("total_scanned", 0),
        )

        log(f"=== {task_name} 완료 (소요: {duration:.1f}초) ===")
        return {"status": "success", "stats": stats, "duration": duration}

    except Exception as e:
        duration = time.time() - start_time
        error_msg = str(e)
        log(f"ERROR: {error_msg}")

        notifier.send_failure(
            task_name,
            error_message=error_msg,
            duration_seconds=duration,
        )

        log(f"=== {task_name} 실패 ===")
        return {"status": "failed", "error": error_msg, "duration": duration}

    finally:
        remove_lock_file(lock_file)


def main():
    result = run_task()
    sys.exit(0 if result.get("status") == "success" else 1)


if __name__ == "__main__":
    main()

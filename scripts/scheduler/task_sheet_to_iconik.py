"""
작업 3: Sheets → Iconik (09:00)

PRD-0010: Iconik_Full_Metadata 시트에서 수정된 메타데이터 읽기, Iconik API로 업데이트
"""

from __future__ import annotations

import io
import sys
import time
from datetime import datetime
from pathlib import Path

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.scheduler.notifier import get_notifier  # noqa: E402


def create_lock_file() -> Path | None:
    """중복 실행 방지용 락 파일 생성"""
    lock_dir = PROJECT_ROOT / "logs" / "scheduler"
    lock_dir.mkdir(parents=True, exist_ok=True)
    lock_file = lock_dir / "task_sheet_to_iconik.lock"

    if lock_file.exists():
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
    """Sheets → Iconik 동기화 작업 실행"""
    task_name = "NAMS_Task3_Iconik_Import"
    start_time = time.time()
    notifier = get_notifier()

    # 로그 파일 설정
    log_dir = PROJECT_ROOT / "logs" / "scheduler"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"{datetime.now().strftime('%Y-%m-%d')}_task3.log"

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
        # iconik2sheet 모듈 경로 추가
        iconik2sheet_path = PROJECT_ROOT / "src" / "migrations" / "iconik2sheet"
        sys.path.insert(0, str(iconik2sheet_path))

        # .env.local 로드 (iconik2sheet 전용 환경변수)
        from dotenv import load_dotenv

        env_local = iconik2sheet_path / ".env.local"
        if env_local.exists():
            load_dotenv(env_local)
            log(f"환경변수 로드: {env_local}")

        # IncrementalReverseSync 실행 (증분 처리)
        import os

        from scripts.reverse_sync import IncrementalReverseSync

        force_full = os.environ.get("NAMS_FORCE_FULL_SYNC") == "1"
        log(f"Sheets → Iconik {'전체' if force_full else '증분'} 동기화 시작 (metadata-only)...")
        sync = IncrementalReverseSync()
        result = sync.run(
            dry_run=False,
            metadata_only=True,  # 메타데이터만 동기화 (timecode는 수동)
            force_full=force_full,
        )

        duration = time.time() - start_time

        if "error" not in result:
            log(f"동기화 완료: {result}")
            metadata_stats = result.get("metadata", {})
            notifier.send_success(
                task_name,
                duration_seconds=duration,
                Total=result.get("total", 0),
                Updated=metadata_stats.get("updated", 0),
                Failed=metadata_stats.get("failed", 0),
                Sync_ID=result.get("sync_id", "N/A"),
            )
            log(f"=== {task_name} 완료 (소요: {duration:.1f}초) ===")
            return {"status": "success", "result": result, "duration": duration}
        else:
            error_msg = result.get("error", "Unknown error")
            log(f"ERROR: {error_msg}")
            notifier.send_failure(
                task_name,
                error_message=error_msg,
                duration_seconds=duration,
            )
            log(f"=== {task_name} 실패 ===")
            return {"status": "failed", "error": error_msg, "duration": duration}

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

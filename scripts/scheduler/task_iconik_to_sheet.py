"""
작업 2: Iconik → Sheets (08:30)

PRD-0010: Iconik API에서 전체 Asset 조회, 35컬럼 메타데이터 추출, Sheets 저장
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


def create_lock_file() -> Path | None:
    """중복 실행 방지용 락 파일 생성"""
    lock_dir = PROJECT_ROOT / "logs" / "scheduler"
    lock_dir.mkdir(parents=True, exist_ok=True)
    lock_file = lock_dir / "task_iconik_to_sheet.lock"

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
    """Iconik → Sheets 동기화 작업 실행"""
    task_name = "NAMS_Task2_Iconik_Export"
    start_time = time.time()
    notifier = get_notifier()

    # 로그 파일 설정
    log_dir = PROJECT_ROOT / "logs" / "scheduler"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"{datetime.now().strftime('%Y-%m-%d')}_task2.log"

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

        # FullMetadataSync 실행
        from sync.full_metadata_sync import FullMetadataSync

        log("Iconik → Sheets 동기화 시작...")
        sync = FullMetadataSync()
        result = sync.run(skip_sampling=True)  # 스케줄러에서는 샘플링 스킵

        duration = time.time() - start_time

        if result.get("status") == "success":
            log(f"동기화 완료: {result}")
            notifier.send_success(
                task_name,
                duration_seconds=duration,
                Assets=result.get("assets_processed", 0),
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

"""Run NAMS servers (API + UI).

Usage:
    python run_nams.py          # Run API server only
    python run_nams.py api      # Run API server only
    python run_nams.py ui       # Run UI dev server only
    python run_nams.py all      # Run both (separate terminals needed)
"""
import sys
import subprocess
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
UI_DIR = PROJECT_ROOT / "src" / "nams" / "ui"


def run_api():
    """Run the NAMS API server."""
    import uvicorn
    print("=" * 50)
    print("  NAMS API Server")
    print("=" * 50)
    print("  URL:  http://localhost:8002")
    print("  Docs: http://localhost:8002/docs")
    print("=" * 50)

    uvicorn.run(
        "src.nams.api.main:app",
        host="0.0.0.0",
        port=8002,
        reload=True,
    )


def run_ui():
    """Run the NAMS UI dev server."""
    print("=" * 50)
    print("  NAMS UI Server")
    print("=" * 50)
    print("  URL: http://localhost:5174")
    print("=" * 50)

    os.chdir(UI_DIR)
    # Windows에서는 shell=True로 문자열 명령어 실행
    subprocess.run("npm run dev", shell=True)


def main():
    if len(sys.argv) < 2 or sys.argv[1] == "api":
        run_api()
    elif sys.argv[1] == "ui":
        run_ui()
    elif sys.argv[1] == "all":
        print("To run both servers, open two terminals:")
        print()
        print("  Terminal 1 (API): python run_nams.py api")
        print("  Terminal 2 (UI):  python run_nams.py ui")
        print()
        print("Or use the combined command:")
        print("  start /B python run_nams.py api && cd src/nams/ui && npm run dev")
    else:
        print(__doc__)


if __name__ == "__main__":
    main()

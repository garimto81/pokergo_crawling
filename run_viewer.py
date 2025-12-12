#!/usr/bin/env python
"""
Run Matching Result Viewer
Starts both FastAPI backend and React frontend
"""

import subprocess
import sys
import os
from pathlib import Path

ROOT = Path(__file__).parent
API_DIR = ROOT / "src" / "api"
UI_DIR = ROOT / "src" / "ui"


def run_api():
    """Start FastAPI backend"""
    print("\n[API] Starting FastAPI server...")
    print("[API] URL: http://localhost:8000")
    print("[API] Docs: http://localhost:8000/docs")

    os.chdir(ROOT)
    subprocess.run([
        sys.executable, "-m", "uvicorn",
        "src.api.main:app",
        "--reload",
        "--host", "0.0.0.0",
        "--port", "8000"
    ])


def run_ui():
    """Start React frontend"""
    print("\n[UI] Starting React development server...")
    print("[UI] URL: http://localhost:5173")

    os.chdir(UI_DIR)
    subprocess.run(["npm", "run", "dev"], shell=True)


def main():
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "api":
            run_api()
        elif cmd == "ui":
            run_ui()
        else:
            print(f"Unknown command: {cmd}")
            print("Usage: python run_viewer.py [api|ui]")
    else:
        print("=" * 60)
        print("PokerGO Content Matcher - Matching Result Viewer")
        print("=" * 60)
        print("\nTo start the application, run in two terminals:")
        print("\n  Terminal 1 (API):")
        print("    python run_viewer.py api")
        print("\n  Terminal 2 (UI):")
        print("    python run_viewer.py ui")
        print("\nOr start manually:")
        print("\n  API:  uvicorn src.api.main:app --reload")
        print("  UI:   cd src/ui && npm run dev")
        print("\n" + "=" * 60)


if __name__ == "__main__":
    main()

"""Extract WSOP files from NAS database"""

import sqlite3
import json
from pathlib import Path

DB_PATH = Path("D:/AI/claude01/pokergo_crawling/data/db/pokergo.db")
OUTPUT_DIR = Path("D:/AI/claude01/pokergo_crawling/data/pokergo/wsop_only")

def main():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 전체 NAS 파일 가져오기
    cursor.execute("""
        SELECT id, nas_filename, nas_directory, nas_size_bytes
        FROM content_mapping
    """)
    rows = cursor.fetchall()

    all_files = []
    wsop_files = []

    for row in rows:
        file_data = {
            "id": row[0],
            "filename": row[1],
            "directory": row[2],
            "size_bytes": row[3],
            "size_gb": round(row[3] / (1024**3), 2) if row[3] else 0
        }
        all_files.append(file_data)

        # WSOP 키워드 체크
        filename_upper = (row[1] or "").upper()
        if "WSOP" in filename_upper or "WORLD SERIES" in filename_upper:
            wsop_files.append(file_data)

    print(f"Total NAS files: {len(all_files)}")
    print(f"WSOP NAS files: {len(wsop_files)}")

    # WSOP 파일 저장
    OUTPUT_DIR.mkdir(exist_ok=True)

    with open(OUTPUT_DIR / "nas_wsop_files.json", "w", encoding="utf-8") as f:
        json.dump({
            "total": len(wsop_files),
            "files": wsop_files
        }, f, ensure_ascii=False, indent=2)

    # 연도별 분포 추정
    years = {}
    for f in wsop_files:
        fname = f["filename"]
        found = False
        for year in range(2010, 2026):
            if str(year) in fname:
                years[year] = years.get(year, 0) + 1
                found = True
                break
        if not found:
            years["unknown"] = years.get("unknown", 0) + 1

    print(f"\n=== WSOP NAS by Year ===")
    for year, count in sorted(years.items(), key=lambda x: str(x[0]), reverse=True):
        print(f"  {year}: {count} files")

    # 파일명 패턴 분석
    print(f"\n=== WSOP NAS File Samples ===")
    for f in wsop_files[:20]:
        fname = f["filename"][:80]
        print(f"  {fname}")

    conn.close()
    print(f"\nSaved to: {OUTPUT_DIR / 'nas_wsop_files.json'}")


if __name__ == "__main__":
    main()

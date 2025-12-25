"""Scan NAS and create comprehensive file database."""
import os
import sys
import json
import re
import argparse
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# 스캔 대상 드라이브 설정
SCAN_PATHS = {
    "origin": Path("Y:/"),                   # Origin (Y: 드라이브 전체)
    "archive": Path("Z:/"),                 # Archive (Z: 드라이브)
    "pokergo": Path("X:/GGP Footage/POKERGO"),  # PokerGO Source (X: 드라이브)
}

NAS_ROOT = Path("Z:/")
OUTPUT_DIR = Path("data/sources/nas")

def parse_filename(filepath):
    """Extract metadata from filename."""
    filename = filepath.stem

    metadata = {
        "filename": filepath.name,
        "extension": filepath.suffix.lower(),
        "size_bytes": filepath.stat().st_size if filepath.exists() else 0,
        "modified": datetime.fromtimestamp(filepath.stat().st_mtime).isoformat() if filepath.exists() else None,
    }

    # Try to parse WSOP-style filenames
    # Pattern: [order]-wsop-[year]-[type]-ev-[event#]-[description]
    wsop_match = re.match(r'(\d+)-wsop-(\d{4})-([a-z]+)-ev-(\d+)-(.+)', filename, re.I)
    if wsop_match:
        metadata.update({
            "order": int(wsop_match.group(1)),
            "year": int(wsop_match.group(2)),
            "event_type": wsop_match.group(3),
            "event_number": int(wsop_match.group(4)),
            "description": wsop_match.group(5).replace('-', ' '),
            "source": "wsop"
        })
        return metadata

    # Try to parse GOG-style filenames
    # Pattern: E##_GOG_...
    gog_match = re.match(r'E(\d+)_GOG_(.+)', filename, re.I)
    if gog_match:
        metadata.update({
            "episode": int(gog_match.group(1)),
            "description": gog_match.group(2).replace('_', ' '),
            "source": "gog"
        })
        return metadata

    # Generic parsing
    metadata["description"] = filename
    metadata["source"] = "unknown"

    return metadata

def scan_directory(root_path, base_path=""):
    """Recursively scan directory and collect file info."""
    files = []

    for entry in os.scandir(root_path):
        if entry.name.startswith('.') or entry.name == 'Thumbs.db':
            continue

        relative_path = os.path.join(base_path, entry.name) if base_path else entry.name

        if entry.is_dir():
            files.extend(scan_directory(entry.path, relative_path))
        elif entry.is_file():
            ext = os.path.splitext(entry.name)[1].lower()
            if ext in ['.mp4', '.mkv', '.mov', '.avi', '.wmv', '.m4v', '.mxf']:
                filepath = Path(entry.path)
                file_info = parse_filename(filepath)
                file_info["relative_path"] = relative_path
                file_info["full_path"] = str(filepath)
                file_info["directory"] = base_path
                files.append(file_info)

    return files

def format_duration(seconds):
    """Format seconds to HH:MM:SS."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    return f"{hours}h {minutes}m"

def format_size(bytes_size):
    """Format bytes to human readable."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_size < 1024:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024
    return f"{bytes_size:.1f} PB"

def main():
    parser = argparse.ArgumentParser(description='NAS 스캔 스크립트')
    parser.add_argument('--folder', choices=['origin', 'archive', 'pokergo', 'all'],
                        default='archive', help='스캔할 폴더 (default: archive)')
    parser.add_argument('--mode', choices=['full', 'incremental'],
                        default='full', help='스캔 모드')
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 스캔할 경로 결정
    if args.folder == 'all':
        scan_targets = list(SCAN_PATHS.items())
    else:
        scan_targets = [(args.folder, SCAN_PATHS[args.folder])]

    all_files = []

    for folder_name, scan_root in scan_targets:
        if not scan_root.exists():
            print(f"[SKIP] {folder_name}: {scan_root} 경로가 존재하지 않습니다")
            continue

        print(f"\n{'='*60}")
        print(f"Scanning {folder_name}: {scan_root}")
        print(f"{'='*60}")

        # 스캔 대상 결정
        if scan_root == Path("Z:/"):
            # Z: 드라이브는 기존 방식 (하위 디렉토리 스캔)
            directories_to_scan = []
            for item in scan_root.iterdir():
                if item.is_dir() and not item.name.startswith('.'):
                    directories_to_scan.append((item.name, item))

            for name, path in directories_to_scan:
                if path.exists():
                    print(f"  Scanning {name}...")
                    files = scan_directory(path, name)
                    for f in files:
                        f['source_folder'] = folder_name
                    all_files.extend(files)
                    print(f"    Found {len(files)} video files")
        else:
            # Y:, X: 드라이브는 직접 스캔
            print(f"  Scanning {scan_root}...")
            files = scan_directory(scan_root, folder_name)
            for f in files:
                f['source_folder'] = folder_name
            all_files.extend(files)
            print(f"    Found {len(files)} video files")

    print(f"\nTotal files found: {len(all_files)}")

    # Organize by directory
    by_directory = defaultdict(list)
    for f in all_files:
        by_directory[f["directory"]].append(f)

    # Calculate statistics
    total_size = sum(f["size_bytes"] for f in all_files)

    # Create summary
    summary = {
        "scan_date": datetime.now().isoformat(),
        "total_files": len(all_files),
        "total_size_bytes": total_size,
        "total_size_formatted": format_size(total_size),
        "directories": {}
    }

    for dir_path, files in sorted(by_directory.items()):
        dir_size = sum(f["size_bytes"] for f in files)
        summary["directories"][dir_path] = {
            "count": len(files),
            "size_bytes": dir_size,
            "size_formatted": format_size(dir_size)
        }

    # Save summary
    with open(OUTPUT_DIR / "nas_summary.json", 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    # Save full file list
    with open(OUTPUT_DIR / "nas_files.json", 'w', encoding='utf-8') as f:
        json.dump({
            "scan_date": datetime.now().isoformat(),
            "total_files": len(all_files),
            "files": all_files
        }, f, ensure_ascii=False)

    # Print summary
    print(f"\n{'='*60}")
    print(f"NAS Scan Summary")
    print(f"{'='*60}")
    print(f"Total Files: {len(all_files)}")
    print(f"Total Size: {format_size(total_size)}")
    print(f"\nBy Directory:")
    for dir_path, info in sorted(summary["directories"].items(), key=lambda x: -x[1]["count"]):
        print(f"  [{info['count']:>4}] {dir_path[:50]:<50} ({info['size_formatted']})")

    print(f"\nOutput saved to {OUTPUT_DIR}")

if __name__ == "__main__":
    main()

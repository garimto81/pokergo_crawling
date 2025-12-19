"""Analyze NAS folder structure and filename patterns."""
import os
import re
from pathlib import Path
from collections import defaultdict, Counter
import json

# NAS paths
ORIGIN_PATH = Path("Y:/WSOP Backup")
ARCHIVE_PATH = Path("Z:/archive")

# Video extensions
VIDEO_EXTENSIONS = {'.mp4', '.mkv', '.mov', '.avi', '.wmv', '.m4v', '.mxf'}


def scan_folder_structure(root_path: Path, max_depth: int = 5) -> dict:
    """Scan folder structure."""
    structure = {
        "root": str(root_path),
        "folders": [],
        "files": [],
        "file_count": 0,
        "folder_count": 0,
    }

    if not root_path.exists():
        return structure

    for item in root_path.rglob("*"):
        rel_path = item.relative_to(root_path)
        depth = len(rel_path.parts)

        if depth > max_depth:
            continue

        if item.is_dir():
            structure["folders"].append(str(rel_path))
            structure["folder_count"] += 1
        elif item.is_file() and item.suffix.lower() in VIDEO_EXTENSIONS:
            structure["files"].append({
                "path": str(rel_path),
                "filename": item.name,
                "folder": str(rel_path.parent),
                "extension": item.suffix.lower(),
            })
            structure["file_count"] += 1

    return structure


def analyze_patterns(files: list) -> dict:
    """Analyze filename patterns."""
    patterns = {
        "folder_patterns": Counter(),
        "filename_patterns": [],
        "year_formats": Counter(),
        "region_indicators": Counter(),
        "event_types": Counter(),
        "episode_formats": Counter(),
        "separators": Counter(),
        "extensions": Counter(),
    }

    # Known patterns
    known_patterns = [
        (r'^WSOP(\d{2})[_-]([A-Z]+)[_-]([A-Z]+)[_-](\d+)', "WSOP{YY}_{REGION}_{TYPE}_{EP}"),
        (r'^WSOP(\d{4})[_-]([A-Z]+)[_-]([A-Z]+)[_-](\d+)', "WSOP{YYYY}_{REGION}_{TYPE}_{EP}"),
        (r'^WS(\d{2})[_-]([A-Z]+)(\d+)', "WS{YY}_{TYPE}{EP}"),
        (r'^(\d+)-wsop-(\d{4})-([a-z]+)-ev-(\d+)', "{ORDER}-wsop-{YYYY}-{type}-ev-{EP}"),
        (r'^E(\d+)[_-]GOG', "E{EP}_GOG..."),
        (r'^WSOP[_-]?(\d{2,4})', "WSOP_{YEAR}..."),
        (r'APAC', "Contains APAC"),
        (r'EUROPE|_EU_', "Contains EU/EUROPE"),
        (r'PARADISE', "Contains PARADISE"),
        (r'[_-]ME[_-]', "Contains ME (Main Event)"),
        (r'[_-]GM[_-]', "Contains GM (Grudge Match)"),
        (r'[_-]HU[_-]', "Contains HU (Heads Up)"),
        (r'[_-]BR[_-]', "Contains BR (Bracelet)"),
    ]

    matched_patterns = defaultdict(list)
    unmatched_files = []

    for file_info in files:
        filename = file_info["filename"]
        folder = file_info["folder"]
        ext = file_info["extension"]

        patterns["extensions"][ext] += 1

        # Analyze folder
        if folder and folder != ".":
            # Extract folder pattern
            folder_parts = folder.replace("\\", "/").split("/")
            for part in folder_parts:
                patterns["folder_patterns"][part] += 1

        # Analyze separators
        if "_" in filename:
            patterns["separators"]["underscore"] += 1
        if "-" in filename:
            patterns["separators"]["hyphen"] += 1

        # Check against known patterns
        matched = False
        for regex, pattern_name in known_patterns:
            if re.search(regex, filename, re.I):
                matched_patterns[pattern_name].append(filename)
                matched = True

        if not matched:
            unmatched_files.append(filename)

        # Year extraction
        year_match = re.search(r'(?:WSOP?|WS)[_-]?(\d{2,4})', filename, re.I)
        if year_match:
            year_str = year_match.group(1)
            if len(year_str) == 2:
                patterns["year_formats"]["YY (2-digit)"] += 1
            else:
                patterns["year_formats"]["YYYY (4-digit)"] += 1

        # Region extraction
        if "APAC" in filename.upper():
            patterns["region_indicators"]["APAC"] += 1
        if "EU" in filename.upper() or "EUROPE" in filename.upper():
            patterns["region_indicators"]["EU/EUROPE"] += 1
        if "PARADISE" in filename.upper():
            patterns["region_indicators"]["PARADISE"] += 1

        # Event type extraction
        for etype in ["ME", "GM", "HU", "BR", "HR", "FT"]:
            if re.search(rf'[_-]{etype}[_-]', filename, re.I):
                patterns["event_types"][etype] += 1
                break

    patterns["matched_patterns"] = {k: len(v) for k, v in matched_patterns.items()}
    patterns["unmatched_count"] = len(unmatched_files)
    patterns["sample_unmatched"] = unmatched_files[:20]
    patterns["sample_matched"] = {k: v[:5] for k, v in matched_patterns.items()}

    return patterns


def main():
    print("=" * 70)
    print("  NAS Pattern Analysis")
    print("=" * 70)

    all_files = []
    all_folders = []

    # Scan Origin
    print(f"\n[1/2] Scanning Origin: {ORIGIN_PATH}")
    if ORIGIN_PATH.exists():
        origin_structure = scan_folder_structure(ORIGIN_PATH)
        print(f"  Folders: {origin_structure['folder_count']}")
        print(f"  Files: {origin_structure['file_count']}")
        all_files.extend(origin_structure["files"])
        all_folders.extend(origin_structure["folders"])

        print("\n  Folder Structure (Origin):")
        for folder in sorted(set(origin_structure["folders"]))[:30]:
            print(f"    {folder}")
    else:
        print(f"  [SKIP] Path not found")

    # Scan Archive
    print(f"\n[2/2] Scanning Archive: {ARCHIVE_PATH}")
    if ARCHIVE_PATH.exists():
        archive_structure = scan_folder_structure(ARCHIVE_PATH)
        print(f"  Folders: {archive_structure['folder_count']}")
        print(f"  Files: {archive_structure['file_count']}")
        all_files.extend(archive_structure["files"])
        all_folders.extend(archive_structure["folders"])

        print("\n  Folder Structure (Archive):")
        for folder in sorted(set(archive_structure["folders"]))[:30]:
            print(f"    {folder}")
    else:
        print(f"  [SKIP] Path not found")

    # Analyze patterns
    print("\n" + "=" * 70)
    print("  Pattern Analysis")
    print("=" * 70)

    analysis = analyze_patterns(all_files)

    print("\n[Folder Patterns] (Top 20)")
    for folder, count in analysis["folder_patterns"].most_common(20):
        print(f"  {count:>4}x  {folder}")

    print("\n[Extensions]")
    for ext, count in analysis["extensions"].most_common():
        print(f"  {count:>4}x  {ext}")

    print("\n[Year Formats]")
    for fmt, count in analysis["year_formats"].most_common():
        print(f"  {count:>4}x  {fmt}")

    print("\n[Region Indicators]")
    for region, count in analysis["region_indicators"].most_common():
        print(f"  {count:>4}x  {region}")

    print("\n[Event Types]")
    for etype, count in analysis["event_types"].most_common():
        print(f"  {count:>4}x  {etype}")

    print("\n[Separators]")
    for sep, count in analysis["separators"].most_common():
        print(f"  {count:>4}x  {sep}")

    print("\n[Matched Patterns]")
    for pattern, count in sorted(analysis["matched_patterns"].items(), key=lambda x: -x[1]):
        print(f"  {count:>4}x  {pattern}")

    print(f"\n[Unmatched Files] ({analysis['unmatched_count']} files)")
    for filename in analysis["sample_unmatched"]:
        print(f"    {filename}")

    print("\n[Sample Filenames by Pattern]")
    for pattern, samples in analysis["sample_matched"].items():
        print(f"\n  {pattern}:")
        for sample in samples[:3]:
            print(f"    - {sample}")

    # Save full analysis
    output_path = Path("data/analysis/nas_pattern_analysis.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({
            "total_files": len(all_files),
            "total_folders": len(set(all_folders)),
            "folder_patterns": dict(analysis["folder_patterns"]),
            "extensions": dict(analysis["extensions"]),
            "year_formats": dict(analysis["year_formats"]),
            "region_indicators": dict(analysis["region_indicators"]),
            "event_types": dict(analysis["event_types"]),
            "separators": dict(analysis["separators"]),
            "matched_patterns": analysis["matched_patterns"],
            "unmatched_count": analysis["unmatched_count"],
            "sample_unmatched": analysis["sample_unmatched"],
            "all_files": all_files,
        }, f, ensure_ascii=False, indent=2)

    print(f"\n[Output] Saved to: {output_path}")

    return analysis


if __name__ == "__main__":
    main()

"""Analyze Archive folder structure and filename patterns in detail."""
import os
import re
import sys
from pathlib import Path
from collections import defaultdict, Counter
import json

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ARCHIVE_PATH = Path("Z:/archive")
VIDEO_EXTENSIONS = {'.mp4', '.mkv', '.mov', '.avi', '.wmv', '.m4v', '.mxf'}


def get_full_structure(root_path: Path) -> dict:
    """Get complete folder and file structure."""
    structure = defaultdict(lambda: {"folders": [], "files": [], "file_count": 0})

    if not root_path.exists():
        return {}

    for item in root_path.rglob("*"):
        rel_path = item.relative_to(root_path)

        if item.is_file() and item.suffix.lower() in VIDEO_EXTENSIONS:
            # Get top-level category
            parts = rel_path.parts
            top_level = parts[0] if parts else "root"

            structure[top_level]["files"].append({
                "full_path": str(rel_path),
                "filename": item.name,
                "folder": str(rel_path.parent),
                "extension": item.suffix.lower(),
                "size_mb": item.stat().st_size / (1024 * 1024) if item.exists() else 0,
            })
            structure[top_level]["file_count"] += 1

        elif item.is_dir():
            parts = rel_path.parts
            top_level = parts[0] if parts else "root"
            structure[top_level]["folders"].append(str(rel_path))

    return dict(structure)


def analyze_category(category: str, data: dict) -> dict:
    """Analyze patterns within a category."""
    files = data.get("files", [])
    folders = data.get("folders", [])

    analysis = {
        "file_count": len(files),
        "folder_count": len(folders),
        "total_size_gb": sum(f["size_mb"] for f in files) / 1024,
        "extensions": Counter(f["extension"] for f in files),
        "folder_patterns": [],
        "filename_patterns": [],
        "sample_files": [],
        "unique_folders": sorted(set(folders)),
    }

    # Analyze folder patterns
    folder_parts = Counter()
    for folder in folders:
        for part in folder.replace("\\", "/").split("/"):
            folder_parts[part] += 1

    analysis["folder_parts"] = dict(folder_parts.most_common(20))

    # Analyze filename patterns
    filename_patterns = defaultdict(list)

    for f in files:
        filename = f["filename"]
        folder = f["folder"]

        # Extract patterns
        patterns_found = []

        # Year patterns
        year_match = re.search(r'(\d{4})', filename)
        if year_match:
            year = int(year_match.group(1))
            if 1970 <= year <= 2030:
                patterns_found.append(f"YEAR:{year}")

        # WSOP patterns
        if re.search(r'WSOP', filename, re.I):
            patterns_found.append("WSOP")
        if re.search(r'\bWS\d{2}', filename, re.I):
            patterns_found.append("WS{YY}")

        # Event types
        if re.search(r'[_-]ME[_\-\d]', filename, re.I) or 'Main Event' in filename:
            patterns_found.append("ME")
        if re.search(r'[_-]GM[_\-\d]', filename, re.I) or 'Grudge' in filename:
            patterns_found.append("GM")
        if re.search(r'[_-]HU[_\-\d]', filename, re.I) or 'Heads Up' in filename:
            patterns_found.append("HU")
        if re.search(r'[_-]BR[_\-\d]', filename, re.I) or 'Bracelet' in filename:
            patterns_found.append("BR")

        # Region patterns
        if 'APAC' in filename.upper():
            patterns_found.append("APAC")
        if 'EUROPE' in filename.upper() or '_EU_' in filename.upper():
            patterns_found.append("EU")
        if 'PARADISE' in filename.upper():
            patterns_found.append("PARADISE")

        # Episode patterns
        ep_match = re.search(r'[_-](\d{1,2})[_\.\-]|EP?(\d{1,2})', filename, re.I)
        if ep_match:
            patterns_found.append("EPISODE")

        # GOG pattern
        if 'GOG' in filename.upper():
            patterns_found.append("GOG")

        # HCL pattern
        if 'HCL' in filename.upper():
            patterns_found.append("HCL")

        # MPP pattern
        if 'MPP' in filename.upper():
            patterns_found.append("MPP")

        # PAD pattern
        if 'PAD' in filename.upper():
            patterns_found.append("PAD")

        key = "+".join(sorted(patterns_found)) if patterns_found else "UNKNOWN"
        filename_patterns[key].append(filename)

    analysis["filename_patterns"] = {k: len(v) for k, v in filename_patterns.items()}
    analysis["pattern_samples"] = {k: v[:5] for k, v in filename_patterns.items()}

    # Sample files
    analysis["sample_files"] = [f["filename"] for f in files[:20]]

    return analysis


def main():
    print("=" * 80)
    print("  Archive Folder Pattern Analysis")
    print("=" * 80)

    if not ARCHIVE_PATH.exists():
        print(f"[ERROR] Archive path not found: {ARCHIVE_PATH}")
        return

    # Get full structure
    print(f"\n[Scanning] {ARCHIVE_PATH}")
    structure = get_full_structure(ARCHIVE_PATH)

    print(f"\n[Categories Found] {len(structure)}")
    for cat in sorted(structure.keys()):
        print(f"  - {cat}: {structure[cat]['file_count']} files")

    # Analyze each category
    full_analysis = {}

    for category in sorted(structure.keys()):
        print(f"\n{'='*80}")
        print(f"  Category: {category}")
        print("=" * 80)

        analysis = analyze_category(category, structure[category])
        full_analysis[category] = analysis

        print(f"\n  Files: {analysis['file_count']}")
        print(f"  Folders: {analysis['folder_count']}")
        print(f"  Size: {analysis['total_size_gb']:.2f} GB")

        print(f"\n  [Extensions]")
        for ext, count in analysis["extensions"].most_common():
            print(f"    {count:>4}x  {ext}")

        print(f"\n  [Unique Folders] ({len(analysis['unique_folders'])})")
        for folder in analysis["unique_folders"][:15]:
            print(f"    {folder}")
        if len(analysis["unique_folders"]) > 15:
            print(f"    ... and {len(analysis['unique_folders']) - 15} more")

        print(f"\n  [Filename Patterns]")
        for pattern, count in sorted(analysis["filename_patterns"].items(), key=lambda x: -x[1]):
            print(f"    {count:>4}x  {pattern}")

        print(f"\n  [Sample Files]")
        for filename in analysis["sample_files"][:10]:
            print(f"    {filename}")

    # Save analysis
    output_path = Path("data/analysis/archive_pattern_analysis.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(full_analysis, f, ensure_ascii=False, indent=2)

    print(f"\n\n{'='*80}")
    print(f"  Analysis saved to: {output_path}")
    print("=" * 80)

    # Generate markdown documentation
    generate_documentation(full_analysis)

    return full_analysis


def generate_documentation(analysis: dict):
    """Generate markdown documentation of patterns."""
    doc_path = Path("data/analysis/NAS_PATTERN_DOCUMENTATION.md")

    lines = [
        "# NAS Archive Pattern Documentation",
        "",
        "## Overview",
        "",
        f"Archive Path: `Z:/archive`",
        "",
        "| Category | Files | Size |",
        "|----------|-------|------|",
    ]

    total_files = 0
    total_size = 0

    for cat, data in sorted(analysis.items()):
        total_files += data["file_count"]
        total_size += data["total_size_gb"]
        lines.append(f"| {cat} | {data['file_count']} | {data['total_size_gb']:.1f} GB |")

    lines.append(f"| **Total** | **{total_files}** | **{total_size:.1f} GB** |")
    lines.append("")

    # Category details
    for cat, data in sorted(analysis.items()):
        lines.append(f"---")
        lines.append(f"")
        lines.append(f"## {cat}")
        lines.append(f"")
        lines.append(f"- Files: {data['file_count']}")
        lines.append(f"- Size: {data['total_size_gb']:.1f} GB")
        lines.append(f"")

        lines.append("### Folder Structure")
        lines.append("```")
        for folder in data["unique_folders"][:20]:
            lines.append(folder)
        if len(data["unique_folders"]) > 20:
            lines.append(f"... and {len(data['unique_folders']) - 20} more")
        lines.append("```")
        lines.append("")

        lines.append("### Filename Patterns")
        lines.append("")
        lines.append("| Pattern | Count | Description |")
        lines.append("|---------|-------|-------------|")

        pattern_descriptions = {
            "WSOP": "WSOP 관련 파일",
            "WS{YY}": "WS + 2자리 연도",
            "ME": "Main Event",
            "GM": "Grudge Match",
            "HU": "Heads Up",
            "BR": "Bracelet Event",
            "APAC": "Asia Pacific",
            "EU": "Europe",
            "PARADISE": "Paradise (Bahamas)",
            "GOG": "Game of Gold",
            "HCL": "Hustler Casino Live",
            "MPP": "Merit Poker Premier",
            "PAD": "PokerStars and Drama",
            "EPISODE": "에피소드 번호 포함",
            "UNKNOWN": "패턴 미매칭",
        }

        for pattern, count in sorted(data["filename_patterns"].items(), key=lambda x: -x[1]):
            parts = pattern.split("+") if pattern else ["UNKNOWN"]
            desc = ", ".join(pattern_descriptions.get(p, p) for p in parts)
            lines.append(f"| `{pattern}` | {count} | {desc} |")

        lines.append("")
        lines.append("### Sample Files")
        lines.append("```")
        for filename in data.get("pattern_samples", {}).get(list(data["filename_patterns"].keys())[0] if data["filename_patterns"] else "UNKNOWN", data["sample_files"])[:10]:
            lines.append(filename)
        lines.append("```")
        lines.append("")

    with open(doc_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"  Documentation saved to: {doc_path}")


if __name__ == "__main__":
    main()

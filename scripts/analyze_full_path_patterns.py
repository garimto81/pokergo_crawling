"""Analyze Archive using full path (folder hierarchy + filename) as pattern."""
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


def extract_metadata_from_path(full_path: str) -> dict:
    """Extract metadata from full path (folder hierarchy + filename)."""
    metadata = {
        "year": None,
        "region": None,
        "event_type": None,
        "event_num": None,
        "episode": None,
        "stage": None,
        "category": None,
        "sub_category": None,
        "pattern_id": None,
        "confidence": 0.0,
    }

    path_upper = full_path.upper()
    path_normalized = full_path.replace("\\", "/")
    parts = path_normalized.split("/")

    # Category (top-level folder)
    if parts:
        metadata["category"] = parts[0]

    # ========== YEAR EXTRACTION ==========
    # Priority 1: 4-digit year in folder name
    for part in parts:
        year_match = re.search(r'(?:^|[^\d])(\d{4})(?:[^\d]|$)', part)
        if year_match:
            year = int(year_match.group(1))
            if 1970 <= year <= 2030:
                metadata["year"] = year
                break

    # Priority 2: 2-digit year patterns (WS11, WSOP13, etc.)
    if not metadata["year"]:
        yy_match = re.search(r'(?:WS|WSOP|WSOPE|WSE)(\d{2})[_\-]', path_upper)
        if yy_match:
            yy = int(yy_match.group(1))
            metadata["year"] = 2000 + yy if yy < 50 else 1900 + yy

    # Priority 3: Date format YYYYMMDD or YYMMDD
    if not metadata["year"]:
        date_match = re.search(r'(?:^|[_\-])(\d{2})(\d{2})(\d{2})(?:[_\-]|$)', full_path)
        if date_match:
            yy = int(date_match.group(1))
            metadata["year"] = 2000 + yy if yy < 50 else 1900 + yy

    # ========== REGION EXTRACTION ==========
    if 'APAC' in path_upper:
        metadata["region"] = "APAC"
    elif 'EUROPE' in path_upper or 'WSOPE' in path_upper or '-EU' in path_upper or '_EU' in path_upper:
        metadata["region"] = "EU"
    elif 'PARADISE' in path_upper:
        metadata["region"] = "PARADISE"
    elif 'LAS VEGAS' in path_upper or 'LAS_VEGAS' in path_upper:
        metadata["region"] = "LV"
    elif 'CIRCUIT' in path_upper and 'LA' in path_upper:
        metadata["region"] = "LA"
    elif 'CYPRUS' in path_upper:
        metadata["region"] = "CYPRUS"
    elif 'LONDON' in path_upper:
        metadata["region"] = "LONDON"

    # ========== EVENT TYPE EXTRACTION ==========
    # Check folder names for event type
    for part in parts:
        part_upper = part.upper()
        if 'MAIN EVENT' in part_upper or 'MAIN_EVENT' in part_upper:
            metadata["event_type"] = "ME"
            break
        elif 'BRACELET' in part_upper:
            metadata["event_type"] = "BR"
        elif 'HIGH ROLLER' in part_upper or 'HIGH_ROLLER' in part_upper:
            metadata["event_type"] = "HR"
        elif 'HEADS UP' in part_upper or 'HEADS-UP' in part_upper:
            metadata["event_type"] = "HU"

    # Check filename for event type codes
    filename = parts[-1] if parts else ""
    filename_upper = filename.upper()

    if not metadata["event_type"]:
        if re.search(r'[_\-]ME[_\-\d]|_ME\d|ME\d{2}[_\-]', filename_upper):
            metadata["event_type"] = "ME"
        elif re.search(r'[_\-]GM[_\-\d]', filename_upper):
            metadata["event_type"] = "GM"
        elif re.search(r'[_\-]HU[_\-\d]', filename_upper):
            metadata["event_type"] = "HU"
        elif re.search(r'[_\-]BR[_\-\d]', filename_upper):
            metadata["event_type"] = "BR"
        elif re.search(r'[_\-]HR[_\-\d]', filename_upper):
            metadata["event_type"] = "HR"
        elif re.search(r'[_\-]PPC[_\-\d]', filename_upper):
            metadata["event_type"] = "PPC"

    # ========== EVENT NUMBER EXTRACTION ==========
    # Event #13, Event#27, etc.
    event_num_match = re.search(r'Event\s*#?(\d+)', full_path, re.I)
    if event_num_match:
        metadata["event_num"] = int(event_num_match.group(1))

    # ========== EPISODE EXTRACTION ==========
    # Various episode patterns
    ep_patterns = [
        r'[_\-](\d{2})[_\.\-]',  # _01_, -02.
        r'EP?(\d{1,2})',          # EP01, E02
        r'Episode[_\s]?(\d+)',    # Episode_1
        r'Show[_\s]?(\d+)',       # Show_1
        r'Part[_\s]?(\d+)',       # Part 1
    ]
    for pattern in ep_patterns:
        ep_match = re.search(pattern, filename, re.I)
        if ep_match:
            metadata["episode"] = int(ep_match.group(1))
            break

    # ========== STAGE EXTRACTION ==========
    stage_patterns = [
        (r'Final\s*Table', 'FT'),
        (r'Final\s*Day', 'FINAL'),
        (r'Day\s*(\d+)\s*([ABCD])?', 'DAY'),
        (r'Session\s*(\d+)', 'SESSION'),
    ]
    for pattern, stage_type in stage_patterns:
        stage_match = re.search(pattern, full_path, re.I)
        if stage_match:
            if stage_type == 'DAY':
                day_num = stage_match.group(1)
                flight = stage_match.group(2) or ''
                metadata["stage"] = f"D{day_num}{flight}"
            elif stage_type == 'SESSION':
                metadata["stage"] = f"S{stage_match.group(1)}"
            else:
                metadata["stage"] = stage_type
            break

    # ========== SUB-CATEGORY ==========
    if len(parts) > 1:
        metadata["sub_category"] = parts[1] if parts[1] != parts[0] else None

    # ========== PATTERN IDENTIFICATION ==========
    pattern_id, confidence = identify_pattern(full_path, metadata)
    metadata["pattern_id"] = pattern_id
    metadata["confidence"] = confidence

    return metadata


def identify_pattern(full_path: str, metadata: dict) -> tuple:
    """Identify pattern ID and confidence score."""
    path_upper = full_path.upper()
    parts = full_path.replace("\\", "/").split("/")
    filename = parts[-1] if parts else ""

    # Pattern definitions with folder context
    patterns = [
        # WSOP Patterns (by folder structure)
        ("WSOP_BR_LV_2025_ME", r'WSOP.*Bracelet.*LAS.?VEGAS.*2025.*MAIN.?EVENT', 1.0),
        ("WSOP_BR_LV_2025_SIDE", r'WSOP.*Bracelet.*LAS.?VEGAS.*2025.*BRACELET.?SIDE', 0.95),
        ("WSOP_BR_EU_2025", r'WSOP.*Bracelet.*EUROPE.*2025', 0.95),
        ("WSOP_BR_EU", r'WSOP.*Bracelet.*EUROPE', 0.9),
        ("WSOP_BR_PARADISE", r'WSOP.*Bracelet.*PARADISE', 0.9),
        ("WSOP_BR_LV", r'WSOP.*Bracelet.*LAS.?VEGAS', 0.85),
        ("WSOP_CIRCUIT_LA", r'WSOP.*Circuit.*LA', 0.9),
        ("WSOP_CIRCUIT_SUPER", r'WSOP.*Super.?Circuit', 0.9),
        ("WSOP_ARCHIVE_PRE2016", r'WSOP.*ARCHIVE.*PRE-?2016', 0.85),

        # By filename pattern
        ("WSOP_CLIP_POKERGO", r'\d+-wsop-\d{4}-(be|me)-', 0.95),
        ("WSOP_WS_SHORT", r'WS\d{2}[_\-][A-Z]{2}\d{2}', 0.9),
        ("WSOP_WSOP_SHORT", r'WSOP\d{2}[_\-]', 0.9),
        ("WSOP_WSOPE_EP", r'WSOPE\d{2}[_\-]Episode', 0.9),
        ("WSOP_WSE", r'WSE\d{2}[_\-]', 0.9),
        ("WSOP_EVENT_NUM", r'\d{4}\s*WSOP\s*Event\s*#\d+', 0.95),
        ("WSOP_BRACELET_EVENT", r'WSOP.*Bracelet.*Event', 0.85),
        ("WSOP_HISTORIC", r'wsop-\d{4}-me|WSOP\s*-\s*\d{4}', 0.8),
        ("WSOP_ESPN", r'ESPN.*WSOP|WSOP.*Show.*\d+', 0.8),
        ("WSOP_MXF_ARCHIVE", r'WSOP[_\-]\d{4}.*\.mxf', 0.85),
        ("WSOP_2016_ME", r'2016.*World.*Series.*Main.*Event', 0.9),

        # PAD (두 가지 형식: pad-s12-ep01 또는 PAD_S13_EP01)
        ("PAD", r'PAD.*(pad-s\d{2}-ep\d{2}|PAD_S\d{2}_EP\d{2})', 1.0),

        # GOG
        ("GOG", r'GOG.*E\d{2}[_\-]GOG', 1.0),

        # MPP
        ("MPP_ME", r'MPP.*Main.?Event', 0.95),
        ("MPP", r'MPP.*\$\d+[MK]?\s*GTD', 0.9),

        # GGMillions
        ("GGMILLIONS", r'GGMillions.*Super.*High.*Roller', 0.9),

        # HCL
        ("HCL", r'^HCL', 0.8),
    ]

    for pattern_id, regex, base_confidence in patterns:
        if re.search(regex, full_path, re.I):
            # Boost confidence if metadata is complete
            confidence = base_confidence
            if metadata["year"]:
                confidence = min(1.0, confidence + 0.05)
            if metadata["event_type"]:
                confidence = min(1.0, confidence + 0.05)
            if metadata["region"]:
                confidence = min(1.0, confidence + 0.03)
            return pattern_id, confidence

    # Fallback patterns based on metadata
    if metadata["category"] == "WSOP":
        if metadata["year"] and metadata["event_type"]:
            return "WSOP_GENERIC", 0.6
        elif metadata["year"]:
            return "WSOP_YEAR_ONLY", 0.5
        return "WSOP_UNKNOWN", 0.3

    return "UNKNOWN", 0.0


def scan_archive(archive_path: Path) -> list:
    """Scan archive and collect all video files with full paths."""
    files = []

    if not archive_path.exists():
        print(f"[ERROR] Archive path not found: {archive_path}")
        return files

    for item in archive_path.rglob("*"):
        if item.is_file() and item.suffix.lower() in VIDEO_EXTENSIONS:
            rel_path = str(item.relative_to(archive_path))
            files.append({
                "full_path": rel_path,
                "filename": item.name,
                "extension": item.suffix.lower(),
                "size_mb": item.stat().st_size / (1024 * 1024),
            })

    return files


def analyze_files(files: list) -> dict:
    """Analyze all files and extract patterns."""
    results = {
        "total_files": len(files),
        "patterns": defaultdict(list),
        "by_year": defaultdict(list),
        "by_region": defaultdict(list),
        "by_event_type": defaultdict(list),
        "by_category": defaultdict(list),
        "metadata_coverage": {
            "year": 0,
            "region": 0,
            "event_type": 0,
            "episode": 0,
            "stage": 0,
        },
        "confidence_distribution": defaultdict(int),
        "detailed_files": [],
    }

    for file_info in files:
        full_path = file_info["full_path"]
        metadata = extract_metadata_from_path(full_path)

        # Store detailed info
        detailed = {
            **file_info,
            **metadata,
        }
        results["detailed_files"].append(detailed)

        # Aggregate by pattern
        pattern_id = metadata["pattern_id"]
        results["patterns"][pattern_id].append(full_path)

        # Aggregate by metadata
        if metadata["year"]:
            results["by_year"][metadata["year"]].append(full_path)
            results["metadata_coverage"]["year"] += 1

        if metadata["region"]:
            results["by_region"][metadata["region"]].append(full_path)
            results["metadata_coverage"]["region"] += 1

        if metadata["event_type"]:
            results["by_event_type"][metadata["event_type"]].append(full_path)
            results["metadata_coverage"]["event_type"] += 1

        if metadata["episode"]:
            results["metadata_coverage"]["episode"] += 1

        if metadata["stage"]:
            results["metadata_coverage"]["stage"] += 1

        if metadata["category"]:
            results["by_category"][metadata["category"]].append(full_path)

        # Confidence distribution
        conf_bucket = int(metadata["confidence"] * 10) * 10
        results["confidence_distribution"][conf_bucket] += 1

    return results


def print_analysis(results: dict):
    """Print analysis results."""
    print("\n" + "=" * 80)
    print("  FULL PATH PATTERN ANALYSIS")
    print("=" * 80)

    total = results["total_files"]

    # Pattern summary
    print(f"\n[PATTERNS] (Total: {total} files)")
    print("-" * 60)

    pattern_counts = {k: len(v) for k, v in results["patterns"].items()}
    for pattern, count in sorted(pattern_counts.items(), key=lambda x: -x[1]):
        pct = count / total * 100
        bar = "█" * int(pct / 2)
        print(f"  {pattern:30s} {count:5d} ({pct:5.1f}%) {bar}")

    # Metadata coverage
    print(f"\n[METADATA COVERAGE]")
    print("-" * 60)
    for field, count in results["metadata_coverage"].items():
        pct = count / total * 100
        print(f"  {field:15s}: {count:5d} / {total} ({pct:5.1f}%)")

    # By year
    print(f"\n[BY YEAR]")
    print("-" * 60)
    for year in sorted(results["by_year"].keys()):
        count = len(results["by_year"][year])
        print(f"  {year}: {count}")

    # By region
    print(f"\n[BY REGION]")
    print("-" * 60)
    for region, paths in sorted(results["by_region"].items(), key=lambda x: -len(x[1])):
        print(f"  {region:15s}: {len(paths)}")

    # By event type
    print(f"\n[BY EVENT TYPE]")
    print("-" * 60)
    for etype, paths in sorted(results["by_event_type"].items(), key=lambda x: -len(x[1])):
        print(f"  {etype:15s}: {len(paths)}")

    # Confidence distribution
    print(f"\n[CONFIDENCE DISTRIBUTION]")
    print("-" * 60)
    for bucket in sorted(results["confidence_distribution"].keys()):
        count = results["confidence_distribution"][bucket]
        pct = count / total * 100
        label = f"{bucket}-{bucket+9}%"
        bar = "█" * int(pct / 2)
        print(f"  {label:10s}: {count:5d} ({pct:5.1f}%) {bar}")

    # Sample files by pattern
    print(f"\n[SAMPLE FILES BY PATTERN]")
    print("-" * 60)
    for pattern in sorted(results["patterns"].keys()):
        paths = results["patterns"][pattern]
        print(f"\n  {pattern} ({len(paths)} files):")
        for path in paths[:3]:
            print(f"    - {path}")


def save_results(results: dict):
    """Save results to JSON and Markdown."""
    output_dir = Path("data/analysis")
    output_dir.mkdir(parents=True, exist_ok=True)

    # JSON output
    json_output = {
        "total_files": results["total_files"],
        "patterns": {k: {"count": len(v), "samples": v[:10]} for k, v in results["patterns"].items()},
        "by_year": {str(k): len(v) for k, v in results["by_year"].items()},
        "by_region": {k: len(v) for k, v in results["by_region"].items()},
        "by_event_type": {k: len(v) for k, v in results["by_event_type"].items()},
        "by_category": {k: len(v) for k, v in results["by_category"].items()},
        "metadata_coverage": results["metadata_coverage"],
        "confidence_distribution": dict(results["confidence_distribution"]),
    }

    with open(output_dir / "full_path_analysis.json", "w", encoding="utf-8") as f:
        json.dump(json_output, f, ensure_ascii=False, indent=2)

    # Detailed CSV-like JSON for NAMS import
    detailed_output = []
    for item in results["detailed_files"]:
        detailed_output.append({
            "full_path": item["full_path"],
            "filename": item["filename"],
            "year": item["year"],
            "region": item["region"],
            "event_type": item["event_type"],
            "event_num": item["event_num"],
            "episode": item["episode"],
            "stage": item["stage"],
            "pattern_id": item["pattern_id"],
            "confidence": item["confidence"],
        })

    with open(output_dir / "full_path_detailed.json", "w", encoding="utf-8") as f:
        json.dump(detailed_output, f, ensure_ascii=False, indent=2)

    # Markdown summary
    generate_markdown_summary(results, output_dir / "FULL_PATH_PATTERN_RULES.md")

    print(f"\n[OUTPUT]")
    print(f"  - {output_dir / 'full_path_analysis.json'}")
    print(f"  - {output_dir / 'full_path_detailed.json'}")
    print(f"  - {output_dir / 'FULL_PATH_PATTERN_RULES.md'}")


def generate_markdown_summary(results: dict, output_path: Path):
    """Generate Markdown summary of patterns."""
    total = results["total_files"]

    lines = [
        "# Archive Full Path Pattern Analysis",
        "",
        f"> 분석 일자: {__import__('datetime').datetime.now().strftime('%Y-%m-%d')}",
        f"> 총 파일: {total}",
        "",
        "## 1. 패턴 분류 결과",
        "",
        "| Pattern ID | Count | % | Description |",
        "|------------|-------|---|-------------|",
    ]

    pattern_descriptions = {
        "WSOP_BR_LV_2025_ME": "2025 WSOP Las Vegas Main Event",
        "WSOP_BR_LV_2025_SIDE": "2025 WSOP Las Vegas Side Events",
        "WSOP_BR_EU_2025": "2025 WSOP Europe",
        "WSOP_BR_EU": "WSOP Europe (All Years)",
        "WSOP_BR_PARADISE": "WSOP Paradise (Bahamas)",
        "WSOP_BR_LV": "WSOP Las Vegas Bracelet",
        "WSOP_CIRCUIT_LA": "WSOP Circuit Los Angeles",
        "WSOP_CIRCUIT_SUPER": "WSOP Super Circuit",
        "WSOP_ARCHIVE_PRE2016": "WSOP Archive (Pre-2016)",
        "WSOP_CLIP_POKERGO": "PokerGO Clip Format",
        "WSOP_WS_SHORT": "WS{YY} Short Format",
        "WSOP_WSOP_SHORT": "WSOP{YY} Short Format",
        "WSOP_WSOPE_EP": "WSOP Europe Episode",
        "WSOP_WSE": "WSE Short Format",
        "WSOP_EVENT_NUM": "WSOP Event # Format",
        "WSOP_BRACELET_EVENT": "WSOP Bracelet Event",
        "WSOP_HISTORIC": "Historic WSOP (1973-2001)",
        "WSOP_ESPN": "ESPN Broadcast Format",
        "WSOP_MXF_ARCHIVE": "MXF Archive Format",
        "WSOP_2016_ME": "2016 Main Event",
        "WSOP_GENERIC": "WSOP Generic (Year+Type)",
        "WSOP_YEAR_ONLY": "WSOP Year Only",
        "WSOP_UNKNOWN": "WSOP Unclassified",
        "PAD": "Poker After Dark",
        "GOG": "Game of Gold",
        "MPP_ME": "MPP Main Event",
        "MPP": "Merit Poker Premier",
        "GGMILLIONS": "GGMillions High Roller",
        "HCL": "Hustler Casino Live",
        "UNKNOWN": "Unclassified",
    }

    pattern_counts = {k: len(v) for k, v in results["patterns"].items()}
    for pattern, count in sorted(pattern_counts.items(), key=lambda x: -x[1]):
        pct = count / total * 100
        desc = pattern_descriptions.get(pattern, "")
        lines.append(f"| `{pattern}` | {count} | {pct:.1f}% | {desc} |")

    lines.extend([
        "",
        "## 2. 메타데이터 추출률",
        "",
        "| Field | Extracted | Rate |",
        "|-------|-----------|------|",
    ])

    for field, count in results["metadata_coverage"].items():
        pct = count / total * 100
        lines.append(f"| {field} | {count} | {pct:.1f}% |")

    lines.extend([
        "",
        "## 3. 연도별 분포",
        "",
        "| Year | Count |",
        "|------|-------|",
    ])

    for year in sorted(results["by_year"].keys()):
        count = len(results["by_year"][year])
        lines.append(f"| {year} | {count} |")

    lines.extend([
        "",
        "## 4. 지역별 분포",
        "",
        "| Region | Count | Description |",
        "|--------|-------|-------------|",
    ])

    region_names = {
        "LV": "Las Vegas",
        "EU": "Europe",
        "APAC": "Asia Pacific",
        "PARADISE": "Bahamas",
        "LA": "Los Angeles",
        "CYPRUS": "Cyprus",
        "LONDON": "London",
    }

    for region, paths in sorted(results["by_region"].items(), key=lambda x: -len(x[1])):
        name = region_names.get(region, region)
        lines.append(f"| {region} | {len(paths)} | {name} |")

    lines.extend([
        "",
        "## 5. 이벤트 타입별 분포",
        "",
        "| Type | Count | Description |",
        "|------|-------|-------------|",
    ])

    type_names = {
        "ME": "Main Event",
        "BR": "Bracelet Event",
        "HR": "High Roller",
        "HU": "Heads Up",
        "GM": "Grudge Match",
        "PPC": "Poker Players Championship",
    }

    for etype, paths in sorted(results["by_event_type"].items(), key=lambda x: -len(x[1])):
        name = type_names.get(etype, etype)
        lines.append(f"| {etype} | {len(paths)} | {name} |")

    lines.extend([
        "",
        "## 6. 패턴별 샘플",
        "",
    ])

    for pattern in sorted(results["patterns"].keys()):
        paths = results["patterns"][pattern]
        lines.append(f"### {pattern} ({len(paths)} files)")
        lines.append("```")
        for path in paths[:5]:
            lines.append(path)
        if len(paths) > 5:
            lines.append(f"... and {len(paths) - 5} more")
        lines.append("```")
        lines.append("")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def main():
    print("=" * 80)
    print("  Archive Full Path Pattern Analysis")
    print("=" * 80)

    print(f"\n[Scanning] {ARCHIVE_PATH}")
    files = scan_archive(ARCHIVE_PATH)
    print(f"[Found] {len(files)} video files")

    print(f"\n[Analyzing patterns...]")
    results = analyze_files(files)

    print_analysis(results)
    save_results(results)

    print("\n" + "=" * 80)
    print("  Analysis Complete")
    print("=" * 80)


if __name__ == "__main__":
    main()

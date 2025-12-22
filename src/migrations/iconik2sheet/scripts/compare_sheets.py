"""Compare Iconik_Full_Metadata with GGmetadata_and_timestamps."""

import sys
from pathlib import Path

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sheets import SheetsWriter


def normalize_value(val: str | None) -> str:
    """Normalize value for comparison."""
    if val is None:
        return ""
    return str(val).strip().lower()


def compare_sheets() -> None:
    """Compare Iconik_Full_Metadata with GGmetadata_and_timestamps by title."""
    print("=" * 70)
    print("Comparing Iconik_Full_Metadata vs GGmetadata_and_timestamps")
    print("=" * 70)
    print()

    writer = SheetsWriter()

    # Read both sheets
    print("Reading Iconik_Full_Metadata...")
    iconik_headers, iconik_data = writer.get_sheet_data("Iconik_Full_Metadata")
    print(f"  Found {len(iconik_data)} rows")

    print("Reading GGmetadata_and_timestamps...")
    gg_headers, gg_data = writer.get_sheet_data("GGmetadata_and_timestamps")
    print(f"  Found {len(gg_data)} rows")
    print()

    if not iconik_data:
        print("ERROR: Iconik_Full_Metadata is empty!")
        return

    if not gg_data:
        print("ERROR: GGmetadata_and_timestamps is empty!")
        return

    # Build title -> row map for GG sheet
    gg_by_title = {}
    for row in gg_data:
        title = row.get("title", "").strip()
        if title:
            gg_by_title[title] = row

    # Compare fields to check
    compare_fields = [
        "time_start_ms", "time_end_ms",
        "Description", "ProjectName", "Year_", "Location", "Venue",
        "EpisodeEvent", "Source", "Scene", "GameType", "PlayersTags",
        "HandGrade", "HANDTag", "EPICHAND", "Tournament", "PokerPlayTags",
    ]

    # Stats
    matched = 0
    not_found_in_gg = 0
    field_matches = {f: 0 for f in compare_fields}
    field_mismatches = {f: [] for f in compare_fields}
    field_both_empty = {f: 0 for f in compare_fields}

    print("-" * 70)
    print("COMPARISON RESULTS")
    print("-" * 70)

    for iconik_row in iconik_data:
        title = iconik_row.get("title", "").strip()

        if title not in gg_by_title:
            not_found_in_gg += 1
            print(f"\n[NOT FOUND in GG] {title[:60]}")
            continue

        matched += 1
        gg_row = gg_by_title[title]

        print(f"\n[MATCHED] {title[:60]}")

        for field in compare_fields:
            iconik_val = normalize_value(iconik_row.get(field))
            gg_val = normalize_value(gg_row.get(field))

            if iconik_val == gg_val:
                if iconik_val:
                    field_matches[field] += 1
                    status = "OK"
                else:
                    field_both_empty[field] += 1
                    status = "EMPTY"
            else:
                field_mismatches[field].append({
                    "title": title,
                    "iconik": iconik_row.get(field, ""),
                    "gg": gg_row.get(field, ""),
                })
                status = "DIFF"

            # Show differences
            if status == "DIFF":
                print(f"  {field}:")
                print(f"    Iconik: {iconik_row.get(field, '')[:50]}")
                print(f"    GG:     {gg_row.get(field, '')[:50]}")

    # Summary
    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"\nTotal Iconik rows: {len(iconik_data)}")
    print(f"Matched by title:  {matched}")
    print(f"Not found in GG:   {not_found_in_gg}")

    print("\n[Field Comparison]")
    print(f"{'Field':<20} {'Match':<8} {'Diff':<8} {'Empty':<8} {'Match %':<10}")
    print("-" * 54)

    for field in compare_fields:
        match_count = field_matches[field]
        diff_count = len(field_mismatches[field])
        empty_count = field_both_empty[field]
        total = match_count + diff_count
        match_pct = (match_count / total * 100) if total > 0 else 0

        print(f"{field:<20} {match_count:<8} {diff_count:<8} {empty_count:<8} {match_pct:>6.1f}%")

    # Show mismatch samples
    print("\n[Mismatch Samples]")
    for field in compare_fields:
        if field_mismatches[field]:
            print(f"\n  {field} ({len(field_mismatches[field])} mismatches):")
            for sample in field_mismatches[field][:2]:
                print(f"    Title: {sample['title'][:40]}")
                print(f"      Iconik: {sample['iconik'][:50]}")
                print(f"      GG:     {sample['gg'][:50]}")


if __name__ == "__main__":
    compare_sheets()

#!/usr/bin/env python
"""Test the new pattern engine with sample paths."""

import sys
from pathlib import Path

# Fix Windows console encoding
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.nams.api.services.pattern_engine import (
    extract_year_from_path,
    extract_stage_from_path,
    extract_event_num_from_path,
    extract_buyin_from_path,
    extract_gtd_from_path,
    extract_version_from_path,
    extract_episode_from_path,
    extract_season_from_path,
    extract_region_from_super_circuit,
    detect_event_type_from_path,
)

# Test cases based on PATTERN_EXTRACTION_RULES.md
TEST_CASES = [
    # WSOP_BR_LV_2025_ME
    {
        "path": "Z:/archive/WSOP/WSOP Bracelet Event/WSOP-LAS VEGAS/2025 WSOP-LAS VEGAS/WSOP 2025 MAIN EVENT/WSOP 2025 Main Event _ Day 1A/WSOP 2025 Main Event _ Day 1A.mp4",
        "expected": {
            "year": 2025,
            "stage": "D1A",
            "event_type": "ME",
        }
    },
    {
        "path": "Z:/archive/WSOP/WSOP Bracelet Event/WSOP-LAS VEGAS/2025 WSOP-LAS VEGAS/WSOP 2025 MAIN EVENT/WSOP 2025 Main Event _ Final Table/WSOP 2025 Main Event _ Final Table Day 1.mp4",
        "expected": {
            "year": 2025,
            "stage": "FT-D1",
            "event_type": "ME",
        }
    },
    # WSOP_BR_LV_2025_SIDE
    {
        "path": "Z:/archive/WSOP/WSOP Bracelet Event/WSOP-LAS VEGAS/2025 WSOP-LAS VEGAS/WSOP 2025 BRACELET SIDE EVENT/WSOP 2025 Bracelet Events  Event #13 $1.5K No-Limit Hold'em 6-Max/(PokerGO) WSOP 2025 Bracelet Events _ Event #13 $1.5K No-Limit Hold'em 6-Max.mp4",
        "expected": {
            "year": 2025,
            "event_num": 13,
            "buyin": "1.5K",
            "event_type": "BR",
        }
    },
    # WSOP_BR_EU_2025
    {
        "path": "Z:/archive/WSOP/WSOP Bracelet Event/WSOP-EUROPE/2025 WSOP-Europe/2025 WSOP-EUROPE #14 MAIN EVENT/NO COMMENTARY WITH GRAPHICS VER/Day 1 A/file.mp4",
        "expected": {
            "year": 2025,
            "event_num": 14,
            "stage": "D1A",
            "version": "NC",
            "event_type": "ME",
        }
    },
    # WSOP_BR_EU (old format)
    {
        "path": "Z:/archive/WSOP/WSOP Bracelet Event/WSOP-EUROPE/2008 WSOP-Europe/WSOPE08_Episode_1_H264.mov",
        "expected": {
            "year": 2008,
            "episode": 1,
        }
    },
    # WSOP_BR_PARADISE
    {
        "path": "Z:/archive/WSOP/WSOP Bracelet Event/WSOP-PARADISE/2024 WSOP-PARADISE SUPER MAIN EVENT/2024 WSOP Paradise Super Main Event - Day 1B.mp4",
        "expected": {
            "year": 2024,
            "stage": "D1B",
            "event_type": "ME",
        }
    },
    # WSOP_CIRCUIT_LA
    {
        "path": "Z:/archive/WSOP/WSOP Circuit Event/WSOP-Circuit/2024 WSOP Circuit LA/2024 WSOP-C LA STREAM/2024 WSOP Circuit Los Angeles - Main Event [Day 1A].mp4",
        "expected": {
            "year": 2024,
            "stage": "D1A",
            "event_type": "ME",
        }
    },
    # WSOP_CIRCUIT_SUPER - Cyprus
    {
        "path": "Z:/archive/WSOP/WSOP Circuit Event/WSOP Super Ciruit/2025 WSOP Super Circuit Cyprus/$5M GTD   WSOP Super Circuit Cyprus Main Event - Day 1A-006.mp4",
        "expected": {
            "year": 2025,
            "region": "CYPRUS",
            "gtd": "5M",
            "stage": "D1A",
            "event_type": "ME",
        }
    },
    # WSOP_ARCHIVE_PRE2016
    {
        "path": "Z:/archive/WSOP/WSOP ARCHIVE (PRE-2016)/WSOP 2004/MOVs/2004 WSOP Show 1 2k NLTH_ESM000100722.mov",
        "expected": {
            "year": 2004,
            "episode": 1,
        }
    },
    # PAD
    {
        "path": "Z:/archive/PAD/PAD S12/pad-s12-ep01-002.mp4",
        "expected": {
            "season": 12,
            "episode": 1,
        }
    },
    {
        "path": "Z:/archive/PAD/PAD S13/PAD_S13_EP01_GGPoker-001.mp4",
        "expected": {
            "season": 13,
            "episode": 1,
        }
    },
    # GOG
    {
        "path": "Z:/archive/GOG 최종/e01/E01_GOG_final_edit_231106.mp4",
        "expected": {
            "episode": 1,
        }
    },
    # MPP
    {
        "path": "Z:/archive/MPP/2025 MPP Cyprus/$5M GTD   $5K MPP Main Event/$5M GTD   $5K MPP Main Event – Day 2.mp4",
        "expected": {
            "year": 2025,
            "gtd": "5M",
            "buyin": "5M",  # First $ match
            "stage": "D2",
            "event_type": "ME",
        }
    },
    # GGMILLIONS
    {
        "path": "Z:/archive/GGMillions/250507_Super High Roller Poker FINAL TABLE with Joey ingram.mp4",
        "expected": {
            "stage": "FT",
            "event_type": "HR",
        }
    },
]


def test_extraction_functions():
    """Test individual extraction functions."""
    print("=" * 60)
    print("Testing Pattern Engine Extraction Functions")
    print("=" * 60)

    passed = 0
    failed = 0

    for i, tc in enumerate(TEST_CASES, 1):
        path = tc["path"]
        expected = tc["expected"]

        print(f"\n[Test {i}] {Path(path).name[:50]}...")

        results = {}
        errors = []

        # Test year extraction
        if "year" in expected:
            actual = extract_year_from_path(path)
            results["year"] = actual
            if actual != expected["year"]:
                errors.append(f"year: expected {expected['year']}, got {actual}")

        # Test stage extraction
        if "stage" in expected:
            actual = extract_stage_from_path(path)
            results["stage"] = actual
            if actual != expected["stage"]:
                errors.append(f"stage: expected {expected['stage']}, got {actual}")

        # Test event_num extraction
        if "event_num" in expected:
            actual = extract_event_num_from_path(path)
            results["event_num"] = actual
            if actual != expected["event_num"]:
                errors.append(f"event_num: expected {expected['event_num']}, got {actual}")

        # Test buyin extraction
        if "buyin" in expected:
            actual = extract_buyin_from_path(path)
            results["buyin"] = actual
            if actual != expected["buyin"]:
                errors.append(f"buyin: expected {expected['buyin']}, got {actual}")

        # Test gtd extraction
        if "gtd" in expected:
            actual = extract_gtd_from_path(path)
            results["gtd"] = actual
            if actual != expected["gtd"]:
                errors.append(f"gtd: expected {expected['gtd']}, got {actual}")

        # Test version extraction
        if "version" in expected:
            actual = extract_version_from_path(path)
            results["version"] = actual
            if actual != expected["version"]:
                errors.append(f"version: expected {expected['version']}, got {actual}")

        # Test event_type detection
        if "event_type" in expected:
            actual = detect_event_type_from_path(path)
            results["event_type"] = actual
            if actual != expected["event_type"]:
                errors.append(f"event_type: expected {expected['event_type']}, got {actual}")

        # Test season extraction
        if "season" in expected:
            actual = extract_season_from_path(path)
            results["season"] = actual
            if actual != expected["season"]:
                errors.append(f"season: expected {expected['season']}, got {actual}")

        # Test episode extraction
        if "episode" in expected:
            # Determine pattern name from path
            pattern_name = "UNKNOWN"
            if "PAD" in path:
                pattern_name = "PAD"
            elif "GOG" in path:
                pattern_name = "GOG"
            elif "ARCHIVE" in path:
                pattern_name = "WSOP_ARCHIVE_PRE2016"
            elif "Circuit" in path and "LA" in path:
                pattern_name = "WSOP_CIRCUIT_LA"
            elif "EUROPE" in path:
                pattern_name = "WSOP_BR_EU"

            actual = extract_episode_from_path(path, pattern_name)
            results["episode"] = actual
            if actual != expected["episode"]:
                errors.append(f"episode: expected {expected['episode']}, got {actual}")

        # Test region extraction for Super Circuit
        if "region" in expected:
            actual = extract_region_from_super_circuit(path)
            results["region"] = actual
            if actual != expected["region"]:
                errors.append(f"region: expected {expected['region']}, got {actual}")

        if errors:
            print(f"  FAILED:")
            for err in errors:
                print(f"    - {err}")
            print(f"  Results: {results}")
            failed += 1
        else:
            print(f"  PASSED: {results}")
            passed += 1

    print("\n" + "=" * 60)
    print(f"Results: {passed}/{passed + failed} passed")
    print("=" * 60)

    return failed == 0


def main():
    success = test_extraction_functions()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

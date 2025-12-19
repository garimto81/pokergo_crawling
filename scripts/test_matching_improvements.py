"""Test matching improvements for P02, P03, P04, M01, D01 fixes."""
import sys
import io
from pathlib import Path

# UTF-8 output
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.nams.api.services.pattern_engine import (
    extract_year_from_path,
    detect_event_type_from_path,
    extract_episode_from_path,
)
from src.nams.api.services.catalog_service import (
    generate_title_from_filename,
)
from src.nams.api.services.matching import normalize_title


def test_p02_year_extraction():
    """Test P02 fix: Year extraction patterns."""
    print("\n=== P02: Year Extraction Tests ===")

    test_cases = [
        # (filename, expected_year)
        ("WSOP_1983.mov", 1983),
        ("WSOP_1983.mxf", 1983),
        ("WSOP_1987.mxf", 1987),
        ("WSOP - 1973.mp4", 1973),
        ("wsop-1973-me-nobug.mp4", 1973),
        ("wsop-1978-me-nobug.mp4", 1978),
        ("wsope-2021-10k-me-ft-004.mp4", 2021),
        ("WSOPE08_Episode_1_H264.mov", 2008),
        ("WS11_ME25_NB.mp4", 2011),
        ("WSOP13_ME01_NB.mp4", 2013),
    ]

    passed = 0
    failed = 0

    for filename, expected in test_cases:
        result = extract_year_from_path(filename)
        status = "✓" if result == expected else "✗"
        if result == expected:
            passed += 1
        else:
            failed += 1
        print(f"  {status} {filename[:50]:<50} → Expected: {expected}, Got: {result}")

    print(f"\n  P02 Results: {passed}/{len(test_cases)} passed")
    return passed == len(test_cases)


def test_p03_event_type():
    """Test P03 fix: Event type detection."""
    print("\n=== P03: Event Type Detection Tests ===")

    test_cases = [
        # (filename, expected_type)
        ("wsop-1973-me-nobug.mp4", "ME"),
        ("WSOP_ME01_NB.mp4", "ME"),
        ("WS11_GM01_NB.mp4", "GM"),
        ("WS11_HU01_NB.mp4", "HU"),
        ("WSOP_HR01.mp4", "HR"),
        ("wsope-2021-10k-me-ft-004.mp4", "FT"),
        ("WSOP 2017 Main Event _ Episode 10.mp4", "ME"),
        ("WSOP_1983.mov", "ME"),  # CLASSIC era = ME
    ]

    passed = 0
    failed = 0

    for filename, expected in test_cases:
        result = detect_event_type_from_path(filename)
        status = "✓" if result == expected else "✗"
        if result == expected:
            passed += 1
        else:
            failed += 1
        print(f"  {status} {filename[:50]:<50} → Expected: {expected}, Got: {result}")

    print(f"\n  P03 Results: {passed}/{len(test_cases)} passed")
    return passed == len(test_cases)


def test_p04_episode():
    """Test P04 fix: Episode extraction."""
    print("\n=== P04: Episode Extraction Tests ===")

    test_cases = [
        # (filename, pattern_name, expected_episode)
        ("wsope-2021-10k-me-ft-004.mp4", None, 4),
        ("wsope-2021-10k-nlh6max-ft-009.mp4", None, 9),
        ("WSOPE08_Episode_1_H264.mov", "WSOP_BR_EU", 1),
        ("WSOPE08_Episode_5_H264.mov", "WSOP_BR_EU", 5),
        ("WSOP 2017 Main Event _ Episode 10.mp4", None, 10),
        ("WS11_ME25_NB.mp4", None, 25),
    ]

    passed = 0
    failed = 0

    for filename, pattern_name, expected in test_cases:
        result = extract_episode_from_path(filename, pattern_name)
        status = "✓" if result == expected else "✗"
        if result == expected:
            passed += 1
        else:
            failed += 1
        print(f"  {status} {filename[:50]:<50} → Expected: {expected}, Got: {result}")

    print(f"\n  P04 Results: {passed}/{len(test_cases)} passed")
    return passed == len(test_cases)


def test_d01_catalog_title():
    """Test D01 fix: Catalog title generation for historic content."""
    print("\n=== D01: Catalog Title Generation Tests ===")

    test_cases = [
        # (filename, expected_title)
        ("WSOPE08_Episode_1_H264.mov", "WSOP Europe 2008 | Episode 1"),
        ("WSOPE08_Episode_5_H264.mov", "WSOP Europe 2008 | Episode 5"),
        ("WSOPE11_Episode_3_H264.mov", "WSOP Europe 2011 | Episode 3"),
        ("wsope-2021-10k-me-ft-004.mp4", "WSOP Europe 2021 €10K ME | Final Table 4"),
        ("WSOP_1983.mov", "WSOP 1983 Main Event"),
        ("wsop-1978-me-nobug.mp4", "WSOP 1978 Main Event"),
    ]

    passed = 0
    failed = 0

    for filename, expected in test_cases:
        result = generate_title_from_filename(filename)
        status = "✓" if result == expected else "✗"
        if result == expected:
            passed += 1
        else:
            failed += 1
        print(f"  {status} {filename[:50]:<50}")
        print(f"      Expected: {expected}")
        print(f"      Got:      {result}")

    print(f"\n  D01 Results: {passed}/{len(test_cases)} passed")
    return passed == len(test_cases)


def test_m01_normalization():
    """Test M01 fix: Title normalization."""
    print("\n=== M01: Title Normalization Tests ===")

    test_cases = [
        # (title1, title2, should_match)
        ("WSOP 2017 Main Event | Episode 10", "WSOP 2017 Main Event _ Episode 10.mp4", True),
        ("Wsop 1978 Main Event", "wsop-1978-me-nobug.mp4", True),
        ("WSOP Europe 2008 Episode 1", "WSOPE08_Episode_1_H264.mov", True),
    ]

    passed = 0
    failed = 0

    for title1, title2, should_match in test_cases:
        norm1 = normalize_title(title1)
        norm2 = normalize_title(title2)

        # Check if normalized versions have significant overlap
        words1 = set(norm1.split())
        words2 = set(norm2.split())
        overlap = len(words1 & words2)
        matches = overlap >= 3  # At least 3 common words

        status = "✓" if matches == should_match else "✗"
        if matches == should_match:
            passed += 1
        else:
            failed += 1
        print(f"  {status} '{title1[:40]}' vs '{title2[:40]}'")
        print(f"      Norm1: {norm1}")
        print(f"      Norm2: {norm2}")
        print(f"      Overlap: {overlap} words, Match: {matches}")

    print(f"\n  M01 Results: {passed}/{len(test_cases)} passed")
    return passed == len(test_cases)


def main():
    """Run all tests."""
    print("=" * 80)
    print("MATCHING IMPROVEMENT TESTS")
    print("=" * 80)

    results = []
    results.append(("P02 (Year Extraction)", test_p02_year_extraction()))
    results.append(("P03 (Event Type)", test_p03_event_type()))
    results.append(("P04 (Episode)", test_p04_episode()))
    results.append(("D01 (Catalog Title)", test_d01_catalog_title()))
    results.append(("M01 (Normalization)", test_m01_normalization()))

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    all_passed = True
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {status}: {name}")
        if not passed:
            all_passed = False

    print("\n" + ("All tests passed!" if all_passed else "Some tests failed."))
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())

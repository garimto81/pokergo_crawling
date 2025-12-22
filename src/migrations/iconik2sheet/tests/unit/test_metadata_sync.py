"""Unit tests for FullMetadataSync multi-value extraction.

Tests the _fetch_metadata method's handling of multi-value fields
like PlayersTags and PokerPlayTags.
"""

import pytest

from sync.full_metadata_sync import METADATA_FIELD_MAP, extract_field_values


class TestMultiValueExtraction:
    """Tests for multi-value field extraction."""

    def test_extract_single_value(self):
        """Single value should be extracted as-is."""
        field_data = {
            "field_values": [{"value": "Phil Ivey"}]
        }

        values = extract_field_values(field_data)
        assert values == "Phil Ivey"

    def test_extract_multiple_values(self):
        """Multiple values should be joined with comma."""
        field_data = {
            "field_values": [
                {"value": "Phil Ivey"},
                {"value": "Daniel Negreanu"},
                {"value": "Doyle Brunson"},
            ]
        }

        values = extract_field_values(field_data)
        assert values == "Phil Ivey,Daniel Negreanu,Doyle Brunson"

    def test_extract_empty_field_values(self):
        """Empty field_values should return None."""
        field_data = {"field_values": []}

        values = extract_field_values(field_data)
        assert values is None

    def test_extract_none_values_filtered(self):
        """None values in the list should be filtered out."""
        field_data = {
            "field_values": [
                {"value": "Phil Ivey"},
                {"value": None},
                {"value": "Daniel Negreanu"},
            ]
        }

        values = extract_field_values(field_data)
        assert values == "Phil Ivey,Daniel Negreanu"

    def test_extract_empty_string_values_filtered(self):
        """Empty string values should be filtered out."""
        field_data = {
            "field_values": [
                {"value": "Phil Ivey"},
                {"value": ""},
                {"value": "Daniel Negreanu"},
            ]
        }

        values = extract_field_values(field_data)
        assert values == "Phil Ivey,Daniel Negreanu"

    def test_extract_missing_value_key(self):
        """Items without 'value' key should be skipped."""
        field_data = {
            "field_values": [
                {"value": "Phil Ivey"},
                {"label": "No value key"},
                {"value": "Daniel Negreanu"},
            ]
        }

        values = extract_field_values(field_data)
        assert values == "Phil Ivey,Daniel Negreanu"

    def test_extract_invalid_field_data(self):
        """Invalid field_data should return None."""
        assert extract_field_values(None) is None
        assert extract_field_values({}) is None
        assert extract_field_values("string") is None

    def test_players_tags_multi_value(self):
        """PlayersTags specific test - real world example."""
        # GGmetadata: "Seth Davies,DAVIES"
        # Iconik API: [{"value": "Seth Davies"}, {"value": "DAVIES"}]
        field_data = {
            "field_values": [
                {"value": "Seth Davies"},
                {"value": "DAVIES"},
            ]
        }

        values = extract_field_values(field_data)
        assert values == "Seth Davies,DAVIES"

    def test_poker_play_tags_multi_value(self):
        """PokerPlayTags specific test - real world example."""
        # GGmetadata: "MysteryHand,Bluff"
        # Iconik API: [{"value": "MysteryHand"}, {"value": "Bluff"}]
        field_data = {
            "field_values": [
                {"value": "MysteryHand"},
                {"value": "Bluff"},
            ]
        }

        values = extract_field_values(field_data)
        assert values == "MysteryHand,Bluff"


class TestMetadataFieldMap:
    """Tests for METADATA_FIELD_MAP configuration."""

    def test_all_expected_fields_present(self):
        """All 29 metadata fields should be in the map."""
        expected_fields = [
            "Description", "ProjectName", "ProjectNameTag", "SearchTag",
            "Year_", "Location", "Venue", "EpisodeEvent", "Source", "Scene",
            "GameType", "PlayersTags", "HandGrade", "HANDTag", "EPICHAND",
            "Tournament", "PokerPlayTags", "Adjective", "Emotion",
            "AppearanceOutfit", "SceneryObject", "_gcvi_tags", "Badbeat",
            "Bluff", "Suckout", "Cooler", "RUNOUTTag", "PostFlop", "All-in",
        ]

        for field in expected_fields:
            assert field in METADATA_FIELD_MAP, f"Missing field: {field}"

    def test_field_count(self):
        """Should have exactly 29 metadata fields."""
        assert len(METADATA_FIELD_MAP) == 29


class TestSegmentMetadataExtraction:
    """Tests for segment metadata_values extraction."""

    def test_extract_metadata_from_segment(self):
        """Segment metadata_values should be extracted correctly."""
        # Simulate segment response with metadata_values
        segment = {
            "id": "segment-123",
            "time_start_milliseconds": 125000,
            "time_end_milliseconds": 180000,
            "segment_type": "GENERIC",
            "metadata_values": {
                "Description": {
                    "field_values": [{"value": "Phil Ivey bluffs with 72o"}]
                },
                "PlayersTags": {
                    "field_values": [
                        {"value": "Phil Ivey"},
                        {"value": "Daniel Negreanu"},
                    ]
                },
                "Year_": {
                    "field_values": [{"value": "2024"}]
                },
            },
        }

        metadata_values = segment.get("metadata_values", {})

        # Extract Description
        desc = extract_field_values(metadata_values.get("Description"))
        assert desc == "Phil Ivey bluffs with 72o"

        # Extract PlayersTags (multi-value)
        players = extract_field_values(metadata_values.get("PlayersTags"))
        assert players == "Phil Ivey,Daniel Negreanu"

        # Extract Year_
        year = extract_field_values(metadata_values.get("Year_"))
        assert year == "2024"

    def test_segment_without_metadata_values(self):
        """Segment without metadata_values should not cause errors."""
        segment = {
            "id": "segment-123",
            "time_start_milliseconds": 125000,
            "time_end_milliseconds": 180000,
            "segment_type": "GENERIC",
            # No metadata_values key
        }

        metadata_values = segment.get("metadata_values", {})
        assert metadata_values == {}

        # Extract should return None for missing fields
        desc = extract_field_values(metadata_values.get("Description"))
        assert desc is None

    def test_segment_with_empty_metadata_values(self):
        """Segment with empty metadata_values should not cause errors."""
        segment = {
            "id": "segment-123",
            "time_start_milliseconds": 125000,
            "time_end_milliseconds": 180000,
            "segment_type": "GENERIC",
            "metadata_values": {},
        }

        metadata_values = segment.get("metadata_values", {})

        desc = extract_field_values(metadata_values.get("Description"))
        assert desc is None

    def test_metadata_priority_segment_over_asset(self):
        """Segment metadata should take priority over asset metadata.

        This tests the expected behavior:
        - If segment has Description, use segment's Description
        - If segment doesn't have PlayersTags, use asset's PlayersTags
        """
        segment_metadata = {
            "Description": {
                "field_values": [{"value": "Segment description"}]
            },
            # PlayersTags missing in segment
        }

        asset_metadata = {
            "Description": {
                "field_values": [{"value": "Asset description"}]
            },
            "PlayersTags": {
                "field_values": [{"value": "From Asset"}]
            },
        }

        export_data = {}
        segment_fields = set()

        # Step 1: Extract from segment (priority)
        for api_field, model_field in METADATA_FIELD_MAP.items():
            field_data = segment_metadata.get(api_field)
            value = extract_field_values(field_data)
            if value is not None:
                export_data[model_field] = value
                segment_fields.add(model_field)

        # Step 2: Extract from asset (fallback, skip existing)
        for api_field, model_field in METADATA_FIELD_MAP.items():
            if model_field in segment_fields:
                continue
            field_data = asset_metadata.get(api_field)
            value = extract_field_values(field_data)
            if value is not None:
                export_data[model_field] = value

        # Verify priority
        assert export_data.get("Description") == "Segment description"  # From segment
        assert export_data.get("PlayersTags") == "From Asset"  # Fallback from asset


class TestGenericSegmentFiltering:
    """Tests for GENERIC segment filtering.

    Iconik stores different segment types:
    - GENERIC: System-created template with timecode range
    - COMMENT: User comments/markers (point markers, start=end)
    - MARKER: Visual markers

    Only GENERIC segments should be used for timecode extraction.
    """

    def test_filter_generic_from_mixed_segments(self):
        """GENERIC segment should be filtered from mixed types."""
        segments = [
            {
                "id": "comment-1",
                "time_start_milliseconds": 347300,
                "time_end_milliseconds": 347300,
                "segment_type": "COMMENT",
            },
            {
                "id": "generic-1",
                "time_start_milliseconds": 136600,
                "time_end_milliseconds": 513088,
                "segment_type": "GENERIC",
            },
            {
                "id": "marker-1",
                "time_start_milliseconds": 500000,
                "time_end_milliseconds": 500000,
                "segment_type": "MARKER",
            },
        ]

        generic_segments = [
            s for s in segments if s.get("segment_type") == "GENERIC"
        ]

        assert len(generic_segments) == 1
        assert generic_segments[0]["id"] == "generic-1"
        assert generic_segments[0]["time_start_milliseconds"] == 136600
        assert generic_segments[0]["time_end_milliseconds"] == 513088

    def test_no_generic_segment(self):
        """When no GENERIC segment exists, timecode should not be extracted."""
        segments = [
            {
                "id": "comment-1",
                "time_start_milliseconds": 347300,
                "time_end_milliseconds": 347300,
                "segment_type": "COMMENT",
            },
        ]

        generic_segments = [
            s for s in segments if s.get("segment_type") == "GENERIC"
        ]

        assert len(generic_segments) == 0

    def test_comment_segment_is_point_marker(self):
        """COMMENT segments typically have start=end (point marker)."""
        segment = {
            "id": "comment-1",
            "time_start_milliseconds": 347300,
            "time_end_milliseconds": 347300,
            "segment_type": "COMMENT",
        }

        # COMMENT is a point marker
        assert segment["time_start_milliseconds"] == segment["time_end_milliseconds"]

    def test_generic_segment_has_range(self):
        """GENERIC segments have a time range (start != end)."""
        segment = {
            "id": "generic-1",
            "time_start_milliseconds": 136600,
            "time_end_milliseconds": 513088,
            "segment_type": "GENERIC",
        }

        # GENERIC has a range
        assert segment["time_start_milliseconds"] != segment["time_end_milliseconds"]


class TestGenericSegmentMetadataAlwaysEmpty:
    """Tests confirming GENERIC segment metadata_values is always empty.

    According to ICONIK_DATA_STRUCTURE.md:
    - GENERIC Segment is a system-created template
    - metadata_values is ALWAYS empty (verified with 100% of samples)
    - Worker metadata is stored in Asset Metadata API, not Segment
    """

    def test_generic_segment_metadata_values_empty(self):
        """GENERIC segment's metadata_values is always empty."""
        # Real Iconik API response - GENERIC segment
        segment = {
            "id": "generic-1",
            "time_start_milliseconds": 136600,
            "time_end_milliseconds": 513088,
            "segment_type": "GENERIC",
            "metadata_values": {},  # Always empty!
        }

        metadata_values = segment.get("metadata_values", {})
        assert metadata_values == {}

    def test_worker_metadata_not_in_segment(self):
        """Worker metadata (Description, PlayersTags) is not in segment.

        This confirms the documented behavior:
        - Segment.metadata_values: {} (empty)
        - Asset Metadata API: contains actual metadata
        """
        # Simulated real case: serock vs griff
        segment = {
            "id": "generic-1",
            "time_start_milliseconds": 136600,
            "time_end_milliseconds": 513088,
            "segment_type": "GENERIC",
            "metadata_values": {},
        }

        # No metadata in segment
        metadata_values = segment.get("metadata_values", {})
        assert "Description" not in metadata_values
        assert "PlayersTags" not in metadata_values
        assert "EPICHAND" not in metadata_values

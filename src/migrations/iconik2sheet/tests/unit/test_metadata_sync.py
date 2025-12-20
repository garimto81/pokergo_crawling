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

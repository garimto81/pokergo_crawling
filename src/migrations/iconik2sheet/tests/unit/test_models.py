"""Unit tests for Pydantic models."""

from datetime import datetime

import pytest


class TestIconikAsset:
    """Test IconikAsset model."""

    def test_required_fields(self):
        """Test required fields validation."""
        from iconik.models import IconikAsset

        asset = IconikAsset(id="abc-123", title="Test Asset")
        assert asset.id == "abc-123"
        assert asset.title == "Test Asset"

    def test_default_values(self):
        """Test default field values."""
        from iconik.models import IconikAsset

        asset = IconikAsset(id="abc", title="Test")
        assert asset.status == "ACTIVE"
        assert asset.is_online is True
        assert asset.external_id is None
        assert asset.analyze_status is None

    def test_datetime_parsing(self):
        """Test datetime field parsing from ISO string."""
        from iconik.models import IconikAsset

        asset = IconikAsset(id="abc", title="Test", created_at="2024-01-15T10:30:00Z")
        assert isinstance(asset.created_at, datetime)
        assert asset.created_at.year == 2024
        assert asset.created_at.month == 1

    def test_from_sample_fixture(self, sample_asset):
        """Test model creation from sample fixture."""
        from iconik.models import IconikAsset

        asset = IconikAsset(**sample_asset)
        assert asset.id == "12345678-1234-1234-1234-123456789abc"
        assert asset.title == "WSOP 2024 Main Event Hand 42"
        assert asset.external_id == "ext-001"


class TestIconikMetadata:
    """Test IconikMetadata model."""

    def test_basic_creation(self):
        """Test basic metadata creation."""
        from iconik.models import IconikMetadata

        metadata = IconikMetadata(asset_id="asset-123", view_id="view-456", fields={"key": "value"})
        assert metadata.asset_id == "asset-123"
        assert metadata.view_id == "view-456"
        assert metadata.fields["key"] == "value"

    def test_empty_fields_default(self):
        """Test empty fields dictionary default."""
        from iconik.models import IconikMetadata

        metadata = IconikMetadata(asset_id="a", view_id="v")
        assert metadata.fields == {}


class TestIconikCollection:
    """Test IconikCollection model."""

    def test_required_fields(self):
        """Test required fields."""
        from iconik.models import IconikCollection

        collection = IconikCollection(id="col-123", title="My Collection")
        assert collection.id == "col-123"
        assert collection.title == "My Collection"

    def test_default_values(self):
        """Test default values."""
        from iconik.models import IconikCollection

        collection = IconikCollection(id="col", title="Test")
        assert collection.parent_id is None
        assert collection.is_root is False


class TestIconikPaginatedResponse:
    """Test IconikPaginatedResponse model."""

    def test_pagination_fields(self):
        """Test pagination metadata."""
        from iconik.models import IconikPaginatedResponse

        response = IconikPaginatedResponse(
            objects=[{"id": "1"}, {"id": "2"}],
            page=1,
            pages=5,
            per_page=100,
            total=450,
        )
        assert response.page == 1
        assert response.pages == 5
        assert response.per_page == 100
        assert response.total == 450
        assert len(response.objects) == 2

    def test_optional_ids(self):
        """Test optional first_id and last_id."""
        from iconik.models import IconikPaginatedResponse

        response = IconikPaginatedResponse(
            objects=[],
            page=1,
            pages=1,
            per_page=100,
            total=0,
        )
        assert response.first_id is None
        assert response.last_id is None


class TestIconikMetadataView:
    """Test IconikMetadataView model."""

    def test_basic_creation(self):
        """Test basic view creation."""
        from iconik.models import IconikMetadataView

        view = IconikMetadataView(id="view-123", name="Poker Metadata", description="WSOP clips")
        assert view.id == "view-123"
        assert view.name == "Poker Metadata"
        assert view.description == "WSOP clips"

    def test_default_view_fields(self):
        """Test empty view_fields default."""
        from iconik.models import IconikMetadataView

        view = IconikMetadataView(id="v", name="Test")
        assert view.view_fields == []


class TestIconikSegment:
    """Test IconikSegment model."""

    def test_timecode_fields(self):
        """Test timecode fields."""
        from iconik.models import IconikSegment

        segment = IconikSegment(
            id="seg-001",
            asset_id="asset-123",
            time_base=125000,
            time_end=180000,
        )
        assert segment.time_base == 125000
        assert segment.time_end == 180000

    def test_default_segment_type(self):
        """Test default segment_type."""
        from iconik.models import IconikSegment

        segment = IconikSegment(id="s", asset_id="a")
        assert segment.segment_type == "GENERIC"

    def test_from_sample_fixture(self, sample_segments):
        """Test model creation from sample fixture."""
        from iconik.models import IconikSegment

        seg_data = sample_segments["objects"][0]
        segment = IconikSegment(**seg_data)
        assert segment.time_base == 125000
        assert segment.time_end == 180000


class TestIconikAssetExport:
    """Test IconikAssetExport 35-column model."""

    def test_all_35_columns_present(self):
        """Test model has exactly 35 fields."""
        from iconik.models import IconikAssetExport

        field_count = len(IconikAssetExport.model_fields)
        assert field_count == 35, f"Expected 35 fields, got {field_count}"

    def test_required_fields(self):
        """Test only id and title are required."""
        from iconik.models import IconikAssetExport

        export = IconikAssetExport(id="abc", title="Test")
        assert export.id == "abc"
        assert export.title == "Test"

    def test_timecode_fields(self):
        """Test timecode fields (ms and seconds)."""
        from iconik.models import IconikAssetExport

        export = IconikAssetExport(
            id="abc",
            title="Test",
            time_start_ms=125000,
            time_end_ms=180000,
            time_start_S=125.0,
            time_end_S=180.0,
        )
        assert export.time_start_ms == 125000
        assert export.time_end_ms == 180000
        assert export.time_start_S == 125.0
        assert export.time_end_S == 180.0

    def test_metadata_fields(self):
        """Test metadata fields from PRD."""
        from iconik.models import IconikAssetExport

        export = IconikAssetExport(
            id="abc",
            title="Test",
            Description="Phil Ivey bluffs",
            ProjectName="WSOP 2024",
            Year_=2024,
            Location="Las Vegas",
            GameType="NLH",
            PlayersTags="Phil Ivey, Daniel Negreanu",
            HandGrade="★★★",
            EPICHAND=True,
        )
        assert export.Description == "Phil Ivey bluffs"
        assert export.ProjectName == "WSOP 2024"
        assert export.Year_ == 2024
        assert export.EPICHAND is True

    def test_all_fields_optional_except_id_title(self):
        """Test all fields except id and title are optional."""
        from iconik.models import IconikAssetExport

        # Should not raise
        export = IconikAssetExport(id="x", title="y")

        # Check all optional fields are None
        assert export.time_start_ms is None
        assert export.Description is None
        assert export.EPICHAND is None

    def test_column_names_match_prd(self):
        """Test column names match PRD specification (35 columns)."""
        from iconik.models import IconikAssetExport

        expected_columns = [
            # Basic info (2)
            "id",
            "title",
            # Timecode (4)
            "time_start_ms",
            "time_end_ms",
            "time_start_S",
            "time_end_S",
            # Metadata fields (20)
            "Description",
            "ProjectName",
            "ProjectNameTag",
            "SearchTag",
            "Year_",
            "Location",
            "Venue",
            "EpisodeEvent",
            "Source",
            "Scene",
            "GameType",
            "PlayersTags",
            "HandGrade",
            "HANDTag",
            "EPICHAND",
            "Tournament",
            "PokerPlayTags",
            "Adjective",
            "Emotion",
            "AppearanceOutfit",
            # Additional fields (9)
            "SceneryObject",
            "gcvi_tags",  # API uses _gcvi_tags, model uses gcvi_tags
            "Badbeat",
            "Bluff",
            "Suckout",
            "Cooler",
            "RUNOUTTag",
            "PostFlop",
            "All_in",
        ]

        actual_columns = list(IconikAssetExport.model_fields.keys())
        assert actual_columns == expected_columns, f"Column mismatch: {actual_columns}"

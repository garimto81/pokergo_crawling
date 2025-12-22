"""Unit tests for SyncStats model."""


class TestSyncStats:
    """Test SyncStats dataclass."""

    def test_initial_counters_zero(self):
        """Test all counters start at zero."""
        from sync.stats import SyncStats

        stats = SyncStats()
        assert stats.total_assets == 0
        assert stats.processed == 0
        assert stats.metadata_success == 0
        assert stats.metadata_404 == 0
        assert stats.metadata_other_error == 0
        assert stats.segments_success == 0
        assert stats.segments_empty == 0
        assert stats.segments_404 == 0

    def test_record_metadata_success_increments_counter(self):
        """Test metadata success recording."""
        from sync.stats import SyncStats

        stats = SyncStats()
        stats.record_metadata_success({"Description": "test", "GameType": "NLH"})

        assert stats.metadata_success == 1
        assert stats.field_counts["Description"] == 1
        assert stats.field_counts["GameType"] == 1

    def test_record_metadata_success_ignores_none_values(self):
        """Test that None values are not counted in field_counts."""
        from sync.stats import SyncStats

        stats = SyncStats()
        stats.record_metadata_success({"Description": "test", "GameType": None, "Empty": ""})

        assert stats.metadata_success == 1
        assert stats.field_counts.get("Description") == 1
        assert "GameType" not in stats.field_counts
        assert "Empty" not in stats.field_counts

    def test_record_metadata_404(self):
        """Test 404 error recording."""
        from sync.stats import SyncStats

        stats = SyncStats()
        stats.record_metadata_404("asset-123")

        assert stats.metadata_404 == 1
        assert len(stats.error_samples) == 1
        assert stats.error_samples[0]["type"] == "metadata_404"
        assert stats.error_samples[0]["asset_id"] == "asset-123"

    def test_record_metadata_error(self):
        """Test other metadata error recording."""
        from sync.stats import SyncStats

        stats = SyncStats()
        stats.record_metadata_error("asset-456", "Connection timeout")

        assert stats.metadata_other_error == 1
        assert len(stats.error_samples) == 1
        assert stats.error_samples[0]["type"] == "metadata_error"
        assert stats.error_samples[0]["detail"] == "Connection timeout"

    def test_record_segments_success(self):
        """Test successful segments recording."""
        from sync.stats import SyncStats

        stats = SyncStats()
        stats.record_segments_result("asset-123", [{"time_base": 1000}])

        assert stats.segments_success == 1
        assert stats.segments_empty == 0
        assert stats.segments_404 == 0

    def test_record_segments_empty(self):
        """Test empty segments recording."""
        from sync.stats import SyncStats

        stats = SyncStats()
        stats.record_segments_result("asset-123", [])

        assert stats.segments_success == 0
        assert stats.segments_empty == 1
        assert stats.segments_404 == 0

    def test_record_segments_404(self):
        """Test 404 segments recording."""
        from sync.stats import SyncStats

        stats = SyncStats()
        stats.record_segments_result("asset-123", [], is_404=True)

        assert stats.segments_success == 0
        assert stats.segments_empty == 0
        assert stats.segments_404 == 1

    def test_error_samples_limited_to_max(self):
        """Test error samples are limited to max_error_samples."""
        from sync.stats import SyncStats

        stats = SyncStats()
        stats.max_error_samples = 5

        for i in range(10):
            stats.record_metadata_404(f"asset-{i}")

        assert len(stats.error_samples) == 5
        assert stats.metadata_404 == 10  # Counter still increments

    def test_to_report_structure(self):
        """Test report generation structure."""
        from sync.stats import SyncStats

        stats = SyncStats()
        stats.total_assets = 100
        stats.processed = 100
        stats.metadata_success = 20
        stats.metadata_404 = 80
        stats.segments_success = 5
        stats.segments_empty = 95
        stats.record_metadata_success({"Description": "test"})

        report = stats.to_report()

        assert "summary" in report
        assert "metadata" in report
        assert "segments" in report
        assert "field_coverage" in report
        assert "error_samples" in report

        assert report["summary"]["total_assets"] == 100
        assert report["metadata"]["success"] == 21  # +1 from record_metadata_success
        assert report["metadata"]["not_found_404"] == 80
        assert "20." in report["metadata"]["success_rate"]  # ~20%

    def test_to_report_success_rate_calculation(self):
        """Test success rate calculation."""
        from sync.stats import SyncStats

        stats = SyncStats()
        stats.metadata_success = 50
        stats.metadata_404 = 50

        report = stats.to_report()

        assert "50.0%" in report["metadata"]["success_rate"]

    def test_to_report_handles_zero_division(self):
        """Test report handles zero division gracefully."""
        from sync.stats import SyncStats

        stats = SyncStats()
        # All zeros

        report = stats.to_report()

        assert report["metadata"]["success_rate"] == "0.0%"
        assert report["field_coverage"] == {}

    def test_field_counts_accumulate(self):
        """Test field counts accumulate across multiple records."""
        from sync.stats import SyncStats

        stats = SyncStats()
        stats.record_metadata_success({"Description": "a", "GameType": "NLH"})
        stats.record_metadata_success({"Description": "b", "PlayersTags": "Phil"})
        stats.record_metadata_success({"Description": "c"})

        assert stats.field_counts["Description"] == 3
        assert stats.field_counts["GameType"] == 1
        assert stats.field_counts["PlayersTags"] == 1
        assert stats.metadata_success == 3

"""Sync statistics models for graceful error handling."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class SyncStats:
    """Synchronization statistics for tracking metadata/segments fetch results.

    Tracks success/failure counts and provides detailed reporting for
    graceful 404 error handling.
    """

    # Asset counts
    total_assets: int = 0
    processed: int = 0

    # Metadata results
    metadata_success: int = 0
    metadata_404: int = 0
    metadata_other_error: int = 0

    # Segment results
    segments_success: int = 0
    segments_empty: int = 0
    segments_404: int = 0
    subclips_with_timecode: int = 0  # Subclip with timecode from asset itself

    # Field-level statistics
    field_counts: dict[str, int] = field(default_factory=dict)

    # Error details (for debugging)
    error_samples: list[dict[str, Any]] = field(default_factory=list)
    max_error_samples: int = 10

    def record_metadata_success(self, fields: dict[str, Any]) -> None:
        """Record successful metadata fetch.

        Args:
            fields: Dictionary of field names to values.
                    Only non-None, non-empty values are counted.
        """
        self.metadata_success += 1
        for field_name, value in fields.items():
            if value is not None and value != "":
                self.field_counts[field_name] = self.field_counts.get(field_name, 0) + 1

    def record_metadata_404(self, asset_id: str) -> None:
        """Record 404 error for metadata.

        Args:
            asset_id: Asset UUID that returned 404.
        """
        self.metadata_404 += 1
        self._add_error_sample("metadata_404", asset_id)

    def record_metadata_error(self, asset_id: str, error: str) -> None:
        """Record other metadata error.

        Args:
            asset_id: Asset UUID that caused error.
            error: Error message or description.
        """
        self.metadata_other_error += 1
        self._add_error_sample("metadata_error", asset_id, error)

    def record_segments_result(
        self, asset_id: str, segments: list, is_404: bool = False, is_subclip: bool = False
    ) -> None:
        """Record segments fetch result.

        Args:
            asset_id: Asset UUID.
            segments: List of segments returned (empty if none).
            is_404: True if 404 error occurred.
            is_subclip: True if this is a subclip (timecode from asset, not segment).
        """
        if is_subclip:
            self.subclips_with_timecode += 1
        elif is_404:
            self.segments_404 += 1
        elif not segments:
            self.segments_empty += 1
        else:
            self.segments_success += 1

    def _add_error_sample(
        self, error_type: str, asset_id: str, detail: str | None = None
    ) -> None:
        """Add error sample for debugging.

        Args:
            error_type: Type of error (e.g., "metadata_404", "metadata_error").
            asset_id: Asset UUID.
            detail: Optional error detail message.
        """
        if len(self.error_samples) < self.max_error_samples:
            self.error_samples.append(
                {
                    "type": error_type,
                    "asset_id": asset_id,
                    "detail": detail,
                    "timestamp": datetime.now().isoformat(),
                }
            )

    def to_report(self) -> dict[str, Any]:
        """Generate statistics report.

        Returns:
            Dictionary with summary, metadata, segments, field_coverage,
            and error_samples sections.
        """
        total_metadata_attempts = (
            self.metadata_success + self.metadata_404 + self.metadata_other_error
        )

        # Calculate success rate
        if total_metadata_attempts > 0:
            success_rate = self.metadata_success / total_metadata_attempts * 100
        else:
            success_rate = 0.0

        # Calculate field coverage
        field_coverage = {}
        if self.metadata_success > 0:
            for field_name, count in sorted(
                self.field_counts.items(), key=lambda x: -x[1]
            ):
                percentage = count / self.metadata_success * 100
                field_coverage[field_name] = (
                    f"{count}/{self.metadata_success} ({percentage:.1f}%)"
                )

        return {
            "summary": {
                "total_assets": self.total_assets,
                "processed": self.processed,
            },
            "metadata": {
                "success": self.metadata_success,
                "success_rate": f"{success_rate:.1f}%",
                "not_found_404": self.metadata_404,
                "other_errors": self.metadata_other_error,
            },
            "segments": {
                "with_segments": self.segments_success,
                "subclips": self.subclips_with_timecode,
                "empty": self.segments_empty,
                "not_found_404": self.segments_404,
            },
            "field_coverage": field_coverage,
            "error_samples": self.error_samples,
        }

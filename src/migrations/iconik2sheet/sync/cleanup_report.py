"""Cleanup report generator.

Generates CSV and log reports for backup cleanup operations.
"""

import csv
import logging
from datetime import datetime
from pathlib import Path

from .backup_cleanup import CleanupResult


def setup_logging(log_dir: str = "data/cleanup_logs") -> Path:
    """Setup logging for cleanup operation.

    Args:
        log_dir: Directory for log files

    Returns:
        Path to log file
    """
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    log_file = log_path / f"backup_cleanup_{datetime.now():%Y%m%d_%H%M%S}.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )

    return log_file


class CleanupReportGenerator:
    """Generate cleanup reports in various formats."""

    def __init__(self, result: CleanupResult) -> None:
        self.result = result

    def to_csv(self, path: str) -> None:
        """Export deletion targets/results to CSV.

        For dry-run: exports target list
        For execute: exports deletion results

        Args:
            path: Output CSV file path
        """
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)

            # Header
            writer.writerow(["Asset ID", "Title", "Status"])

            # If we have targets (dry-run mode), export them
            if self.result.targets and not self.result.deleted:
                for asset_id, title in self.result.targets:
                    writer.writerow([asset_id, title, "TO_DELETE"])
            else:
                # Export deletion results
                # Find title from targets if available
                title_map = {aid: title for aid, title in self.result.targets}

                for asset_id in self.result.deleted:
                    title = title_map.get(asset_id, "")
                    writer.writerow([asset_id, title, "DELETED"])

                for asset_id in self.result.not_found:
                    title = title_map.get(asset_id, "")
                    writer.writerow([asset_id, title, "NOT_FOUND"])

                for asset_id, error in self.result.failed:
                    title = title_map.get(asset_id, "")
                    writer.writerow([asset_id, title, f"FAILED: {error}"])

        print(f"Report saved to: {output_path}")

    def to_summary_csv(self, path: str) -> None:
        """Export summary statistics to CSV.

        Args:
            path: Output CSV file path
        """
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)

            writer.writerow(["Metric", "Value"])
            writer.writerow(["Run Time", self.result.start_time.isoformat() if self.result.start_time else ""])
            writer.writerow(["Duration (seconds)", f"{self.result.duration_seconds:.1f}"])
            writer.writerow(["Master_Catalog Backup Rows", self.result.total_backup_rows])
            writer.writerow(["Unique Backup Stems", self.result.unique_backup_stems])
            writer.writerow(["Matched Iconik Assets", self.result.matched_assets])
            writer.writerow(["Skipped Subclips", self.result.skipped_subclips])
            writer.writerow(["Deleted", self.result.deleted_count])
            writer.writerow(["Not Found (404)", len(self.result.not_found)])
            writer.writerow(["Failed", self.result.failed_count])

        print(f"Summary saved to: {output_path}")

    def log_result(self) -> None:
        """Log cleanup result to logging system."""
        logger = logging.getLogger(__name__)

        logger.info("=" * 60)
        logger.info("Backup Cleanup Result")
        logger.info("=" * 60)
        logger.info(f"Start Time: {self.result.start_time}")
        logger.info(f"End Time: {self.result.end_time}")
        logger.info(f"Duration: {self.result.duration_seconds:.1f} seconds")
        logger.info("-" * 60)
        logger.info(f"Master_Catalog Backup Rows: {self.result.total_backup_rows}")
        logger.info(f"Unique Backup Stems: {self.result.unique_backup_stems}")
        logger.info(f"Matched Iconik Assets: {self.result.matched_assets}")
        logger.info(f"Skipped Subclips: {self.result.skipped_subclips}")
        logger.info("-" * 60)
        logger.info(f"Deleted: {self.result.deleted_count}")
        logger.info(f"Not Found (404): {len(self.result.not_found)}")
        logger.info(f"Failed: {self.result.failed_count}")
        logger.info("=" * 60)

        # Log failed items
        if self.result.failed:
            logger.warning("Failed deletions:")
            for asset_id, error in self.result.failed:
                logger.warning(f"  {asset_id}: {error}")

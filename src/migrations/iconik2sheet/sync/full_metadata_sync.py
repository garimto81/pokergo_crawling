"""Full metadata sync - 전체 메타데이터 추출 (35개 컬럼) with graceful 404 handling."""

import uuid
from datetime import datetime

from config.settings import get_settings
from iconik import IconikClient
from iconik.exceptions import IconikAPIError, IconikNotFoundError
from sheets import SheetsWriter

from .state import SyncState
from .stats import SyncStats

# 메타데이터 필드 매핑 (Iconik API 필드명 → 모델 필드명)
# API 응답 구조: {"Description": [{"value": "..."}], "All-in": [{"label": "...", "value": "..."}]}
METADATA_FIELD_MAP = {
    # 기본 정보
    "Description": "Description",
    "ProjectName": "ProjectName",
    "ProjectNameTag": "ProjectNameTag",
    "SearchTag": "SearchTag",
    "Year_": "Year_",
    "Location": "Location",
    "Venue": "Venue",
    "EpisodeEvent": "EpisodeEvent",
    "Source": "Source",
    "Scene": "Scene",
    # 포커 관련
    "GameType": "GameType",
    "PlayersTags": "PlayersTags",
    "HandGrade": "HandGrade",
    "HANDTag": "HANDTag",
    "EPICHAND": "EPICHAND",
    "Tournament": "Tournament",
    "PokerPlayTags": "PokerPlayTags",
    "Adjective": "Adjective",
    "Emotion": "Emotion",
    "AppearanceOutfit": "AppearanceOutfit",
    # 추가 필드
    "SceneryObject": "SceneryObject",
    "_gcvi_tags": "gcvi_tags",  # API uses _gcvi_tags, model uses gcvi_tags
    "Badbeat": "Badbeat",
    "Bluff": "Bluff",
    "Suckout": "Suckout",
    "Cooler": "Cooler",
    "RUNOUTTag": "RUNOUTTag",
    "PostFlop": "PostFlop",
    "All-in": "All_in",  # 하이픈 → 언더스코어
}


def extract_field_values(field_data: dict | None) -> str | None:
    """Extract all values from field_data and join with comma.

    Handles multi-value fields like PlayersTags, PokerPlayTags.

    Args:
        field_data: API response field data with field_values list
            Example: {"field_values": [{"value": "A"}, {"value": "B"}]}

    Returns:
        Comma-joined values or None if no values
        Example: "A,B"
    """
    if not field_data or not isinstance(field_data, dict):
        return None

    field_values = field_data.get("field_values", [])
    if not field_values:
        return None

    # Extract all values (filter None and empty strings)
    values = []
    for item in field_values:
        if isinstance(item, dict):
            value = item.get("value")
            if value is not None and value != "":
                values.append(str(value))

    if not values:
        return None

    return ",".join(values)


class FullMetadataSync:
    """Full metadata sync from Iconik to Sheets (35 columns).

    Features graceful 404 handling with detailed statistics reporting.
    """

    def __init__(self) -> None:
        self.iconik = IconikClient()
        self.sheets = SheetsWriter()
        self.state = SyncState()
        self.stats = SyncStats()

    def run(self, skip_sampling: bool = False) -> dict:
        """Run full metadata sync.

        Args:
            skip_sampling: Skip pre-sync sampling check

        Returns:
            Sync result summary
        """
        sync_id = str(uuid.uuid4())[:8]
        started_at = datetime.now()

        print(f"Starting full metadata sync (ID: {sync_id})")
        print("This will fetch metadata for each asset - may take a while...")

        result = {
            "sync_id": sync_id,
            "sync_type": "full_metadata",
            "started_at": started_at,
            "completed_at": None,
            "assets_processed": 0,
            "assets_with_metadata": 0,
            "assets_with_segments": 0,
            "status": "running",
        }

        try:
            # Get metadata view ID from settings
            settings = get_settings()
            view_id = settings.iconik.metadata_view_id if settings.iconik else None

            if not view_id:
                print("Warning: ICONIK_METADATA_VIEW_ID not set, metadata will be empty")

            # Pre-sync sampling (optional)
            if not skip_sampling and view_id:
                self._run_sampling(view_id)

            # Sync assets with full metadata
            exports = self._sync_assets_with_metadata(view_id)
            result["assets_processed"] = len(exports)
            result["assets_with_metadata"] = self.stats.metadata_success
            result["assets_with_segments"] = self.stats.segments_success

            # Update state
            self.state.mark_sync_complete(
                sync_type="full_metadata",
                total_assets=len(exports),
                total_collections=0,  # Full metadata sync는 컬렉션 동기화 안함
            )

            result["completed_at"] = datetime.now()
            result["status"] = "success"

            # Write sync log
            self.sheets.write_sync_log(result)

            # Print detailed statistics report
            report = self.stats.to_report()
            self._print_report(report)

        except Exception as e:
            result["status"] = "failed"
            result["completed_at"] = datetime.now()
            self.sheets.write_sync_log(result)

            print(f"Sync failed: {e}")
            raise

        finally:
            self.iconik.close()

        return result

    def _run_sampling(self, view_id: str, sample_size: int = 10) -> None:
        """Pre-sync sampling to check metadata availability.

        Args:
            view_id: Metadata view UUID
            sample_size: Number of assets to sample
        """
        print(f"\n[Sampling] Checking {sample_size} random assets...")

        success = 0
        not_found = 0

        for i, asset in enumerate(self.iconik.get_all_assets()):
            if i >= sample_size:
                break

            metadata = self.iconik.get_asset_metadata(
                asset.id, view_id, raise_for_404=False
            )

            if metadata is not None:
                success += 1
            else:
                not_found += 1

        rate = success / sample_size * 100
        print(f"  Sample result: {success}/{sample_size} ({rate:.0f}%) have metadata")

        if rate < 50:
            print("  Warning: Low metadata availability, consider checking view_id")
            self._show_available_views()

    def _show_available_views(self) -> None:
        """Show available metadata views."""
        print("\n  Available metadata views:")
        try:
            views = self.iconik.get_metadata_views()
            for v in views[:5]:
                print(f"    - {v.get('id', 'N/A')}: {v.get('name', 'Untitled')}")
            if len(views) > 5:
                print(f"    ... and {len(views) - 5} more")
        except Exception as e:
            print(f"    (Could not fetch views: {e})")

    def _sync_assets_with_metadata(self, view_id: str | None) -> list[dict]:
        """Sync all assets with full metadata and graceful error handling.

        Args:
            view_id: Metadata view UUID (or None to skip metadata)

        Returns:
            List of export data dicts
        """
        print("\nFetching assets with metadata...")

        exports = []

        for asset in self.iconik.get_all_assets():
            self.stats.processed += 1

            # Build export data
            export_data = {
                "id": asset.id,
                "title": asset.title,
            }

            # Fetch segments
            self._fetch_segments(asset.id, export_data)

            # Fetch metadata
            if view_id:
                self._fetch_metadata(asset.id, view_id, export_data)

            exports.append(export_data)

            if self.stats.processed % 100 == 0:
                self._print_progress()

        self.stats.total_assets = len(exports)

        # Write to sheet
        print(f"\nProcessed {len(exports)} assets")
        print("Writing to Iconik_Full_Metadata sheet...")
        self.sheets.write_full_metadata(exports)

        return exports

    def _fetch_segments(self, asset_id: str, export_data: dict) -> None:
        """Fetch segments with graceful 404 handling.

        Args:
            asset_id: Asset UUID
            export_data: Dict to populate with segment data
        """
        try:
            segments = self.iconik.get_asset_segments(asset_id, raise_for_404=False)

            if segments:
                first_segment = segments[0]
                # API returns time_start_milliseconds, time_end_milliseconds
                time_start = first_segment.get("time_start_milliseconds")
                time_end = first_segment.get("time_end_milliseconds")

                if time_start is not None:
                    export_data["time_start_ms"] = time_start
                    export_data["time_start_S"] = time_start / 1000

                if time_end is not None:
                    export_data["time_end_ms"] = time_end
                    export_data["time_end_S"] = time_end / 1000

                self.stats.record_segments_result(asset_id, segments)
            else:
                self.stats.record_segments_result(asset_id, [])

        except IconikNotFoundError:
            self.stats.record_segments_result(asset_id, [], is_404=True)
        except Exception:
            # Log but continue - segments are optional
            self.stats.record_segments_result(asset_id, [])

    def _fetch_metadata(self, asset_id: str, view_id: str, export_data: dict) -> None:
        """Fetch metadata with graceful 404 handling.

        Args:
            asset_id: Asset UUID
            view_id: Metadata view UUID
            export_data: Dict to populate with metadata fields
        """
        try:
            metadata = self.iconik.get_asset_metadata(
                asset_id, view_id, raise_for_404=False
            )

            if metadata is None:
                self.stats.record_metadata_404(asset_id)
                return

            metadata_values = metadata.get("metadata_values", {})
            extracted_fields = {}

            for api_field, model_field in METADATA_FIELD_MAP.items():
                field_data = metadata_values.get(api_field)
                # API 응답 구조: {"field_values": [{"value": "..."}, ...]}
                # 다중 값 필드 처리 (PlayersTags, PokerPlayTags 등)
                value = extract_field_values(field_data)
                if value is not None:
                    export_data[model_field] = value
                    extracted_fields[model_field] = value

            self.stats.record_metadata_success(extracted_fields)

        except IconikNotFoundError:
            self.stats.record_metadata_404(asset_id)
        except IconikAPIError as e:
            self.stats.record_metadata_error(asset_id, str(e))
        except Exception as e:
            self.stats.record_metadata_error(asset_id, str(e))

    def _print_progress(self) -> None:
        """Print progress update."""
        s = self.stats
        print(
            f"  ... {s.processed} processed "
            f"(metadata: {s.metadata_success} OK, {s.metadata_404} 404, "
            f"{s.metadata_other_error} err)"
        )

    def _print_report(self, report: dict) -> None:
        """Print final statistics report.

        Args:
            report: Report dict from SyncStats.to_report()
        """
        print("\n" + "=" * 60)
        print("SYNC STATISTICS REPORT")
        print("=" * 60)

        print("\n[Summary]")
        print(f"  Total assets: {report['summary']['total_assets']}")
        print(f"  Processed: {report['summary']['processed']}")

        print("\n[Metadata]")
        m = report["metadata"]
        print(f"  Success: {m['success']} ({m['success_rate']})")
        print(f"  Not found (404): {m['not_found_404']}")
        print(f"  Other errors: {m['other_errors']}")

        print("\n[Segments]")
        s = report["segments"]
        print(f"  With segments: {s['with_segments']}")
        print(f"  Empty: {s['empty']}")
        print(f"  Not found (404): {s['not_found_404']}")

        if report["field_coverage"]:
            print("\n[Field Coverage] (top 10)")
            for i, (field, coverage) in enumerate(
                list(report["field_coverage"].items())[:10]
            ):
                print(f"  {field}: {coverage}")

        if report["error_samples"]:
            print(f"\n[Error Samples] ({len(report['error_samples'])} of max 10)")
            for err in report["error_samples"][:3]:
                detail = f" - {err['detail']}" if err.get("detail") else ""
                print(f"  - {err['type']}: {err['asset_id']}{detail}")

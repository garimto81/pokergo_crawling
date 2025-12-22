"""Test reverse sync - 타임코드 없는 Asset에 임의의 타임코드 입력 테스트.

Usage:
    python -m scripts.test_reverse_sync
"""

import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

import httpx
from rich.console import Console
from rich.table import Table

from config.settings import get_settings
from iconik import IconikClient


class ReverseSyncTester:
    """Test reverse sync to iconik."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.iconik = IconikClient()
        self.console = Console()

    def find_assets_without_segments(self, limit: int = 10) -> list[dict]:
        """타임코드(세그먼트)가 없는 Asset 찾기."""
        self.console.print("[bold]1. 타임코드 없는 Asset 검색 중...[/bold]")

        assets_without_segments = []
        checked = 0

        for asset in self.iconik.get_all_assets():
            checked += 1
            segments = self.iconik.get_asset_segments(asset.id, raise_for_404=False)

            if not segments:
                assets_without_segments.append({
                    "id": asset.id,
                    "title": asset.title[:50] if asset.title else "Untitled",
                })

                if len(assets_without_segments) >= limit:
                    break

            if checked % 100 == 0:
                self.console.print(f"   ... {checked}개 확인, {len(assets_without_segments)}개 발견")

        self.console.print(f"   [green]총 {len(assets_without_segments)}개 발견[/green]")
        return assets_without_segments

    def create_segment(self, asset_id: str, time_start_ms: int, time_end_ms: int) -> dict | None:
        """Asset에 세그먼트(타임코드) 생성 시도.

        iconik API: POST /assets/v1/assets/{asset_id}/segments/
        """
        endpoint = f"/assets/v1/assets/{asset_id}/segments/"

        # 세그먼트 데이터 (iconik API 형식)
        # segment_type: MARKER, QC, GENERIC, COMMENT, TAG, TRANSCRIPTION, SCENE, PERSON
        segment_data = {
            "time_start_milliseconds": time_start_ms,
            "time_end_milliseconds": time_end_ms,
            "segment_type": "GENERIC",
            "title": "Test Segment (Auto-generated)",
        }

        try:
            response = self.iconik.client.post(endpoint, json=segment_data)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            self.console.print(f"   [red]HTTP Error: {e.response.status_code}[/red]")
            self.console.print(f"   Response: {e.response.text[:500]}")
            return None
        except Exception as e:
            self.console.print(f"   [red]Error: {e}[/red]")
            return None

    def update_segment(self, asset_id: str, segment_id: str, time_start_ms: int, time_end_ms: int) -> dict | None:
        """기존 세그먼트 업데이트.

        iconik API: PUT /assets/v1/assets/{asset_id}/segments/{segment_id}/
        """
        endpoint = f"/assets/v1/assets/{asset_id}/segments/{segment_id}/"

        segment_data = {
            "time_start_milliseconds": time_start_ms,
            "time_end_milliseconds": time_end_ms,
        }

        try:
            response = self.iconik.client.put(endpoint, json=segment_data)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            self.console.print(f"   [red]HTTP Error: {e.response.status_code}[/red]")
            self.console.print(f"   Response: {e.response.text[:500]}")
            return None
        except Exception as e:
            self.console.print(f"   [red]Error: {e}[/red]")
            return None

    def verify_segment(self, asset_id: str) -> list[dict]:
        """세그먼트 생성 확인."""
        segments = self.iconik.get_asset_segments(asset_id, raise_for_404=False)
        return segments

    def run_test(self) -> None:
        """역방향 동기화 테스트 실행."""
        self.console.print("\n[bold blue]=== Reverse Sync Test ===[/bold blue]\n")

        # 1. 타임코드 없는 Asset 찾기
        assets = self.find_assets_without_segments(limit=3)

        if not assets:
            self.console.print("[yellow]타임코드 없는 Asset이 없습니다.[/yellow]")
            return

        # 결과 테이블
        table = Table(title="타임코드 없는 Asset 샘플")
        table.add_column("Asset ID", style="cyan")
        table.add_column("Title")

        for asset in assets:
            table.add_row(asset["id"], asset["title"])

        self.console.print(table)

        # 2. 첫 번째 Asset에 테스트 세그먼트 생성
        test_asset = assets[0]
        self.console.print(f"\n[bold]2. 세그먼트 생성 테스트[/bold]")
        self.console.print(f"   대상: {test_asset['id']}")
        self.console.print(f"   제목: {test_asset['title']}")

        # 임의의 타임코드 (0초 ~ 10초)
        time_start_ms = 0
        time_end_ms = 10000  # 10초

        self.console.print(f"   타임코드: {time_start_ms}ms ~ {time_end_ms}ms")

        result = self.create_segment(test_asset["id"], time_start_ms, time_end_ms)

        if result:
            self.console.print(f"   [green]OK - Segment created![/green]")
            self.console.print(f"   생성된 세그먼트 ID: {result.get('id', 'N/A')}")

            # 3. 확인
            self.console.print(f"\n[bold]3. 세그먼트 확인[/bold]")
            segments = self.verify_segment(test_asset["id"])

            if segments:
                self.console.print(f"   [green]OK - {len(segments)} segment(s) verified[/green]")
                for seg in segments:
                    start = seg.get("time_start_milliseconds", "N/A")
                    end = seg.get("time_end_milliseconds", "N/A")
                    self.console.print(f"     - {start}ms ~ {end}ms")
            else:
                self.console.print("   [yellow]Segment not visible (API delay?)[/yellow]")
        else:
            self.console.print(f"   [red]FAILED - Segment creation failed[/red]")
            self.console.print("\n[yellow]대안 테스트: 메타데이터 업데이트[/yellow]")
            self._test_metadata_update(test_asset["id"])

        self.iconik.close()

    def _test_metadata_update(self, asset_id: str) -> None:
        """메타데이터 업데이트 테스트 (세그먼트 실패 시 대안)."""
        view_id = self.settings.iconik.metadata_view_id

        if not view_id:
            self.console.print("   [red]ICONIK_METADATA_VIEW_ID가 설정되지 않음[/red]")
            return

        self.console.print(f"\n[bold]메타데이터 업데이트 테스트[/bold]")
        self.console.print(f"   Asset: {asset_id}")
        self.console.print(f"   View: {view_id}")

        # 테스트 메타데이터
        metadata = {
            "metadata_values": {
                "Description": {
                    "field_values": [{"value": "Test description from reverse sync"}]
                }
            }
        }

        try:
            response = self.iconik.client.put(
                f"/metadata/v1/assets/{asset_id}/views/{view_id}/",
                json=metadata
            )
            response.raise_for_status()
            self.console.print("   [green]OK - Metadata updated![/green]")
        except httpx.HTTPStatusError as e:
            self.console.print(f"   [red]HTTP Error: {e.response.status_code}[/red]")
            self.console.print(f"   Response: {e.response.text[:500]}")
        except Exception as e:
            self.console.print(f"   [red]Error: {e}[/red]")


def main() -> None:
    """Run reverse sync test."""
    tester = ReverseSyncTester()
    tester.run_test()


if __name__ == "__main__":
    main()

"""Iconik API Client."""

from typing import Any, Generator

import httpx
from rich.progress import Progress, TaskID

from config.settings import get_settings

from .exceptions import (
    IconikAPIError,
    IconikAuthError,
    IconikNotFoundError,
    IconikRateLimitError,
)
from .models import IconikAsset, IconikCollection, IconikPaginatedResponse


class IconikClient:
    """Iconik API client with pagination support."""

    def __init__(self) -> None:
        settings = get_settings()
        self.base_url = f"{settings.iconik.base_url}/API"
        self.headers = {
            "App-ID": settings.iconik.app_id,
            "Auth-Token": settings.iconik.auth_token,
            "Content-Type": "application/json",
        }
        self.timeout = settings.iconik.timeout
        self.per_page = settings.batch_size
        self._client: httpx.Client | None = None

    @property
    def client(self) -> httpx.Client:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.Client(
                base_url=self.base_url,
                headers=self.headers,
                timeout=self.timeout,
            )
        return self._client

    def close(self) -> None:
        """Close HTTP client."""
        if self._client is not None:
            self._client.close()
            self._client = None

    def __enter__(self) -> "IconikClient":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    def _get(
        self, endpoint: str, raise_for_404: bool = True, **kwargs: Any
    ) -> dict[str, Any] | None:
        """Make GET request with graceful error handling.

        Args:
            endpoint: API endpoint path
            raise_for_404: If False, return None on 404 instead of raising.
                          Useful for graceful handling of missing metadata.
            **kwargs: Additional request parameters (params, headers, etc.)

        Returns:
            Response JSON dict, or None if 404 and raise_for_404=False

        Raises:
            IconikNotFoundError: 404 (if raise_for_404=True)
            IconikAuthError: 401/403
            IconikRateLimitError: 429
            IconikAPIError: Other HTTP errors (4xx/5xx)
        """
        response = self.client.get(endpoint, **kwargs)

        if response.status_code == 404:
            if not raise_for_404:
                return None
            raise IconikNotFoundError(f"Not found: {endpoint}", status_code=404)

        if response.status_code in (401, 403):
            raise IconikAuthError(
                f"Auth error: {endpoint}", status_code=response.status_code
            )

        if response.status_code == 429:
            raise IconikRateLimitError(f"Rate limit: {endpoint}", status_code=429)

        if response.status_code >= 400:
            raise IconikAPIError(
                f"API error: {endpoint}", status_code=response.status_code
            )

        return response.json()

    def _put(self, endpoint: str, data: dict[str, Any]) -> dict[str, Any]:
        """Make PUT request.

        Args:
            endpoint: API endpoint path
            data: JSON data to send

        Returns:
            Response JSON dict

        Raises:
            IconikNotFoundError: 404
            IconikAuthError: 401/403
            IconikRateLimitError: 429
            IconikAPIError: Other HTTP errors (4xx/5xx)
        """
        response = self.client.put(endpoint, json=data)

        if response.status_code == 404:
            raise IconikNotFoundError(f"Not found: {endpoint}", status_code=404)

        if response.status_code in (401, 403):
            raise IconikAuthError(
                f"Auth error: {endpoint}", status_code=response.status_code
            )

        if response.status_code == 429:
            raise IconikRateLimitError(f"Rate limit: {endpoint}", status_code=429)

        if response.status_code >= 400:
            raise IconikAPIError(
                f"API error: {endpoint} - {response.text[:200]}",
                status_code=response.status_code,
            )

        return response.json()

    def _post(self, endpoint: str, data: dict[str, Any]) -> dict[str, Any]:
        """Make POST request.

        Args:
            endpoint: API endpoint path
            data: JSON data to send

        Returns:
            Response JSON dict

        Raises:
            IconikNotFoundError: 404
            IconikAuthError: 401/403
            IconikRateLimitError: 429
            IconikAPIError: Other HTTP errors (4xx/5xx)
        """
        response = self.client.post(endpoint, json=data)

        if response.status_code == 404:
            raise IconikNotFoundError(f"Not found: {endpoint}", status_code=404)

        if response.status_code in (401, 403):
            raise IconikAuthError(
                f"Auth error: {endpoint}", status_code=response.status_code
            )

        if response.status_code == 429:
            raise IconikRateLimitError(f"Rate limit: {endpoint}", status_code=429)

        if response.status_code >= 400:
            raise IconikAPIError(
                f"API error: {endpoint} - {response.text[:200]}",
                status_code=response.status_code,
            )

        return response.json()

    # Assets API
    def get_assets_page(self, page: int = 1, per_page: int | None = None) -> IconikPaginatedResponse:
        """Get a single page of assets."""
        params = {
            "page": page,
            "per_page": per_page or self.per_page,
        }
        data = self._get("/assets/v1/assets/", params=params)
        return IconikPaginatedResponse(**data)

    def get_all_assets(self, progress: Progress | None = None, task_id: TaskID | None = None) -> Generator[IconikAsset, None, None]:
        """Get all assets with pagination.

        Yields:
            IconikAsset objects one by one
        """
        page = 1
        total_pages = 1

        while page <= total_pages:
            response = self.get_assets_page(page=page)
            total_pages = response.pages

            if progress and task_id:
                progress.update(task_id, total=response.total, completed=min(page * response.per_page, response.total))

            for obj in response.objects:
                yield IconikAsset(**obj)

            page += 1

    def get_asset(self, asset_id: str) -> IconikAsset:
        """Get single asset by ID."""
        data = self._get(f"/assets/v1/assets/{asset_id}/")
        return IconikAsset(**data)

    # Metadata API
    def get_asset_metadata(
        self, asset_id: str, view_id: str, raise_for_404: bool = True
    ) -> dict[str, Any] | None:
        """Get asset metadata for a specific view.

        Args:
            asset_id: Asset UUID
            view_id: Metadata view UUID
            raise_for_404: If False, return None instead of raising on 404.
                          Useful for graceful handling when asset has no metadata
                          for this view.

        Returns:
            Metadata dict with metadata_values, or None if not found
        """
        return self._get(
            f"/metadata/v1/assets/{asset_id}/views/{view_id}/",
            raise_for_404=raise_for_404,
        )

    def get_metadata_views(self) -> list[dict[str, Any]]:
        """Get all metadata views.

        Returns:
            List of metadata view objects with id, name, description, view_fields
        """
        data = self._get("/metadata/v1/views/")
        return data.get("objects", [])

    def get_metadata_view(self, view_id: str) -> dict[str, Any]:
        """Get a single metadata view by ID.

        Args:
            view_id: Metadata view UUID

        Returns:
            View object with id, name, description, view_fields
        """
        return self._get(f"/metadata/v1/views/{view_id}/")

    def update_asset_metadata(
        self, asset_id: str, view_id: str, metadata_values: dict[str, Any]
    ) -> dict[str, Any]:
        """Update asset metadata for a specific view.

        Args:
            asset_id: Asset UUID
            view_id: Metadata view UUID
            metadata_values: Dict of field_name -> field_values
                Example: {"Description": {"field_values": [{"value": "test"}]}}

        Returns:
            Updated metadata response
        """
        data = {"metadata_values": metadata_values}
        return self._put(f"/metadata/v1/assets/{asset_id}/views/{view_id}/", data)

    # Segments API (timecodes for subclips)
    def get_asset_segments(
        self, asset_id: str, raise_for_404: bool = True
    ) -> list[dict[str, Any]]:
        """Get asset segments (timecodes for subclips).

        Args:
            asset_id: Asset UUID
            raise_for_404: If False, return empty list instead of raising on 404.
                          Most assets don't have segments, so this is often
                          the preferred behavior.

        Returns:
            List of segment objects with time_base, time_end, segment_type.
            Empty list if not found and raise_for_404=False.
        """
        result = self._get(
            f"/assets/v1/assets/{asset_id}/segments/",
            raise_for_404=raise_for_404,
        )
        if result is None:
            return []
        return result.get("objects", [])

    def create_asset_segment(
        self,
        asset_id: str,
        time_start_ms: int,
        time_end_ms: int,
        segment_type: str = "GENERIC",
        title: str | None = None,
    ) -> dict[str, Any]:
        """Create a segment (timecode) on an asset.

        Args:
            asset_id: Asset UUID
            time_start_ms: Start time in milliseconds
            time_end_ms: End time in milliseconds
            segment_type: MARKER, QC, GENERIC, COMMENT, TAG, TRANSCRIPTION, SCENE, PERSON
            title: Optional segment title

        Returns:
            Created segment data with id
        """
        data = {
            "time_start_milliseconds": time_start_ms,
            "time_end_milliseconds": time_end_ms,
            "segment_type": segment_type,
        }
        if title:
            data["title"] = title

        return self._post(f"/assets/v1/assets/{asset_id}/segments/", data)

    # Collections API
    def get_collections_page(self, page: int = 1, per_page: int | None = None) -> IconikPaginatedResponse:
        """Get a single page of collections."""
        params = {
            "page": page,
            "per_page": per_page or self.per_page,
        }
        data = self._get("/assets/v1/collections/", params=params)
        return IconikPaginatedResponse(**data)

    def get_all_collections(self) -> Generator[IconikCollection, None, None]:
        """Get all collections with pagination."""
        page = 1
        total_pages = 1

        while page <= total_pages:
            response = self.get_collections_page(page=page)
            total_pages = response.pages

            for obj in response.objects:
                yield IconikCollection(**obj)

            page += 1

    # Health check
    def health_check(self) -> bool:
        """Check API connection."""
        try:
            self._get("/files/v1/storages/")
            return True
        except Exception:
            return False

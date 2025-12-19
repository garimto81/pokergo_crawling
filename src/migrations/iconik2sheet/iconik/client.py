"""Iconik API Client."""

from typing import Any, Generator

import httpx
from rich.progress import Progress, TaskID

from config.settings import get_settings

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

    def _get(self, endpoint: str, **kwargs: Any) -> dict[str, Any]:
        """Make GET request."""
        response = self.client.get(endpoint, **kwargs)
        response.raise_for_status()
        return response.json()

    # Assets API
    def get_assets_page(self, page: int = 1, per_page: int | None = None) -> IconikPaginatedResponse:
        """Get a single page of assets."""
        params = {
            "page": page,
            "per_page": per_page or self.per_page,
            "sort": "created_at",
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
    def get_asset_metadata(self, asset_id: str, view_id: str) -> dict[str, Any]:
        """Get asset metadata for a specific view."""
        return self._get(f"/metadata/v1/assets/{asset_id}/views/{view_id}/")

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

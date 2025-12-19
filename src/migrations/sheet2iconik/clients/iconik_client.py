"""Iconik API Client."""

from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from config.settings import get_settings


class IconikClient:
    """Iconik API client with retry logic."""

    def __init__(self) -> None:
        settings = get_settings()
        self.base_url = f"{settings.iconik.base_url}/API"
        self.headers = {
            "App-ID": settings.iconik.app_id,
            "Auth-Token": settings.iconik.auth_token,
            "Content-Type": "application/json",
        }
        self.timeout = settings.iconik.timeout
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

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=30),
        reraise=True,
    )
    def _request(self, method: str, endpoint: str, **kwargs: Any) -> dict[str, Any]:
        """Make HTTP request with retry."""
        response = self.client.request(method, endpoint, **kwargs)
        response.raise_for_status()
        return response.json()

    # Assets API
    def create_asset(self, data: dict[str, Any]) -> dict[str, Any]:
        """Create a new asset."""
        return self._request("POST", "/assets/v1/assets/", json=data)

    def get_asset(self, asset_id: str) -> dict[str, Any]:
        """Get asset by ID."""
        return self._request("GET", f"/assets/v1/assets/{asset_id}/")

    def search_assets(self, query: dict[str, Any]) -> dict[str, Any]:
        """Search assets."""
        return self._request("POST", "/search/v1/search/", json=query)

    # Metadata API
    def set_metadata(self, asset_id: str, view_id: str, data: dict[str, Any]) -> dict[str, Any]:
        """Set asset metadata."""
        return self._request("PUT", f"/metadata/v1/assets/{asset_id}/views/{view_id}/", json=data)

    def get_metadata(self, asset_id: str, view_id: str) -> dict[str, Any]:
        """Get asset metadata."""
        return self._request("GET", f"/metadata/v1/assets/{asset_id}/views/{view_id}/")

    # Collections API
    def create_collection(self, data: dict[str, Any]) -> dict[str, Any]:
        """Create a new collection."""
        return self._request("POST", "/assets/v1/collections/", json=data)

    def get_collections(self, per_page: int = 100, page: int = 1) -> dict[str, Any]:
        """Get collections list."""
        return self._request("GET", "/assets/v1/collections/", params={"per_page": per_page, "page": page})

    def add_to_collection(self, collection_id: str, asset_ids: list[str]) -> dict[str, Any]:
        """Add assets to collection."""
        data = {"object_ids": asset_ids}
        return self._request("PUT", f"/assets/v1/collections/{collection_id}/contents/", json=data)

    # Health check
    def health_check(self) -> bool:
        """Check API connection."""
        try:
            self._request("GET", "/files/v1/storages/")
            return True
        except Exception:
            return False

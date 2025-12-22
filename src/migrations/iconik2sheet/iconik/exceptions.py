"""Iconik API exceptions for graceful error handling."""


class IconikAPIError(Exception):
    """Base Iconik API error.

    All Iconik-specific errors inherit from this class.
    """

    def __init__(self, message: str, status_code: int | None = None) -> None:
        self.status_code = status_code
        super().__init__(message)


class IconikNotFoundError(IconikAPIError):
    """404 Not Found - asset, metadata view, or resource doesn't exist.

    This error is commonly raised when:
    - An asset doesn't have metadata for the specified view
    - The view_id is incorrect or not associated with the asset
    - The asset or resource doesn't exist
    """

    pass


class IconikAuthError(IconikAPIError):
    """401/403 Authentication or Authorization error.

    Raised when:
    - App-ID or Auth-Token is invalid (401)
    - User doesn't have permission to access the resource (403)
    """

    pass


class IconikRateLimitError(IconikAPIError):
    """429 Too Many Requests.

    Raised when the API rate limit is exceeded.
    Consider implementing retry with exponential backoff.
    """

    pass

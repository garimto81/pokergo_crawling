"""Shared pytest fixtures for Iconik2Sheet tests."""

import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# ============ Environment Check ============


@pytest.fixture(scope="session")
def env_check():
    """Check if environment variables are set for integration tests."""
    from dotenv import load_dotenv

    # Load .env.local if exists
    env_local = PROJECT_ROOT / ".env.local"
    if env_local.exists():
        load_dotenv(env_local)

    required = ["ICONIK_APP_ID", "ICONIK_AUTH_TOKEN"]
    missing = [v for v in required if not os.getenv(v)]
    return {"missing": missing, "valid": len(missing) == 0}


# ============ Fixture Files ============


@pytest.fixture
def fixtures_dir() -> Path:
    """Path to fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_asset(fixtures_dir) -> dict:
    """Load sample asset JSON."""
    with open(fixtures_dir / "sample_asset.json", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def sample_metadata(fixtures_dir) -> dict:
    """Load sample metadata JSON."""
    with open(fixtures_dir / "sample_metadata.json", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def sample_segments(fixtures_dir) -> dict:
    """Load sample segments JSON."""
    with open(fixtures_dir / "sample_segments.json", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def sample_metadata_views() -> dict:
    """Sample metadata views response."""
    return {
        "objects": [
            {"id": "view-001-uuid", "name": "Poker Hand Metadata", "description": "WSOP clips metadata"},
            {"id": "view-002-uuid", "name": "Default View", "description": "System default"},
        ],
        "page": 1,
        "pages": 1,
        "per_page": 100,
        "total": 2,
    }


@pytest.fixture
def sample_paginated_assets(sample_asset) -> dict:
    """Sample paginated assets response."""
    return {
        "objects": [sample_asset],
        "page": 1,
        "pages": 1,
        "per_page": 100,
        "total": 1,
        "first_id": sample_asset["id"],
        "last_id": sample_asset["id"],
    }


# ============ Mock Settings ============


@pytest.fixture
def mock_iconik_settings():
    """Mock IconikSettings for unit tests."""
    settings = MagicMock()
    settings.app_id = "test-app-id"
    settings.auth_token = "test-auth-token"
    settings.base_url = "https://app.iconik.io"
    settings.timeout = 30
    settings.max_retries = 3
    settings.metadata_view_id = "test-view-id"
    return settings


@pytest.fixture
def mock_sheets_settings():
    """Mock GoogleSheetsSettings for unit tests."""
    settings = MagicMock()
    settings.service_account_path = "/fake/path/service_account.json"
    settings.spreadsheet_id = "test-spreadsheet-id"
    return settings


@pytest.fixture
def mock_settings(mock_iconik_settings, mock_sheets_settings):
    """Mock full Settings for unit tests."""
    settings = MagicMock()
    settings.iconik = mock_iconik_settings
    settings.sheets = mock_sheets_settings
    settings.state_file = "data/sync_state.json"
    settings.batch_size = 100
    settings.rate_limit_per_sec = 50
    return settings


# ============ Integration Test Fixtures ============


@pytest.fixture
def iconik_client(env_check):
    """Real IconikClient for integration tests.

    Requires valid credentials in .env.local
    """
    if not env_check["valid"]:
        pytest.skip(f"Missing env vars: {env_check['missing']}")

    # Clear settings cache to ensure fresh load from .env.local
    from config.settings import get_settings

    get_settings.cache_clear()

    from iconik.client import IconikClient

    client = IconikClient()
    yield client
    client.close()


@pytest.fixture
def sheets_writer(env_check):
    """Real SheetsWriter for integration tests."""
    google_vars = ["GOOGLE_SERVICE_ACCOUNT_PATH", "GOOGLE_SPREADSHEET_ID"]
    missing = [v for v in google_vars if not os.getenv(v)]

    if missing:
        pytest.skip(f"Missing Google env vars: {missing}")

    from sheets.writer import SheetsWriter

    return SheetsWriter()


# ============ Pytest Markers ============


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "integration: mark test as integration test (requires API credentials)")
    config.addinivalue_line("markers", "slow: mark test as slow running")

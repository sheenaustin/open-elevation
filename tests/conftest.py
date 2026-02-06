"""Shared test fixtures."""

import shutil
from pathlib import Path

import pytest

from open_elevation.config import Settings
from open_elevation.elevation.service import ElevationService

FIXTURES_DIR = Path(__file__).parent / "fixtures"
TEST_TIF = FIXTURES_DIR / "test_elevation.tif"


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    """Create test settings pointing at a temporary directory."""
    return Settings(
        tif_directory=str(tmp_path),
        index_directory=str(tmp_path / "index"),
        cache_max_size=100,
        max_workers=2,
    )


@pytest.fixture
def tif_settings(tmp_path: Path) -> Settings:
    """Create settings with the test TIF file copied into a temp directory."""
    tif_dir = tmp_path / "tif_files"
    tif_dir.mkdir()
    shutil.copy(TEST_TIF, tif_dir / "test_elevation.tif")
    return Settings(
        tif_directory=str(tif_dir),
        index_directory=str(tmp_path / "index"),
        cache_max_size=100,
        max_workers=2,
    )


@pytest.fixture
def elevation_service(tif_settings: Settings) -> ElevationService:
    """Create an ElevationService with a real spatial index built from the test TIF."""
    service = ElevationService(tif_settings)
    service.build_or_load_index()
    yield service  # type: ignore[misc]
    service.shutdown()

"""End-to-end integration tests using a real GeoTIFF fixture.

The test fixture is a 10x10 pixel GeoTIFF covering:
    - Longitude: 0.0 to 1.0
    - Latitude:  50.0 to 51.0
    - Pixel size: 0.1 degrees
    - Elevation: west-to-east gradient from 100m to 190m (10m steps per column)

Column index -> elevation mapping:
    col 0 (lon 0.0-0.1)  = 100m
    col 1 (lon 0.1-0.2)  = 110m
    col 5 (lon 0.5-0.6)  = 150m
    col 9 (lon 0.9-1.0)  = 190m
"""

import pytest

from open_elevation.elevation.service import ElevationService
from open_elevation.exceptions import ElevationNotFoundError


class TestGetElevation:
    """Test the full rasterio lookup pipeline with a real TIF file."""

    def test_returns_elevation_at_center(
        self, elevation_service: ElevationService
    ) -> None:
        elevation = elevation_service.get_elevation(latitude=50.5, longitude=0.55)

        assert elevation == 150.0

    def test_returns_elevation_at_top_left(
        self, elevation_service: ElevationService
    ) -> None:
        elevation = elevation_service.get_elevation(latitude=50.95, longitude=0.05)

        assert elevation == 100.0

    def test_returns_elevation_at_bottom_right(
        self, elevation_service: ElevationService
    ) -> None:
        elevation = elevation_service.get_elevation(latitude=50.05, longitude=0.95)

        assert elevation == 190.0

    def test_returns_different_values_across_gradient(
        self, elevation_service: ElevationService
    ) -> None:
        west = elevation_service.get_elevation(latitude=50.5, longitude=0.05)
        east = elevation_service.get_elevation(latitude=50.5, longitude=0.85)

        assert west == 100.0
        assert east == 180.0
        assert east > west

    def test_raises_not_found_for_coordinates_outside_tif(
        self, elevation_service: ElevationService
    ) -> None:
        with pytest.raises(ElevationNotFoundError):
            elevation_service.get_elevation(latitude=40.0, longitude=10.0)

    def test_caches_repeated_lookups(
        self, elevation_service: ElevationService
    ) -> None:
        first = elevation_service.get_elevation(latitude=50.5, longitude=0.55)
        second = elevation_service.get_elevation(latitude=50.5, longitude=0.55)

        assert first == second == 150.0


class TestProcessLocationEndToEnd:
    """Test the full process_location pipeline with real TIF data."""

    def test_returns_correct_result(
        self, elevation_service: ElevationService
    ) -> None:
        result = elevation_service.process_location("50.5,0.55")

        assert result.latitude == 50.5
        assert result.longitude == 0.55
        assert result.elevation == 150.0

    def test_returns_correct_result_with_different_coordinate(
        self, elevation_service: ElevationService
    ) -> None:
        result = elevation_service.process_location("50.95,0.05")

        assert result.latitude == 50.95
        assert result.longitude == 0.05
        assert result.elevation == 100.0

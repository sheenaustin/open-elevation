"""Tests for the elevation service."""

from unittest.mock import patch

import pytest

from open_elevation.config import Settings
from open_elevation.elevation.service import ElevationService
from open_elevation.exceptions import InvalidCoordinateError


@pytest.fixture
def service(settings: Settings) -> ElevationService:
    """Create an ElevationService with test settings."""
    return ElevationService(settings)


class TestProcessLocation:
    def test_parses_valid_location(self, service: ElevationService) -> None:
        with patch.object(service, "get_elevation", return_value=100.0):
            result = service.process_location("51.5,-0.1")

        assert result.latitude == 51.5
        assert result.longitude == -0.1
        assert result.elevation == 100.0

    def test_handles_whitespace(self, service: ElevationService) -> None:
        with patch.object(service, "get_elevation", return_value=50.0):
            result = service.process_location(" 48.8 , 2.3 ")

        assert result.latitude == 48.8
        assert result.longitude == 2.3

    def test_rejects_invalid_format(self, service: ElevationService) -> None:
        with pytest.raises(InvalidCoordinateError, match="Invalid location format"):
            service.process_location("not-a-coordinate")

    def test_rejects_single_value(self, service: ElevationService) -> None:
        with pytest.raises(InvalidCoordinateError, match="Invalid location format"):
            service.process_location("51.5")

    def test_rejects_latitude_out_of_range(self, service: ElevationService) -> None:
        with pytest.raises(InvalidCoordinateError, match="Invalid latitude"):
            service.process_location("91.0,0.0")

    def test_rejects_negative_latitude_out_of_range(self, service: ElevationService) -> None:
        with pytest.raises(InvalidCoordinateError, match="Invalid latitude"):
            service.process_location("-91.0,0.0")

    def test_rejects_longitude_out_of_range(self, service: ElevationService) -> None:
        with pytest.raises(InvalidCoordinateError, match="Invalid longitude"):
            service.process_location("0.0,181.0")

    def test_rejects_negative_longitude_out_of_range(self, service: ElevationService) -> None:
        with pytest.raises(InvalidCoordinateError, match="Invalid longitude"):
            service.process_location("0.0,-181.0")

    def test_accepts_boundary_latitude(self, service: ElevationService) -> None:
        with patch.object(service, "get_elevation", return_value=0.0):
            result_north = service.process_location("90.0,0.0")
            result_south = service.process_location("-90.0,0.0")

        assert result_north.latitude == 90.0
        assert result_south.latitude == -90.0

    def test_accepts_boundary_longitude(self, service: ElevationService) -> None:
        with patch.object(service, "get_elevation", return_value=0.0):
            result_east = service.process_location("0.0,180.0")
            result_west = service.process_location("0.0,-180.0")

        assert result_east.longitude == 180.0
        assert result_west.longitude == -180.0


class TestBuildOrLoadIndex:
    def test_raises_when_tif_directory_missing(self, service: ElevationService) -> None:
        service._settings = Settings(
            tif_directory="/nonexistent/path",
            index_directory="/nonexistent/index",
            cache_max_size=100,
            max_workers=2,
        )

        with pytest.raises(Exception, match="TIF directory not found"):
            service.build_or_load_index()

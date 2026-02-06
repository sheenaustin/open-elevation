"""Tests for elevation schemas."""

import pytest
from pydantic import ValidationError

from open_elevation.elevation.schemas import ElevationResult, LookupResponse


class TestElevationResult:
    def test_valid_result(self) -> None:
        result = ElevationResult(latitude=51.5, longitude=-0.1, elevation=11.0)

        assert result.latitude == 51.5
        assert result.longitude == -0.1
        assert result.elevation == 11.0

    def test_negative_elevation(self) -> None:
        result = ElevationResult(latitude=31.5, longitude=35.5, elevation=-430.0)

        assert result.elevation == -430.0

    def test_rejects_missing_fields(self) -> None:
        with pytest.raises(ValidationError):
            ElevationResult(latitude=51.5, longitude=-0.1)  # type: ignore[call-arg]


class TestLookupResponse:
    def test_empty_results(self) -> None:
        response = LookupResponse(results=[])

        assert response.results == []

    def test_multiple_results(self) -> None:
        results = [
            ElevationResult(latitude=51.5, longitude=-0.1, elevation=11.0),
            ElevationResult(latitude=48.8, longitude=2.3, elevation=35.0),
        ]

        response = LookupResponse(results=results)

        assert len(response.results) == 2
        assert response.results[0].latitude == 51.5
        assert response.results[1].latitude == 48.8

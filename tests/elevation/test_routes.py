"""Functional tests for the elevation API routes."""

from collections.abc import Generator
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from open_elevation.elevation.schemas import ElevationResult
from open_elevation.elevation.service import ElevationService
from open_elevation.exceptions import ElevationNotFoundError, ElevationReadError
from open_elevation.main import app


@pytest.fixture
def mock_service() -> Generator[MagicMock, None, None]:
    """Create a mock ElevationService with a real executor."""
    service = MagicMock(spec=ElevationService)
    executor = ThreadPoolExecutor(max_workers=2)
    service.executor = executor
    yield service
    executor.shutdown(wait=False)


@pytest.fixture
def client(mock_service: MagicMock) -> TestClient:
    """Create a TestClient with the mocked service injected."""
    app.state.elevation_service = mock_service
    return TestClient(app, raise_server_exceptions=False)


class TestLookupEndpoint:
    def test_returns_elevation_for_single_location(
        self, client: TestClient, mock_service: MagicMock
    ) -> None:
        mock_service.process_location.return_value = ElevationResult(
            latitude=51.5, longitude=-0.1, elevation=11.0
        )

        response = client.get("/api/v1/lookup", params={"locations": "51.5,-0.1"})

        assert response.status_code == 200
        body = response.json()
        assert len(body["results"]) == 1
        assert body["results"][0]["latitude"] == 51.5
        assert body["results"][0]["longitude"] == -0.1
        assert body["results"][0]["elevation"] == 11.0

    def test_returns_elevation_for_multiple_locations(
        self, client: TestClient, mock_service: MagicMock
    ) -> None:
        mock_service.process_location.side_effect = [
            ElevationResult(latitude=51.5, longitude=-0.1, elevation=11.0),
            ElevationResult(latitude=48.8, longitude=2.3, elevation=35.0),
        ]

        response = client.get(
            "/api/v1/lookup",
            params={"locations": ["51.5,-0.1", "48.8,2.3"]},
        )

        assert response.status_code == 200
        body = response.json()
        assert len(body["results"]) == 2

    def test_returns_400_for_invalid_coordinates(
        self, client: TestClient, mock_service: MagicMock
    ) -> None:
        mock_service.process_location.side_effect = ElevationNotFoundError(
            latitude=999.0, longitude=999.0
        )

        response = client.get("/api/v1/lookup", params={"locations": "999,999"})

        assert response.status_code == 404

    def test_returns_404_when_elevation_not_found(
        self, client: TestClient, mock_service: MagicMock
    ) -> None:
        mock_service.process_location.side_effect = ElevationNotFoundError(
            latitude=0.0, longitude=0.0
        )

        response = client.get("/api/v1/lookup", params={"locations": "0.0,0.0"})

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_returns_500_on_read_error(
        self, client: TestClient, mock_service: MagicMock
    ) -> None:
        mock_service.process_location.side_effect = ElevationReadError(
            "Corrupt raster file"
        )

        response = client.get("/api/v1/lookup", params={"locations": "51.5,-0.1"})

        assert response.status_code == 500
        assert "Corrupt raster file" in response.json()["detail"]

    def test_returns_422_when_no_locations_param(self, client: TestClient) -> None:
        response = client.get("/api/v1/lookup")

        assert response.status_code == 422

    def test_response_shape_matches_schema(
        self, client: TestClient, mock_service: MagicMock
    ) -> None:
        mock_service.process_location.return_value = ElevationResult(
            latitude=10.0, longitude=20.0, elevation=500.0
        )

        response = client.get("/api/v1/lookup", params={"locations": "10.0,20.0"})

        body = response.json()
        assert "results" in body
        result = body["results"][0]
        assert set(result.keys()) == {"latitude", "longitude", "elevation"}

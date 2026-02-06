"""Pydantic schemas for elevation API requests and responses."""

from pydantic import BaseModel


class ElevationResult(BaseModel):
    """Elevation data for a single coordinate pair."""

    latitude: float
    longitude: float
    elevation: float


class LookupResponse(BaseModel):
    """Response schema for the elevation lookup endpoint."""

    results: list[ElevationResult]

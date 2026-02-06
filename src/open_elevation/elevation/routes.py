"""API routes for elevation lookups."""

import asyncio
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from open_elevation.elevation.schemas import LookupResponse
from open_elevation.elevation.service import ElevationService
from open_elevation.exceptions import (
    ElevationNotFoundError,
    ElevationReadError,
    InvalidCoordinateError,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["elevation"])


def get_elevation_service(request: Request) -> ElevationService:
    """FastAPI dependency that retrieves the ElevationService from app state."""
    service: ElevationService = request.app.state.elevation_service
    return service


@router.get("/lookup", response_model=LookupResponse, summary="Look up elevation data")
async def lookup(
    locations: Annotated[list[str], Query(...)],
    service: Annotated[ElevationService, Depends(get_elevation_service)],
) -> LookupResponse:
    """Look up elevation for one or more 'latitude,longitude' pairs.

    Args:
        locations: Query parameters in 'lat,lon' format.
        service: Injected ElevationService instance.

    Returns:
        A LookupResponse containing elevation results for each location.
    """
    if not locations:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No locations provided",
        )

    loop = asyncio.get_running_loop()
    tasks = [
        loop.run_in_executor(service.executor, service.process_location, location)
        for location in locations
    ]

    try:
        results = await asyncio.gather(*tasks)
    except InvalidCoordinateError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except ElevationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except ElevationReadError as exc:
        logger.error("Elevation read error during lookup", extra={"error": str(exc)})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    return LookupResponse(results=list(results))

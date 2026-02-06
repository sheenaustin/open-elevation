"""FastAPI application entry point."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from open_elevation.config import Settings
from open_elevation.elevation.routes import router
from open_elevation.elevation.service import ElevationService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage application startup and shutdown.

    Builds or loads the spatial index on startup and shuts down
    the thread pool executor on teardown.
    """
    settings = Settings.from_env()
    service = ElevationService(settings)
    service.build_or_load_index()
    app.state.elevation_service = service
    logger.info("Elevation service initialized")
    yield
    service.shutdown()
    logger.info("Elevation service shut down")


app = FastAPI(title="Open Elevation API", lifespan=lifespan)
app.include_router(router)

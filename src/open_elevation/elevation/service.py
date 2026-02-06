"""Elevation lookup service backed by GeoTIFF files and a spatial index."""

import logging
import os
from concurrent.futures import ThreadPoolExecutor

import rasterio
from cachetools import LRUCache
from rasterio.windows import Window
from rtree import index

from open_elevation.config import Settings
from open_elevation.elevation.schemas import ElevationResult
from open_elevation.exceptions import (
    ElevationNotFoundError,
    ElevationReadError,
    IndexBuildError,
    InvalidCoordinateError,
)

logger = logging.getLogger(__name__)


class ElevationService:
    """Service for querying elevation data from indexed GeoTIFF files.

    Manages a spatial index (backed by rtree) for fast coordinate-to-file
    lookups, an LRU cache for repeat queries, and a thread pool for
    concurrent blocking I/O.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._cache: LRUCache[tuple[float, float], float] = LRUCache(
            maxsize=settings.cache_max_size,
        )
        self._executor = ThreadPoolExecutor(max_workers=settings.max_workers)
        self._spatial_index: index.Index | None = None
        self._index_counter: int = 0

    @property
    def executor(self) -> ThreadPoolExecutor:
        """Thread pool executor for running blocking I/O in async contexts."""
        return self._executor

    def build_or_load_index(self) -> None:
        """Build a new spatial index or load an existing one from disk.

        Raises:
            IndexBuildError: If the TIF directory does not exist.
        """
        tif_directory = self._settings.tif_directory
        index_directory = self._settings.index_directory

        if not os.path.exists(tif_directory):
            raise IndexBuildError(f"TIF directory not found: {tif_directory}")

        os.makedirs(index_directory, exist_ok=True)
        index_path = os.path.join(index_directory, "spatial_index")

        properties = index.Property()
        properties.storage = index.RT_Disk
        properties.overwrite = False

        if os.path.exists(index_path + ".dat"):
            logger.info("Loading existing spatial index from disk")
            self._spatial_index = index.Index(index_path, properties=properties)
        else:
            logger.info("Building spatial index from scratch")
            self._spatial_index = index.Index(index_path, properties=properties)
            self._index_tif_files(tif_directory)

    def _index_tif_files(self, directory: str) -> None:
        """Walk a directory tree and insert all .tif files into the spatial index."""
        if self._spatial_index is None:
            raise IndexBuildError("Spatial index not initialized")

        for root, _, files in os.walk(directory):
            for filename in files:
                if not filename.endswith(".tif"):
                    continue
                filepath = os.path.join(root, filename)
                try:
                    with rasterio.open(filepath) as src:
                        bounds = src.bounds
                        self._index_counter += 1
                        self._spatial_index.insert(
                            self._index_counter,
                            (bounds.left, bounds.bottom, bounds.right, bounds.top),
                            obj=filepath,
                        )
                        logger.info(
                            "Indexed TIF file",
                            extra={"tif_name": filename, "tif_path": filepath},
                        )
                except rasterio.RasterioIOError as exc:
                    logger.error(
                        "Failed to index TIF file",
                        extra={"tif_name": filename, "error": str(exc)},
                    )

    def get_elevation(self, latitude: float, longitude: float) -> float:
        """Look up the elevation at a given coordinate.

        Args:
            latitude: Latitude in decimal degrees (-90 to 90).
            longitude: Longitude in decimal degrees (-180 to 180).

        Returns:
            Elevation value in meters.

        Raises:
            IndexBuildError: If the spatial index has not been initialized.
            ElevationReadError: If reading the raster data fails.
            ElevationNotFoundError: If no TIF file covers the coordinate.
        """
        cache_key = (latitude, longitude)
        if cache_key in self._cache:
            return self._cache[cache_key]

        if self._spatial_index is None:
            raise IndexBuildError("Spatial index not initialized")

        matches = list(
            self._spatial_index.intersection(
                (longitude, latitude, longitude, latitude),
                objects=True,
            )
        )

        for match in matches:
            tif_file = str(match.object)
            try:
                with rasterio.open(tif_file) as dataset:
                    row, col = dataset.index(longitude, latitude)
                    # Windowed read: fetch only the single pixel instead of the full band
                    window = Window(col, row, 1, 1)
                    elevation_value = dataset.read(1, window=window)[0, 0]
                    elevation = float(elevation_value)
                    self._cache[cache_key] = elevation
                    return elevation
            except rasterio.RasterioIOError as exc:
                logger.error(
                    "Error reading elevation data",
                    extra={"tif_file": tif_file, "error": str(exc)},
                )
                raise ElevationReadError(f"Error reading elevation from {tif_file}") from exc

        raise ElevationNotFoundError(latitude, longitude)

    def process_location(self, location: str) -> ElevationResult:
        """Parse a 'lat,lon' string and return the elevation result.

        Args:
            location: Comma-separated latitude and longitude, e.g. '51.5,-0.1'.

        Returns:
            An ElevationResult with the coordinates and elevation.

        Raises:
            InvalidCoordinateError: If the format is wrong or values are out of range.
            ElevationNotFoundError: If no data covers the coordinate.
            ElevationReadError: If reading the raster data fails.
        """
        try:
            lat_str, lon_str = location.split(",")
            latitude = float(lat_str.strip())
            longitude = float(lon_str.strip())
        except ValueError as exc:
            raise InvalidCoordinateError(
                f"Invalid location format: '{location}'. Expected 'latitude,longitude'."
            ) from exc

        if not (-90 <= latitude <= 90):
            raise InvalidCoordinateError(
                f"Invalid latitude: {latitude}. Must be between -90 and 90."
            )
        if not (-180 <= longitude <= 180):
            raise InvalidCoordinateError(
                f"Invalid longitude: {longitude}. Must be between -180 and 180."
            )

        elevation = self.get_elevation(latitude, longitude)
        return ElevationResult(
            latitude=latitude,
            longitude=longitude,
            elevation=elevation,
        )

    def shutdown(self) -> None:
        """Shut down the thread pool executor."""
        self._executor.shutdown(wait=False)

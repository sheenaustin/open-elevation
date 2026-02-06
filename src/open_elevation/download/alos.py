"""Download and extract ALOS World 3D elevation tiles.

Run directly:
    python -m open_elevation.download.alos [destination_folder]
"""

import logging
import os
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

logger = logging.getLogger(__name__)

TILE_STEP = 5
BASE_URL = "https://www.eorc.jaxa.jp/ALOS/aw3d30/data/release_v2404/"
DEFAULT_DESTINATION = "tif_files"
MAX_DOWNLOAD_THREADS = 100
MIN_VALID_ZIP_SIZE_BYTES = 4096
REQUEST_TIMEOUT_SECONDS = 60


def generate_all_tiles(*, step: int = TILE_STEP) -> list[str]:
    """Generate all ALOS tile names for the global grid.

    Args:
        step: Grid step size in degrees.

    Returns:
        A list of tile name strings such as 'N060W005_N065E000'.
    """
    tile_names: list[str] = []

    for lat in range(85, -90, -step):
        for lon in range(-180, 180, step):
            start_lat = f"N{abs(lat):03d}" if lat >= 0 else f"S{abs(lat):03d}"
            start_lon = f"W{abs(lon):03d}" if lon < 0 else f"E{abs(lon):03d}"

            end_lat_val = lat + step
            end_lat = (
                f"N{abs(end_lat_val):03d}"
                if end_lat_val <= 90 and end_lat_val > 0
                else f"S{abs(end_lat_val):03d}"
            )
            end_lon_val = lon + step
            end_lon = (
                f"W{abs(end_lon_val):03d}" if end_lon_val <= 0 else f"E{abs(end_lon_val):03d}"
            )

            tile_names.append(f"{start_lat}{start_lon}_{end_lat}{end_lon}")

    return tile_names


def _safe_extract(zip_file: zipfile.ZipFile, destination: str) -> None:
    """Extract zip contents after verifying no path traversal.

    Args:
        zip_file: An opened ZipFile instance.
        destination: Target extraction directory.

    Raises:
        ValueError: If an archive member attempts path traversal.
    """
    dest = os.path.realpath(destination)
    for member in zip_file.namelist():
        member_path = os.path.realpath(os.path.join(dest, member))
        if not member_path.startswith(dest + os.sep) and member_path != dest:
            raise ValueError(f"Attempted path traversal in zip: {member}")
    zip_file.extractall(destination)


def download_and_extract_tile(tile_name: str, destination_folder: str) -> None:
    """Download a single tile archive and extract it.

    Skips files smaller than 4 KB (empty/invalid tiles from the server).

    Args:
        tile_name: The ALOS tile identifier.
        destination_folder: Directory to save and extract into.
    """
    url = f"{BASE_URL}{tile_name}.zip"
    zip_path = os.path.join(destination_folder, f"{tile_name}.zip")
    extract_path = os.path.join(destination_folder, tile_name)

    try:
        logger.info("Downloading tile", extra={"url": url})
        response = requests.get(url, stream=True, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()

        with open(zip_path, "wb") as file_handle:
            for chunk in response.iter_content(chunk_size=8192):
                file_handle.write(chunk)

        if os.path.getsize(zip_path) < MIN_VALID_ZIP_SIZE_BYTES:
            logger.warning(
                "Tile zip too small, removing",
                extra={"tile": tile_name, "path": zip_path},
            )
            os.remove(zip_path)
            return

        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            _safe_extract(zip_ref, extract_path)
        logger.info("Extracted tile", extra={"tile": tile_name, "path": extract_path})

        os.remove(zip_path)

    except requests.exceptions.RequestException as exc:
        logger.error("Failed to download tile", extra={"tile": tile_name, "error": str(exc)})
    except zipfile.BadZipFile:
        logger.error("Invalid zip archive", extra={"tile": tile_name})
        if os.path.exists(zip_path):
            os.remove(zip_path)


def download_all_tiles(
    destination_folder: str = DEFAULT_DESTINATION,
    *,
    max_threads: int = MAX_DOWNLOAD_THREADS,
) -> None:
    """Download and extract all ALOS tiles concurrently.

    Args:
        destination_folder: Root directory for downloaded data.
        max_threads: Maximum number of concurrent download threads.
    """
    os.makedirs(destination_folder, exist_ok=True)
    all_tiles = generate_all_tiles()

    with ThreadPoolExecutor(max_workers=max_threads) as executor:
        future_to_tile = {
            executor.submit(download_and_extract_tile, tile, destination_folder): tile
            for tile in all_tiles
        }

        for future in as_completed(future_to_tile):
            tile = future_to_tile[future]
            try:
                future.result()
            except Exception:
                logger.exception("Unexpected error processing tile", extra={"tile": tile})


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    )
    download_all_tiles()

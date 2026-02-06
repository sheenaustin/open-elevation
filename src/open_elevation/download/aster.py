"""Download and extract ASTER GDEM elevation tiles.

Run directly:
    python -m open_elevation.download.aster [destination_folder]
"""

import logging
import os
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

logger = logging.getLogger(__name__)

BASE_URL = "https://gdemdl.aster.jspacesystems.or.jp/download/Download_"
DEFAULT_DOWNLOAD_FOLDER = "/dev/shm/ASTER_GDE"  # noqa: S108 — intentional tmpfs for fast I/O
DEFAULT_UNZIP_FOLDER = "tif_files"
MAX_DOWNLOAD_THREADS = 100
NORTH_LATITUDE_RANGE = range(0, 83)
SOUTH_LATITUDE_RANGE = range(0, 83)
WEST_LONGITUDE_RANGE = range(0, 181)
EAST_LONGITUDE_RANGE = range(0, 181)
REQUEST_TIMEOUT_SECONDS = 30


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


def recursive_unzip(zip_path: str, extract_to: str) -> None:
    """Unzip a file and recursively extract any nested zip archives.

    Args:
        zip_path: Path to the zip file to extract.
        extract_to: Destination directory for extracted contents.
    """
    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        _safe_extract(zip_ref, extract_to)
    os.remove(zip_path)

    for root, _, files in os.walk(extract_to):
        for filename in files:
            if filename.endswith(".zip"):
                nested_zip_path = os.path.join(root, filename)
                nested_extract_to = os.path.splitext(nested_zip_path)[0]
                os.makedirs(nested_extract_to, exist_ok=True)
                recursive_unzip(nested_zip_path, nested_extract_to)


def download_and_unzip(
    lat_str: str,
    lon_str: str,
    *,
    download_folder: str = DEFAULT_DOWNLOAD_FOLDER,
    unzip_folder: str = DEFAULT_UNZIP_FOLDER,
) -> None:
    """Download and recursively extract a single ASTER tile.

    Args:
        lat_str: Latitude identifier, e.g. 'N45'.
        lon_str: Longitude identifier, e.g. 'W090'.
        download_folder: Temporary download directory.
        unzip_folder: Final extraction directory.
    """
    url = f"{BASE_URL}{lat_str}{lon_str}.zip"
    zip_path = os.path.join(download_folder, f"{lat_str}{lon_str}.zip")
    extract_path = os.path.join(unzip_folder, f"{lat_str}{lon_str}")

    try:
        response = requests.get(url, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()

        with open(zip_path, "wb") as file_handle:
            file_handle.write(response.content)

        os.makedirs(extract_path, exist_ok=True)
        recursive_unzip(zip_path, extract_path)

        logger.info(
            "Downloaded and extracted tile",
            extra={"lat": lat_str, "lon": lon_str},
        )
    except requests.exceptions.RequestException as exc:
        logger.error(
            "Failed to download tile",
            extra={"url": url, "error": str(exc)},
        )
    except zipfile.BadZipFile:
        logger.error("Invalid zip archive", extra={"path": zip_path})


def generate_coordinates() -> list[tuple[str, str]]:
    """Generate all latitude/longitude identifier pairs for ASTER tiles.

    Returns:
        A list of (lat_str, lon_str) tuples covering the full ASTER grid.
    """
    coordinates: list[tuple[str, str]] = []

    for lat in NORTH_LATITUDE_RANGE:
        for lon in WEST_LONGITUDE_RANGE:
            coordinates.append((f"N{lat:02d}", f"W{lon:03d}"))
        for lon in EAST_LONGITUDE_RANGE:
            coordinates.append((f"N{lat:02d}", f"E{lon:03d}"))

    for lat in SOUTH_LATITUDE_RANGE:
        for lon in WEST_LONGITUDE_RANGE:
            coordinates.append((f"S{lat:02d}", f"W{lon:03d}"))
        for lon in EAST_LONGITUDE_RANGE:
            coordinates.append((f"S{lat:02d}", f"E{lon:03d}"))

    return coordinates


def download_all_tiles(
    *,
    download_folder: str = DEFAULT_DOWNLOAD_FOLDER,
    unzip_folder: str = DEFAULT_UNZIP_FOLDER,
    max_threads: int = MAX_DOWNLOAD_THREADS,
) -> None:
    """Download and extract all ASTER tiles concurrently.

    Args:
        download_folder: Temporary download directory (recommend tmpfs/ramdisk).
        unzip_folder: Final extraction directory for .tif files.
        max_threads: Maximum number of concurrent download threads.
    """
    os.makedirs(download_folder, exist_ok=True)
    os.makedirs(unzip_folder, exist_ok=True)

    coordinates = generate_coordinates()

    with ThreadPoolExecutor(max_workers=max_threads) as executor:
        futures = {
            executor.submit(
                download_and_unzip,
                lat,
                lon,
                download_folder=download_folder,
                unzip_folder=unzip_folder,
            ): (lat, lon)
            for lat, lon in coordinates
        }

        for future in as_completed(futures):
            lat, lon = futures[future]
            try:
                future.result()
            except Exception:
                logger.exception(
                    "Unexpected error processing tile",
                    extra={"lat": lat, "lon": lon},
                )


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    )
    download_all_tiles()

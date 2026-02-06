# Open Elevation

A self-hosted, open-source elevation API. Drop GeoTIFF files into a directory, start the server, and query elevation for any coordinate on Earth.

## Quick Start

```bash
# 1. Clone and enter the project
git clone <repo-url> && cd open-elevation

# 2. Download elevation data (pick one)
python -m open_elevation.download.alos     # ALOS World 3D 30m
python -m open_elevation.download.aster    # ASTER GDEM

# 3. Start the server
docker compose up --build
```

The API is now available at `http://localhost:9898`.

## API Usage

### `GET /api/v1/lookup`

Look up elevation for one or more coordinates.

**Single location:**

```bash
curl "http://localhost:9898/api/v1/lookup?locations=51.5,-0.1"
```

```json
{
  "results": [
    {
      "latitude": 51.5,
      "longitude": -0.1,
      "elevation": 11.0
    }
  ]
}
```

**Multiple locations:**

```bash
curl "http://localhost:9898/api/v1/lookup?locations=51.5,-0.1&locations=48.8,2.3"
```

```json
{
  "results": [
    { "latitude": 51.5, "longitude": -0.1, "elevation": 11.0 },
    { "latitude": 48.8, "longitude": 2.3, "elevation": 35.0 }
  ]
}
```

**Error responses:**

| Status | Condition |
|--------|-----------|
| 400 | Invalid coordinate format or out of range |
| 404 | No elevation data covers the coordinate |
| 422 | Missing `locations` parameter |

Interactive docs are available at `http://localhost:9898/docs`.

## Data Sources

The project includes download scripts for two global elevation datasets:

| Dataset | Resolution | Script |
|---------|-----------|--------|
| [ALOS World 3D](https://www.eorc.jaxa.jp/ALOS/en/dataset/aw3d30/aw3d30_e.htm) | 30m | `python -m open_elevation.download.alos` |
| [ASTER GDEM](https://asterweb.jpl.nasa.gov/gdem.asp) | 30m | `python -m open_elevation.download.aster` |

You can also use any GeoTIFF (`.tif`) elevation file. Place them in the `tif_files/` directory (or set `TIF_DIRECTORY`) and the server will index them automatically on startup.

## Configuration

All settings are configured via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `TIF_DIRECTORY` | `/app/tif_files/` | Directory containing `.tif` elevation files |
| `INDEX_DIRECTORY` | `{TIF_DIRECTORY}/index` | Spatial index storage location |
| `CACHE_MAX_SIZE` | `100000` | Maximum number of cached elevation lookups |
| `MAX_WORKERS` | `100` | Thread pool size for concurrent lookups |

## Deployment

### Docker Compose (recommended)

```bash
docker compose up --build
```

This mounts `./tif_files` into the container and exposes port 9898.

### Docker

```bash
docker build -t open-elevation .
docker run -p 9898:9898 -v ./tif_files:/app/tif_files open-elevation
```

### Local

```bash
uv venv && uv pip install .
TIF_DIRECTORY=./tif_files uvicorn open_elevation.main:app --port 9898
```

## Development

### Setup

```bash
uv venv
uv pip install -e ".[dev]"
```

### Commands

```bash
make lint        # Run ruff linter
make format      # Auto-format code
make typecheck   # Run mypy --strict
make test        # Run pytest (31 tests)
make all         # All of the above
```

### Project Structure

```
src/open_elevation/
    main.py                 # FastAPI app entry point
    config.py               # Settings from environment variables
    exceptions.py           # Custom exception hierarchy
    elevation/
        routes.py           # API endpoints
        service.py          # Spatial index, raster reads, caching
        schemas.py          # Pydantic request/response models
    download/
        alos.py             # ALOS World 3D downloader
        aster.py            # ASTER GDEM downloader
tests/
    fixtures/
        test_elevation.tif  # Synthetic GeoTIFF for testing
    elevation/
        test_integration.py # End-to-end tests with real raster I/O
        test_routes.py      # API route tests
        test_schemas.py     # Schema validation tests
        test_service.py     # Service unit tests
```

## License

This project is licensed under the [MIT License](LICENSE).

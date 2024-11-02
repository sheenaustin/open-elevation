import os
import time
import logging
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from typing import List, Dict, Union
from concurrent.futures import ThreadPoolExecutor
import rasterio
from rtree import index
from cachetools import LRUCache
import asyncio

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

app = FastAPI()

# Directory paths
TIF_DIRECTORY = os.getenv("TIF_DIRECTORY", "/app/tif_files/")
INDEX_DIRECTORY = os.getenv("INDEX_DIRECTORY", "/app/tif_files/index")

# Ensure index directory exists
os.makedirs(INDEX_DIRECTORY, exist_ok=True)

# Persistent index file paths
INDEX_PATH = os.path.join(INDEX_DIRECTORY, "spatial_index")

# Cache for frequently accessed elevation data
cache = LRUCache(maxsize=100000)
executor = ThreadPoolExecutor(max_workers=100)

class ElevationResult(BaseModel):
    latitude: float
    longitude: float
    elevation: Union[float, str]

# Initialize or load the spatial index with rtree's persistent storage
def build_or_load_index():
    global spatial_index

    if not os.path.exists(TIF_DIRECTORY):
        raise HTTPException(status_code=500, detail="TIF directory not found")

    properties = index.Property()
    properties.storage = index.RT_Disk
    properties.overwrite = False  # Only overwrite if rebuilding

    # Check if index files exist, load if they do; otherwise, rebuild
    if os.path.exists(INDEX_PATH + ".dat"):
        logging.info("Loading existing spatial index from disk...")
        spatial_index = index.Index(INDEX_PATH, properties=properties)
    else:
        logging.info("Index outdated or missing. Rebuilding spatial index from scratch...")
        spatial_index = index.Index(INDEX_PATH, properties=properties)

        for root, _, files in os.walk(TIF_DIRECTORY):
            for filename in files:
                if filename.endswith(".tif"):
                    filepath = os.path.join(root, filename)
                    try:
                        with rasterio.open(filepath) as src:
                            bounds = src.bounds
                            spatial_index.insert(id(filepath), (bounds.left, bounds.bottom, bounds.right, bounds.top), obj=filepath)
                            logging.info(f"Indexed file {filename} at {filepath}")
                    except Exception as e:
                        logging.error(f"Failed to index file {filename}. Error: {e}")

# Get elevation from the indexed TIF files
def get_elevation(lat, lon):
    cache_key = (lat, lon)
    if cache_key in cache:
        return cache[cache_key]

    matches = [obj for obj in spatial_index.intersection((lon, lat, lon, lat), objects=True)]
    for match in matches:
        tif_file = match.object
        try:
            with rasterio.open(tif_file) as dataset:
                row, col = dataset.index(lon, lat)
                elevation = dataset.read(1)[row, col]
                cache[cache_key] = elevation
                return elevation
        except Exception as e:
            logging.error(f"Error reading elevation data from file {tif_file}: {e}")
            raise HTTPException(status_code=500, detail="Error accessing elevation data")
    
    raise HTTPException(status_code=404, detail="Elevation data not found for specified coordinates")

@app.get("/api/v1/lookup", response_model=Dict[str, List[ElevationResult]])
async def lookup(locations: List[str] = Query(...)):
    if not locations:
        raise HTTPException(status_code=400, detail="No locations provided")

    loop = asyncio.get_event_loop()
    tasks = [loop.run_in_executor(executor, process_location, location) for location in locations]
    try:
        elevations = await asyncio.gather(*tasks)
    except Exception as e:
        logging.error(f"Error processing lookup: {e}")
        raise HTTPException(status_code=500, detail="Error processing elevation lookup")

    return {"results": elevations}

def process_location(location: str) -> ElevationResult:
    try:
        lat, lon = map(float, location.split(','))
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid location format: '{location}'")
    
    if not (-90 <= lat <= 90):
        raise HTTPException(status_code=400, detail=f"Invalid latitude value: {lat}. Must be between -90 and 90.")
    if not (-180 <= lon <= 180):
        raise HTTPException(status_code=400, detail=f"Invalid longitude value: {lon}. Must be between -180 and 180.")

    elevation = get_elevation(lat, lon)
    if elevation is not None:
        return ElevationResult(latitude=lat, longitude=lon, elevation=elevation)
    
    raise HTTPException(status_code=404, detail="Elevation data not found")

# Load or build the index on startup
try:
    build_or_load_index()
except HTTPException as e:
    logging.error(f"Error during index build or load: {e.detail}")
except Exception as e:
    logging.error(f"Unexpected error during index build or load: {e}")
    raise HTTPException(status_code=500, detail="Unexpected server error during index initialization")

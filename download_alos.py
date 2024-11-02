import os
import requests
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed

def generate_all_tiles(step=5):
    tile_names = []
    
    # Loop through latitude from 90 (N) to -90 (S) with 5-degree steps
    for lat in range(85, -90, -step):
        # Loop through longitude from -180 (W) to 180 (E) with 5-degree steps
        for lon in range(-180, 180, step):
            # Determine start coordinates
            start_lat = f"N{abs(lat):03d}" if lat >= 0 else f"S{abs(lat):03d}"
            start_lon = f"W{abs(lon):03d}" if lon < 0 else f"E{abs(lon):03d}"
            
            # Determine end coordinates
            end_lat = f"N{abs(lat + step):03d}" if (lat + step) <= 90 and (lat + step) > 0 else f"S{abs(lat + step):03d}"
            end_lon = f"W{abs(lon + step):03d}" if (lon + step) <= 0 else f"E{abs(lon + step):03d}"
            
            # Create the tile name
            tile_name = f"{start_lat}{start_lon}_{end_lat}{end_lon}"
            tile_names.append(tile_name)
    
    return tile_names

def download_and_extract_tile(tile_name, destination_folder):
    # Base URL format for downloading files
    base_url = "https://www.eorc.jaxa.jp/ALOS/aw3d30/data/release_v2404/"
    url = f"{base_url}{tile_name}.zip"
    zip_path = os.path.join(destination_folder, f"{tile_name}.zip")
    extract_path = os.path.join(destination_folder, tile_name)
    
    # Attempt to download the tile
    try:
        print(f"Downloading {url} to {zip_path}...")
        response = requests.get(url, stream=True)
        response.raise_for_status()  # Check for HTTP errors
        
        # Write the downloaded content to a file
        with open(zip_path, "wb") as file:
            for chunk in response.iter_content(chunk_size=8192):
                file.write(chunk)
        print(f"Downloaded {tile_name}.zip successfully.")
        
        # Check the file size and delete if smaller than 4 KB
        if os.path.getsize(zip_path) < 4096:
            print(f"{tile_name}.zip is smaller than 4 KB. Removing file.")
            os.remove(zip_path)
        else:
            print(f"{tile_name}.zip is larger than 4 KB and has been saved.")
            
            # Extract the zip file
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_path)
            print(f"Extracted {tile_name}.zip to {extract_path}")
            
            # Delete the zip file after extraction
            os.remove(zip_path)
            print(f"Deleted the zip file: {zip_path}")
            
    except requests.exceptions.RequestException as e:
        print(f"Failed to download {tile_name}: {e}")
    except zipfile.BadZipFile:
        print(f"Failed to unzip {tile_name}.zip: The file is not a valid zip archive.")
        os.remove(zip_path)

def download_all_tiles(destination_folder, max_threads=100):
    # Create the destination folder
    os.makedirs(destination_folder, exist_ok=True)
    
    # Generate all tile names
    all_tiles = generate_all_tiles()

    # Concurrent downloads
    with ThreadPoolExecutor(max_workers=max_threads) as executor:
        # Submit all download tasks to the executor
        future_to_tile = {executor.submit(download_and_extract_tile, tile, destination_folder): tile for tile in all_tiles}
        
        # Process completed tasks as they finish
        for future in as_completed(future_to_tile):
            tile = future_to_tile[future]
            try:
                future.result()  # Raise any exceptions caught during download and extraction
            except Exception as e:
                print(f"Tile {tile} generated an exception: {e}")

# Destination folder for the downloads
destination_folder = "tif_files"

# Start the download process with 100 parallel threads
download_all_tiles(destination_folder, max_threads=100)

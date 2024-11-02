import requests
import os
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed

# Ranges for latitudes and longitudes in both hemispheres
north_latitude_range = range(0, 83)  # From 0°N to 83°N
south_latitude_range = range(0, 83)  # From 0°S to 83°S
west_longitude_range = range(0, 181)  # From 0°W to 180°W
east_longitude_range = range(0, 181)  # From 0°E to 180°E

# Base URL
base_url = "https://gdemdl.aster.jspacesystems.or.jp/download/Download_"
download_folder = "/dev/shm/ASTER_GDE" # Put it in shared memory
unzip_folder = "tif_files"

# Create download and unzip folders if they don't exist
os.makedirs(download_folder, exist_ok=True)
os.makedirs(unzip_folder, exist_ok=True)

# Recursively unzip files
def recursive_unzip(zip_path, extract_to):
    """ Recursively unzips nested zip files within a directory. """
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to)
    os.remove(zip_path)  # Remove the original zip after extraction

    # Check for nested zip files and extract them
    for root, _, files in os.walk(extract_to):
        for file in files:
            if file.endswith(".zip"):
                nested_zip_path = os.path.join(root, file)
                nested_extract_to = os.path.splitext(nested_zip_path)[0]
                os.makedirs(nested_extract_to, exist_ok=True)
                recursive_unzip(nested_zip_path, nested_extract_to)  # Recursively unzip

# Download and unzip files
def download_and_unzip(lat_str, lon_str):
    url = f"{base_url}{lat_str}{lon_str}.zip"
    zip_path = os.path.join(download_folder, f"{lat_str}{lon_str}.zip")
    extract_path = os.path.join(unzip_folder, f"{lat_str}{lon_str}")
    
    try:
        # Download the zip file
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        # Save the downloaded zip file
        with open(zip_path, "wb") as f:
            f.write(response.content)
        
        # Unzip the file, recursively handling nested zips
        os.makedirs(extract_path, exist_ok=True)
        recursive_unzip(zip_path, extract_path)
        
        print(f"Downloaded and recursively unzipped: {lat_str}{lon_str}")
        
    except requests.exceptions.RequestException as e:
        print(f"Failed to download {url}: {e}")
    except zipfile.BadZipFile:
        print(f"Failed to unzip {zip_path}: Bad zip file")

# Generate all latitude and longitude pairs for North, South, East, and West
coordinates = []
for lat in north_latitude_range:
    for lon in west_longitude_range:
        coordinates.append((f"N{lat:02d}", f"W{lon:03d}"))
    for lon in east_longitude_range:
        coordinates.append((f"N{lat:02d}", f"E{lon:03d}"))

for lat in south_latitude_range:
    for lon in west_longitude_range:
        coordinates.append((f"S{lat:02d}", f"W{lon:03d}"))
    for lon in east_longitude_range:
        coordinates.append((f"S{lat:02d}", f"E{lon:03d}"))

# Use ThreadPoolExecutor to download and unzip files simultaneously
with ThreadPoolExecutor(max_workers=100) as executor:
    # Submit download tasks
    futures = {executor.submit(download_and_unzip, lat, lon): (lat, lon) for lat, lon in coordinates}

    # Wait for all downloads to complete
    for future in as_completed(futures):
        lat, lon = futures[future]
        try:
            future.result()  # Check if there were any exceptions
        except Exception as e:
            print(f"Error processing {lat}{lon}: {e}")

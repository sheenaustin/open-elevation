#!/bin/bash

# Find unique latitude-longitude identifiers
coordinates=$(find tif_files/ -name '*.tif' | awk -F'_' '{ match($4, /[NS][0-9]{1,3}[EW][0-9]{2,3}/, arr); if (arr[0] != "") print arr[0] }' | sort -u)

# Function to convert coordinates to decimal lat/long and add random decimals
parse_coordinate() {
    coord=$1
    lat_sign=1
    lon_sign=1
    
    # Determine if latitude or longitude is negative
    [[ ${coord:0:1} == "S" ]] && lat_sign=-1
    [[ ${coord:3:1} == "W" ]] && lon_sign=-1

    # Extract numeric values and remove leading zeros
    lat=$(echo "${coord:1:2}" | sed 's/^0*//')
    lon=$(echo "${coord:4:3}" | sed 's/^0*//')
    
    # Apply signs
    lat=$((lat_sign * lat))
    lon=$((lon_sign * lon))
    
    # Generate random decimals between 0 and 9999 for precision
    lat_random=$(shuf -i 0-5000 -n 1)
    lon_random=$(shuf -i 0-5000 -n 1)
    
    # Format latitude and longitude with random decimals
    lat_decimal=$(printf "%s.%04d" "$lat" "$lat_random")
    lon_decimal=$(printf "%s.%04d" "$lon" "$lon_random")
    
    echo "$lat_decimal,$lon_decimal"
}

# Iterate over each unique coordinate and make the API request
for coord in $coordinates; do
    # Parse latitude and longitude with random decimals
    latlon=$(parse_coordinate "$coord")

    # Update with the correct IP as needed
    url="http://0.0.0.0:9898/api/v1/lookup?locations=${latlon}"

    # Send the request and capture the HTTP status
    http_status=$(curl -s -o /dev/null -w "%{http_code}" "$url")

    # Check the status code
    if [ "$http_status" -eq 200 ]; then
        echo "SUCCESS: $coord -> $url -> HTTP Status $http_status"
    else
        echo "FAILURE: $coord -> $url -> HTTP Status $http_status"
    fi
done

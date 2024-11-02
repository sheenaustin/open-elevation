# Use an official Python image as the base
FROM python:3.12-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV TIF_DIRECTORY=/app/tif_files

# Install required system libraries, including libspatialindex and libexpat for rasterio
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    libspatialindex-dev \
    libexpat1 \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Copy requirements and install them
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# Expose the new port
EXPOSE 9898

# Run the FastAPI application with Uvicorn on port 9898
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "9898"]

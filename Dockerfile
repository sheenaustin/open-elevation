# Use an official Python image as the base
FROM python:3.12-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV TIF_DIRECTORY=/app/tif_files

# Install required system libraries for rasterio and rtree
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    libspatialindex-dev \
    libexpat1 \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set the working directory
WORKDIR /app

# Copy dependency files first for layer caching
COPY pyproject.toml requirements.txt ./

# Install dependencies with uv
RUN uv pip install --system --no-cache -r requirements.txt

# Copy the application source
COPY src/ src/

# Install the project itself (no deps — already installed above)
RUN uv pip install --system --no-cache --no-deps .

# Expose the port
EXPOSE 9898

# Run the FastAPI application with Uvicorn
CMD ["uvicorn", "open_elevation.main:app", "--host", "0.0.0.0", "--port", "9898"]

# ArthLens Backend Multi-Stage Dockerfile
# Authoritative Reference: ArthLens Build Handbook v1.0 (Part 3.2, 14.2)
FROM python:3.14-slim-bookworm AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install system dependencies for geospatial libraries (GDAL, GEOS, PROJ) and PostgreSQL client
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libgdal-dev \
    libgeos-dev \
    libproj-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy backend requirements and pyproject.toml
COPY backend/pyproject.toml /app/backend/
WORKDIR /app/backend
RUN pip install --upgrade pip && \
    pip install .

WORKDIR /app
COPY backend /app/backend

EXPOSE 8000

CMD ["uvicorn", "backend.arthlens.api.main:app", "--host", "0.0.0.0", "--port", "8000"]

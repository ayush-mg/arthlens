# ArthLens Backend Multi-Stage Dockerfile
FROM python:3.12-slim-bookworm AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app

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

COPY backend/pyproject.toml /app/backend/
WORKDIR /app/backend
RUN pip install --upgrade pip && \
    pip install .

WORKDIR /app
COPY backend /app/backend
COPY scripts /app/scripts

EXPOSE 8000

CMD ["uvicorn", "backend.arthlens.api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]

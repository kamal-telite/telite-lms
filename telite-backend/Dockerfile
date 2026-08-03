FROM python:3.12-slim

LABEL org.opencontainers.image.title="Telite LMS Backend" \
      org.opencontainers.image.description="FastAPI backend for Telite LMS" \
      org.opencontainers.image.source="https://github.com/telite-systems/telite-lms"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    BACKEND_INTERNAL_PORT=8001

WORKDIR /app

# Stage 1: Build dependencies
# Update and upgrade all system packages, then install build dependencies
RUN apt-get update && apt-get upgrade -y && apt-get install -y --no-install-recommends \
    bash \
    build-essential \
    gosu \
    libcairo2 \
    libcairo2-dev \
    libpango-1.0-0 \
    libpango1.0-dev \
    libgdk-pixbuf-2.0-0 \
    libgdk-pixbuf-2.0-dev \
    libffi-dev \
    libpq-dev \
    shared-mime-info \
    fonts-dejavu-core \
    libharfbuzz0b \
    libharfbuzz-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip to latest security version
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Create application user before copying files for better layer caching
RUN groupadd --system telite \
    && useradd --system --gid telite --home-dir /app telite

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app ./app
COPY scripts ./scripts
COPY main.py telite_store.py ./
COPY students.csv faculty.csv ./
COPY alembic.ini ./
COPY app/db/migrations ./app/db/migrations

# Set up application directory permissions
RUN sed -i 's/\r$//' /app/scripts/docker-entrypoint.sh \
    && chmod +x /app/scripts/docker-entrypoint.sh \
    && mkdir -p /app/uploads \
    && chown -R telite:telite /app

EXPOSE ${BACKEND_INTERNAL_PORT}

USER telite

# Health check using the new operational endpoints
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD python -c "import os, urllib.request; port=os.getenv('BACKEND_INTERNAL_PORT','8001'); urllib.request.urlopen(f'http://127.0.0.1:{port}/ops/health', timeout=5)" || exit 1

# Use STOPSIGNAL for graceful shutdown
STOPSIGNAL SIGTERM

ENTRYPOINT ["/app/scripts/docker-entrypoint.sh"]
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${BACKEND_INTERNAL_PORT:-8001} --timeout-graceful-shutdown 30"]

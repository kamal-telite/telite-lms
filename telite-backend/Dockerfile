FROM python:3.12-slim-bookworm

LABEL org.opencontainers.image.title="Telite LMS Backend" \
      org.opencontainers.image.description="FastAPI backend for Telite LMS" \
      org.opencontainers.image.source="https://github.com/telite-systems/telite-lms"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    BACKEND_INTERNAL_PORT=8001

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
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
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system telite \
    && useradd --system --gid telite --home-dir /app telite

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY scripts ./scripts
COPY main.py telite_store.py ./
COPY students.csv faculty.csv ./
COPY alembic.ini ./
COPY app/db/migrations ./app/db/migrations

RUN sed -i 's/\r$//' /app/scripts/docker-entrypoint.sh \
    && chmod +x /app/scripts/docker-entrypoint.sh \
    && mkdir -p /app/uploads \
    && chown -R telite:telite /app

EXPOSE ${BACKEND_INTERNAL_PORT}

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD python -c "import os, urllib.request; port=os.getenv('BACKEND_INTERNAL_PORT','8001'); urllib.request.urlopen(f'http://127.0.0.1:{port}/health/liveness', timeout=5)" || exit 1

ENTRYPOINT ["/app/scripts/docker-entrypoint.sh"]
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${BACKEND_INTERNAL_PORT:-8001}"]

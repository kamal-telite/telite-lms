FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    BACKEND_INTERNAL_PORT=8001

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential gosu \
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

RUN sed -i 's/\r$//' /app/scripts/docker-entrypoint.sh \
    && chmod +x /app/scripts/docker-entrypoint.sh \
    && mkdir -p /app/uploads \
    && chown -R telite:telite /app

EXPOSE ${BACKEND_INTERNAL_PORT}

ENTRYPOINT ["/app/scripts/docker-entrypoint.sh"]
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${BACKEND_INTERNAL_PORT:-8001}"]

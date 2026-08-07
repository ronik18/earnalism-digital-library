FROM python:3.11-slim AS builder

ENV PIP_NO_CACHE_DIR=1

WORKDIR /build

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN python -m pip install --upgrade pip \
    && python -m pip wheel --wheel-dir /wheels -r requirements.txt \
    && python -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-index --find-links=/wheels -r requirements.txt \
    && find /opt/venv -type d -name __pycache__ -prune -exec rm -rf {} +

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MALLOC_ARENA_MAX=2 \
    COST_CONTROL_MODE=true \
    ENABLE_BACKGROUND_WORKERS=false \
    ENABLE_AUDIOBOOK_PIPELINE=false \
    ENABLE_BOOK_RENDERING_JOBS=false \
    ENABLE_COVER_GENERATION=false \
    ENABLE_SCHEDULED_JOBS=false \
    ENABLE_QUEUE_CONSUMER=false \
    ENABLE_ADMIN_MEDIA_UPLOADS=false \
    ENABLE_STARTUP_DB_MAINTENANCE=false \
    MAX_CONCURRENT_JOBS=1

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:${PATH}"

COPY . .

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=5).read()"

CMD ["sh", "./start_prod.sh"]

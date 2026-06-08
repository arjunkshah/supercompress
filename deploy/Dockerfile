FROM python:3.11-slim-bookworm

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md LICENSE ./
COPY supercompress ./supercompress
COPY scripts ./scripts
COPY checkpoints/.gitkeep ./checkpoints/

RUN pip install --no-cache-dir -U pip && \
    pip install --no-cache-dir -e . && \
    supercompress-train --fast

ENV HARBOR_DEMO=0
ENV PORT=8000

EXPOSE 8000

CMD uvicorn supercompress.stack.server_api:app --host 0.0.0.0 --port ${PORT:-8000}

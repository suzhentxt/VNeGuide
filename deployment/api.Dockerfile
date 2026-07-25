# syntax=docker/dockerfile:1.7

FROM python:3.14-slim@sha256:cea0e6040540fb2b965b6e7fb5ffa00871e632eef63719f0ea54bca189ce14a6

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    VNEGUIDE_API_HOST=0.0.0.0 \
    VNEGUIDE_API_PORT=8000 \
    VNEGUIDE_LLM_PROVIDER=mock

WORKDIR /app

COPY pyproject.toml README.md deployment/requirements-api.lock ./
COPY src ./src
COPY data ./data

RUN python -m pip install --no-cache-dir --constraint requirements-api.lock ".[api,ocr]" \
    && useradd --create-home --uid 10001 vneguide \
    && chown -R vneguide:vneguide /app

USER vneguide
EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=3s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2).read()"]

CMD ["python", "-m", "vneguide.api"]

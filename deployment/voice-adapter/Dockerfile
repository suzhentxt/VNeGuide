# syntax=docker/dockerfile:1.7

FROM python:3.11-slim@sha256:db3ff2e1800a8581e2c48a27c3995339d47bdf046da21c7627accd3d51053a93

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    VNEGUIDE_VOICE_ADAPTER_PORT=9210

WORKDIR /app

RUN apt-get update \
    && apt-get install --yes --no-install-recommends ca-certificates ffmpeg \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 10001 --shell /usr/sbin/nologin voice-adapter

COPY deployment/voice-adapter/requirements.txt ./requirements.txt
RUN python -m pip install --no-cache-dir --requirement requirements.txt

COPY --chown=voice-adapter:voice-adapter deployment/voice-adapter/app.py ./app.py

USER 10001:10001

HEALTHCHECK --interval=15s --timeout=3s --start-period=5s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:9210/health', timeout=2).read()"]

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "9210", "--no-access-log", "--workers", "1"]

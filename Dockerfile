FROM python:3.12.13-slim-bookworm@sha256:d50fb7611f86d04a3b0471b46d7557818d88983fc3136726336b2a4c657aa30b

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app/engine/src \
    PAPERFLOW_STORAGE_ROOT=/var/data/projects

WORKDIR /app

COPY engine /app/engine
RUN python -m pip install --upgrade pip==26.2.1 \
    && python -m pip install -c /app/engine/constraints.txt /app/engine

RUN useradd --create-home --uid 10001 paperflow \
    && mkdir -p /var/data/projects \
    && chown -R paperflow:paperflow /var/data /app

USER paperflow
EXPOSE 10000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:'+os.getenv('PORT','10000')+'/healthz', timeout=3)" || exit 1

CMD ["sh", "-c", "uvicorn paperflow.server.app:app --host 0.0.0.0 --port ${PORT:-10000} --workers 1"]

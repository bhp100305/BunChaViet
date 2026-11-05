
FROM python:3.14-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DB_MODE=postgres

WORKDIR /app

# psycopg[binary] bundles libpq; no SQL Server ODBC driver in the Neon image.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --require-hashes -r requirements.txt \
    && pip check

# .dockerignore restricts the context to application files and public assets.
COPY . .

CMD ["sh", "-c", "exec gunicorn main:app --bind 0.0.0.0:${PORT:-10000} --workers 1 --threads 4 --timeout 120"]

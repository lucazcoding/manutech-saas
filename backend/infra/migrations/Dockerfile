FROM python:3.12-slim

WORKDIR /migrations

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /requirements.txt
RUN pip install --no-cache-dir alembic "psycopg[binary]" "sqlalchemy[asyncio]"

COPY infra/migrations/ .

CMD ["alembic", "upgrade", "head"]

FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY shared/ ./shared/
ENV PYTHONPATH=/app

COPY services/finance/ ./services/finance/

RUN groupadd -r appuser && useradd -r -g appuser -u 1000 appuser
USER appuser

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8005/health || exit 1

CMD ["uvicorn", "services.finance.main:app", "--host", "0.0.0.0", "--port", "8005"]

FROM python:3.12-slim

WORKDIR /seed

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /seed/requirements.txt
RUN pip install --no-cache-dir -r /seed/requirements.txt

COPY seed_admin.py /seed/seed_admin.py
COPY seed_data.py /seed/seed_data.py

CMD ["python", "seed_data.py"]

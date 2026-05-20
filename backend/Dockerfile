FROM python:3.11.13-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

COPY pyproject.toml .

RUN pip install --upgrade pip && \
    pip install . --no-cache-dir

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        wget ca-certificates && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

COPY src/ .

ARG BACKEND_VERSION=UNSET
ENV BACKEND_VERSION=${BACKEND_VERSION}

RUN mkdir -p /data

VOLUME ["/data"]

EXPOSE 8000

CMD ["python", "main.py"]

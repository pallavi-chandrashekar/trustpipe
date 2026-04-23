FROM python:3.11-slim

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# Install TrustPipe with all extras
COPY pyproject.toml README.md LICENSE ./
COPY src/ src/
RUN pip install --no-cache-dir ".[trust,dashboard,api,postgres]"

# Default: run the API server
EXPOSE 8000 8050
CMD ["trustpipe", "serve", "--host", "0.0.0.0", "--port", "8000"]

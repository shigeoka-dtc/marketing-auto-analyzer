FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install system dependencies including Node.js and Playwright requirements
RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    ca-certificates \
    build-essential \
    gcc \
    g++ \
    curl \
    gnupg \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip setuptools wheel && \
    pip install -r requirements.txt

COPY . .

RUN chmod +x /app/run.sh /app/run_dashboard.sh /app/run_worker.sh

# Create user with UID 1000 for non-root execution and set home directory
RUN useradd -m -u 1000 -d /app appuser && \
    chown -R appuser:appuser /app

# Install Playwright browsers (without system dependencies - already installed)
RUN python -m playwright install

USER appuser

CMD ["/bin/bash", "/app/run_dashboard.sh"]

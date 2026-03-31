FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    ca-certificates \
    build-essential \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip setuptools wheel && \
    pip install -r requirements.txt

COPY . .

RUN chmod +x /app/run.sh /app/run_dashboard.sh /app/run_worker.sh

CMD ["/bin/bash", "/app/run_dashboard.sh"]

# Node.js を追加する例（Debian/Ubuntu ベースイメージ想定）
# 1) Node.js のインストール（LTS）
RUN apt-get update && apt-get install -y curl gnupg \
  && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
  && apt-get install -y nodejs

# 2) Python の依存をインストール（既存の pip install -r requirements.txt の後に）
RUN python -m playwright install --with-deps

# 注意:
# - Playwright のブラウザは上のコマンドで取得されます
# - Lighthouse を使うために nodejs が必要。npx lighthouse で動作します。

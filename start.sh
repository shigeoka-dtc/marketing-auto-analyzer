#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

export LOCAL_UID="${LOCAL_UID:-$(id -u)}"
export LOCAL_GID="${LOCAL_GID:-$(id -g)}"

docker compose up --build -d

echo ""
echo "Marketing Auto Analyzer を起動しました。"
echo "Dashboard: http://localhost:8501"
echo "対象サイト設定: data/raw/target_urls.txt"
echo "レポート出力先: reports/"
echo "停止する場合: docker compose down"

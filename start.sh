#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

export LOCAL_UID="${LOCAL_UID:-$(id -u)}"
export LOCAL_GID="${LOCAL_GID:-$(id -g)}"

docker compose up --build -d

echo ""
echo "Marketing Auto Analyzer を起動しました。"
echo "レポート出力先: reports/"
echo "対象サイト設定: data/raw/target_urls.txt"
echo "停止する場合: docker compose down"
echo ""
echo "✅ Worker が起動中です。定期的に分析を実行し、レポートを生成します。"
echo "📊 最新のレポートは reports/daily_analysis_latest.md を参照してください。"

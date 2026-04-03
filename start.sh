#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

export LOCAL_UID="${LOCAL_UID:-$(id -u)}"
export LOCAL_GID="${LOCAL_GID:-$(id -g)}"

# Parse options
DURATION=""
NO_OVERWRITE="false"
while [[ $# -gt 0 ]]; do
    case $1 in
        --duration)
            DURATION="$2"
            shift 2
            ;;
        --no-overwrite)
            NO_OVERWRITE="true"
            shift 1
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

docker compose up --build -d

echo ""
echo "Marketing Auto Analyzer を起動しました。"
echo "レポート出力先: reports/"
echo "対象サイト設定: data/raw/target_urls.txt"
echo "停止する場合: docker compose down"
echo ""

if [ -n "$DURATION" ]; then
    echo "⏱️  指定時間の間、ひたすら分析を実行します: $DURATION"
    echo ""

    if [ -d ".venv" ]; then
        source .venv/bin/activate

        WORKER_CMD="python -m src.worker --duration \"$DURATION\" --final-report \"hourly_analysis_final.md\""
        if [ "$NO_OVERWRITE" = "true" ]; then
            WORKER_CMD="$WORKER_CMD --no-overwrite"
        fi

        eval "$WORKER_CMD"

        echo "✅ 指定時間の連続分析が完了しました。"
        echo "📊 最終レポート: reports/hourly_analysis_final.md"
    else
        echo "❌ virtualenv が見つかりません"
        exit 1
    fi
else
    echo "✅ Worker が起動中です。定期的に分析を実行し、レポートを生成します。"
    echo "📊 最新のレポートは reports/daily_analysis_latest.md を参照してください。"
fi

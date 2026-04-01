#!/bin/bash
# ノートPC用 高速スタートスクリプト

set -e

echo "🚀 ノートPC版 Marketing Auto Analyzer スタート"
echo "================================================"

# ステップ1: 環境確認
echo -e "\n✅ ステップ1: 環境確認中..."
bash check_laptop_compatibility.sh > /dev/null 2>&1 || bash check_laptop_compatibility.sh

# ステップ2: Ollama モデルダウンロード（必要時）
echo -e "\n✅ ステップ2: Ollama モデル確認中..."
MODEL=$(grep "^OLLAMA_MODEL=" .env | cut -d'=' -f2)
echo "  モデル: $MODEL"

if ! curl -s http://localhost:11434/api/tags | grep -q "$MODEL" 2>/dev/null; then
    echo "  ⏳ モデルをダウンロード中... (初回は 5-10分程度かかります)"
    ollama pull "$MODEL"
else
    echo "  ✅ モデルはすでにダウンロード済み"
fi

# ステップ3: Docker イメージビルド
echo -e "\n✅ ステップ3: Docker イメージをビルド中..."
if ! docker images | grep -q marketing-auto-analyzer; then
    echo "  ⏳ 初回ビルド中..."
    docker compose build
else
    echo "  ✅ イメージはすでにビルド済み"
fi

# ステップ4: Docker コンテナ起動
echo -e "\n✅ ステップ4: Docker コンテナ起動中..."
docker compose up -d
sleep 3

# ステップ5: 起動確認
echo -e "\n✅ ステップ5: 起動状態を確認中..."
while ! curl -s http://localhost:8501 > /dev/null 2>&1; do
    echo "  ⏳ ダッシュボード起動待機中... (最大60秒)"
    sleep 5
done

echo -e "\n================================================"
echo "✅ セットアップ完了！"
echo ""
echo "📊 ダッシュボード: http://localhost:8501"
echo ""
echo "📋 次の操作:"
echo "  • ダッシュボードで URL を登録"
echo "  • Worker が自動分析を開始します"
echo "  • ログ確認: docker-compose logs -f worker"
echo ""
echo "🛑 停止方法:"
echo "  docker-compose down"
echo ""
echo "================================================"

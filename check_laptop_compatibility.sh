#!/bin/bash
set -e

echo "🔍 ノートPC動作環境チェック開始..."
echo "================================================"

# 1. メモリ確認
echo -e "\n📊 【メモリ確認】"
TOTAL_MEM=$(free -g | awk 'NR==2 {print $2}')
AVAILABLE_MEM=$(free -g | awk 'NR==2 {print $7}')
echo "  総メモリ: ${TOTAL_MEM}GB"
echo "  利用可能: ${AVAILABLE_MEM}GB"

if [ "$TOTAL_MEM" -lt 7 ]; then
    echo "  ⚠️  警告: 7GB以上推奨です"
else
    echo "  ✅ OK"
fi

# 2. Docker確認
echo -e "\n🐳 【Docker確認】"
if ! command -v docker &> /dev/null; then
    echo "  ❌ Docker がインストールされていません"
    exit 1
fi
echo "  ✅ Docker インストール済み"

# 3. docker-compose確認
echo -e "\n📦 【Docker Compose確認】"
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "  ❌ Docker Compose がインストールされていません"
    exit 1
fi
echo "  ✅ Docker Compose インストール済み"

# 4. .env ファイル確認
echo -e "\n⚙️  【.env 設定確認】"
if [ ! -f ".env" ]; then
    echo "  ❌ .env ファイルが見当たりません"
    exit 1
fi

MODEL=$(grep "^OLLAMA_MODEL=" .env | cut -d'=' -f2)
VISION=$(grep "^VISION_ANALYSIS_ENABLED=" .env | cut -d'=' -f2)
AGENT=$(grep "^MULTI_AGENT_ENABLED=" .env | cut -d'=' -f2)
RAG=$(grep "^RAG_ENABLED=" .env | cut -d'=' -f2)
PAGES=$(grep "^TARGET_SITE_MAX_PAGES=" .env | cut -d'=' -f2)

echo "  ✅ .env ファイル読み込み成功"
echo "     - Model: $MODEL"
echo "     - Vision: $VISION"
echo "     - Agent: $AGENT"
echo "     - RAG: $RAG"
echo "     - Max Pages: $PAGES"

# 5. Ollama サービス確認
echo -e "\n🤖 【Ollama サービス確認】"
if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "  ⚠️  Ollama がローカルで起動していません（後で起動）"
else
    echo "  ✅ Ollama サービス稼働中"
    # モデル確認
    MODELS=$(curl -s http://localhost:11434/api/tags | grep -o '"name":"[^"]*"' || true)
    if echo "$MODELS" | grep -q "$MODEL"; then
        echo "     ✅ モデル '$MODEL' がロード済み"
    else
        echo "     ⚠️  モデル '$MODEL' をダウンロード予定"
    fi
fi

# 6. ディレクトリ構造確認
echo -e "\n📁 【ディレクトリ構造確認】"
dirs=("data" "data/raw" "data/chroma" "db" "reports" "logs" "prompts" "src" "tests")
for dir in "${dirs[@]}"; do
    if [ -d "$dir" ]; then
        echo "  ✅ $dir/"
    else
        echo "  ⚠️  $dir/ 作成予定"
        mkdir -p "$dir"
    fi
done

# 7. Python 環境確認
echo -e "\n🐍 【Python 環境確認】"
if ! command -v python3 &> /dev/null; then
    echo "  ❌ Python3 がインストールされていません"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | awk '{print $2}')
echo "  ✅ Python $PYTHON_VERSION"

# 8. requirements.txt確認
echo -e "\n📋 【依存ライブラリ確認】"
if [ ! -f "requirements.txt" ]; then
    echo "  ❌ requirements.txt が見当たりません"
    exit 1
fi

# chromadb の確認
if grep -q "chromadb" requirements.txt; then
    echo "  ✅ chromadb が requirements.txt に含まれています"
else
    echo "  ⚠️  chromadb が必要です（後で追加）"
fi

# 9. 推奨事項
echo -e "\n💡 【推奨事項】"
if [ "$TOTAL_MEM" -eq 7 ] || [ "$TOTAL_MEM" -eq 8 ]; then
    echo "  • 他のアプリケーションを閉じて実行してください"
    echo "  • Ollama は localhost のみで起動してください"
fi

if [ "$TOTAL_MEM" -ge 16 ]; then
    echo "  • RAM が充分です。.env.full 設定を試せます"
fi

# 10. 次のステップ
echo -e "\n🚀 【次のステップ】"
echo "  1. Ollama が起動していることを確認:"
echo "     ollama serve &"
echo ""
echo "  2. モデルをダウンロード:"
echo "     ollama pull $MODEL"
echo ""
echo "  3. Docker で起動:"
echo "     docker-compose up -d"
echo ""
echo "  4. ダッシュボードアクセス:"
echo "     http://localhost:8501"
echo ""
echo "  5. ログ確認:"
echo "     docker-compose logs -f worker"

echo -e "\n================================================"
echo "✅ チェック完了！通常に進行できます。"

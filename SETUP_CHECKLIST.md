# ✅ AI全機能セットアップ確認チェックリスト

このチェックリストに従えば、AI全機能を無料で活用できます。

---

## ステップ 1: Ollama のセットアップ

### macOS の場合

- [ ] https://ollama.ai からダウンロード
- [ ] `/Applications/Ollama.app` をダブルクリック
- [ ] メニューバーに Ollama アイコンが表示される

```bash
# ターミナルで確認
curl http://localhost:11434/api/tags
```

出力例: `{"models":[{"name":"phi3:mini:latest",...}]}`

### Linux の場合

```bash
# インストール
curl https://ollama.ai/install.sh | sh

# サービス確認
systemctl status ollama

# 手動起動
ollama serve
```

---

## ステップ 2: LLM モデルのダウンロード

```bash
# phi3:mini をダウンロード（推奨・軽量・高速）
ollama pull phi3:mini

# または neural-chat（さらに高速）
ollama pull neural-chat

# ダウンロード確認
ollama list
```

**初回は 5-10分 かかります**

---

## ステップ 3: 設定ファイルの確認

```bash
# .env ファイルを検証
cd /home/nshigeoka/marketing-auto-analyzer

# AI機能が全て有効か確認
grep "ENABLED=true" .env
```

期待される出力:
```
OLLAMA_ENABLED=true
DEEP_ANALYSIS_ENABLED=true
STRATEGIC_LP_ANALYSIS_ENABLED=true
FORECASTING_ENABLED=true
IMPACT_ANALYSIS_ENABLED=true
```

### ❌ 有効でない場合

```bash
# .env を再生成
cat > .env << 'EOF'
OLLAMA_ENABLED=true
OLLAMA_URL=http://host.docker.internal:11434
OLLAMA_MODEL=phi3:mini
OLLAMA_TIMEOUT=120
OLLAMA_NUM_PREDICT=500

DEEP_ANALYSIS_ENABLED=true
DEEP_ANALYSIS_NUM_PREDICT=1800

STRATEGIC_LP_ANALYSIS_ENABLED=true
FORECASTING_ENABLED=true
IMPACT_ANALYSIS_ENABLED=true

SQLITE_BUSY_TIMEOUT_MS=30000
URL_PROCESSING_STALE_MINUTES=30
URL_RETRY_DELAY_MINUTES=15

WORKER_INTERVAL_SECONDS=300
TARGET_SITE_MAX_PAGES=8
URL_BATCH_SIZE=3
URL_ANALYSIS_TIMEOUT=30
ALLOWED_TARGET_HOSTS=

USE_PLAYWRIGHT=true
PLAYWRIGHT_HEADLESS=true
PLAYWRIGHT_MAX_PAGES=8
USE_LIGHTHOUSE=true
EOF
```

---

## ステップ 4: 分析対象の設定

### CSV データ

```bash
# data/raw/marketing.csv が存在するか確認
ls -lh data/raw/marketing.csv

# なければサンプルを作成
cat > data/raw/marketing.csv << 'EOF'
date,channel,campaign,sessions,users,conversions,revenue,cost
2026-03-25,google,search_brand,1500,1200,45,4500,800
2026-03-25,facebook,awareness,2000,1600,32,3200,1200
2026-03-26,google,search_brand,1600,1280,48,4800,850
2026-03-26,facebook,awareness,2100,1680,35,3500,1250
EOF
```

### 分析対象サイト

```bash
# data/raw/target_urls.txt を作成
cat > data/raw/target_urls.txt << 'EOF'
https://example.com/
https://example.com/pricing
EOF
```

---

## ステップ 5: 最初の実行

### 実行方法 A: 予測分析のみ（最速・LLM不要）

```bash
python main.py --enable-forecasting --enable-impact-analysis --skip-llm
```

⏱️ 実行時間: 1-2分

期待される出力:
```
CSV同期: success
対象サイト数: 2
分析レポートを生成しました: reports/manual_analysis_20260...
```

### 実行方法 B: 完全AI分析（推奨・Ollama必須）

```bash
python main.py --enable-forecasting --enable-impact-analysis
```

⏱️ 実行時間: 5-10分

期待される出力:
```
CSV同期: success
対象サイト数: 2
分析レポートを生成しました: reports/manual_analysis_20260...
戦略的LP分析レポート生成: reports/lp_strategy_analysis_...
```

### 実行方法 C: ダッシュボード起動（本番運用）

```bash
./start.sh
```

**ダッシュボード**: http://localhost:8501

---

## ステップ 6: 出力の確認

### レポートの場所

```bash
ls -lh reports/

# 最新レポート表示
cat reports/$(ls -t reports/ | head -1)
```

### 期待される内容

✅ **日次KPI分析**
- チャネル別診断
- 前日比較

✅ **予測分析**（`--enable-forecasting` 有効時）
- 7日先のトレンド予測
- 異常検知アラート

✅ **施策効果分析**（`--enable-impact-analysis` 有効時）
- チャネル別貢献度

✅ **戦略的LP分析**（`--skip-llm` なし・Ollama有効時）
- H1/CTA/テキスト分析
- 複数改善パターン
- A/Bテスト設計

✅ **深掘り分析**（`DEEP_ANALYSIS_ENABLED=true` 時）
- チャネル別訴求案
- 実装チケット分解

---

## ステップ 7: ダッシュボード操作

```bash
# http://localhost:8501 へアクセス
```

**ダッシュボード機能**:
1. 📊 KPI メトリクスの可視化
2. 🎯 対象サイトの追加・編集
3. 📈 改善度の追跡
4. 🔍 詳細分析結果の表示

---

## ⚡ パフォーマンス最適化（オプション）

### 速度を優先

```env
OLLAMA_MODEL=neural-chat        # 高速モデル
OLLAMA_NUM_PREDICT=300
DEEP_ANALYSIS_NUM_PREDICT=600
TARGET_SITE_MAX_PAGES=3
WORKER_INTERVAL_SECONDS=180
```

### 深度を優先

```env
OLLAMA_TIMEOUT=180
OLLAMA_NUM_PREDICT=1500
DEEP_ANALYSIS_NUM_PREDICT=2000
TARGET_SITE_MAX_PAGES=10
WORKER_INTERVAL_SECONDS=600
```

---

## 🆘 トラブルシューティング

### ❌ エラー: `[LLM unavailable]`

```bash
# 原因1: Ollama が起動していない
curl http://localhost:11434/api/tags
# 出力がなければ
ollama serve

# 原因2: モデルがない
ollama list
# phi3 がなければ
ollama pull phi3:mini
```

### ❌ エラー: Docker コンテナが起動しない

```bash
# logs を確認
docker compose logs

# コンテナを再構築
docker compose down
docker compose up --build
```

### ❌ 実行が遅い / メモリ不足

```bash
# 軽量設定を使用
echo "OLLAMA_MODEL=neural-chat" >> .env
echo "OLLAMA_NUM_PREDICT=200" >> .env
docker compose restart
```

---

## 📚 詳しくは

- [AI_USAGE_GUIDE.md](AI_USAGE_GUIDE.md) - 使用ガイド
- [README.md](README.md) - プロジェクト説明
- [NEW_FEATURES.md](NEW_FEATURES.md) - 新機能説明

---

**全機能セットアップ完了! 🎉**

次のコマンドで分析開始:

```bash
python main.py --enable-forecasting --enable-impact-analysis
```

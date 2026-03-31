# 🤖 AI全機能の完全ガイド

このプロジェクトのAI機能を完全に活用するための実行ガイドです。

---

## 🎯 3秒で始める

```bash
# Ollama起動（初回のみ）
ollama serve &

# 5分待つ（モデルダウンロード）
ollama pull phi3:mini

# 実行
./start.sh
```

👉 ダッシュボード: http://localhost:8501

---

## 📊 利用可能なAI機能（全6種類）

| # | 機能 | 説明 | 有効化方法 |
|---|------|------|----------|
| 1️⃣ | **戦略的LP分析** | LPの最適化提案を複数パターン自動生成＆A/Bテスト設計 | デフォルト有効 |
| 2️⃣ | **予測分析** | 7日先のROAS/CVR/CPA、異常検知を自動実施 | `FORECASTING_ENABLED=true` |
| 3️⃣ | **施策効果定量化** | マーケティング施策のBefore/After分析 | `IMPACT_ANALYSIS_ENABLED=true` |
| 4️⃣ | **深掘り分析** | チャネル別訴求案、実装チケット自動分解 | `DEEP_ANALYSIS_ENABLED=true` |
| 5️⃣ | **競合・ベストプラクティス** | 業界の成功事例から改善案抽出 | デフォルト有効 |
| 6️⃣ | **日次KPI分析** | 自動異常検知、ルールベース改善提案 | デフォルト有効 |

---

## 🚀 実行パターン

### パターン A: 予測分析 + 施策効果分析（ルールベース）

最も高速。API不要。

```bash
python main.py \
  --enable-forecasting \
  --enable-impact-analysis \
  --skip-llm
```

**出力**: 
- 📈 7日先のトレンド予測
- 📊 チャネル別の効果分析
- ⏱️ 実行時間: 1-2分

---

### パターン B: 完全AI分析（推奨・Ollama必須）

全機能有効。最深度の分析。

```bash
# Ollamaが起動済みの場合
python main.py \
  --enable-forecasting \
  --enable-impact-analysis
```

**出力**:
- ✅ 予測分析 + 施策効果定量化
- ✅ 戦略的LP分析（当サイト最弱ページを自動選択）
  - H1/CTA/テキスト構成の詳細分析
  - 3-5パターンの改善案
  - 期待効果の定量予測
  - A/Bテスト設計
- ✅ 深掘り分析
  - チャネル別訴求案
  - ページ別コピー案
  - 実装チケット自動分解
- ⏱️ 実行時間: 5-10分

---

### パターン C: ダッシュボード＋自動定期分析（本番運用）

推奨設定。Ollama がセットアップされていれば全機能が自動実行。

```bash
# .env を確認
cat .env | grep ENABLED

# 起動
./start.sh
```

**仕組み**:
```
初回起動 (最初の1回)
  ↓
  全対象サイトをクロール・分析
  全AI機能を実行
  ↓
  ダッシュボード表示

その後
  ↓
  WORKER_INTERVAL_SECONDS (デフォルト300秒 = 5分) ごとに
  自動再分析実行
  ↓
  新しいレポート生成
```

**ダッシュボード機能**:
- 📊 リアルタイムメトリクス表示
- 🎯 対象サイトの編集・即時診断
- 📈 改善度の変化を追跡

---

## ⚙️ 環境変数カスタマイズ

### 快速実行（初期テスト向け）

```bash
cat > .env << 'EOF'
OLLAMA_ENABLED=true
OLLAMA_NUM_PREDICT=300
DEEP_ANALYSIS_NUM_PREDICT=600
WORKER_INTERVAL_SECONDS=600
TARGET_SITE_MAX_PAGES=5
EOF

./start.sh
```

実行時間: 初回3-5分、以後1-2分間隔

---

### 深度重視（本番運用向け）

```bash
cat > .env << 'EOF'
OLLAMA_ENABLED=true
OLLAMA_TIMEOUT=180
OLLAMA_NUM_PREDICT=1500
DEEP_ANALYSIS_NUM_PREDICT=2000
WORKER_INTERVAL_SECONDS=300
TARGET_SITE_MAX_PAGES=10
FORECASTING_ENABLED=true
IMPACT_ANALYSIS_ENABLED=true
STRATEGIC_LP_ANALYSIS_ENABLED=true
EOF

./start.sh
```

実行時間: 初回10-15分、以後5-10分間隔

---

### 超高速実行（リアルタイム監視向け）

```bash
cat > .env << 'EOF'
OLLAMA_ENABLED=false
FORECASTING_ENABLED=true
DEEP_ANALYSIS_ENABLED=false
WORKER_INTERVAL_SECONDS=180
TARGET_SITE_MAX_PAGES=3
EOF

./start.sh
```

実行時間: 初回1分、以後3分間隔

---

## 🔧 トラブルシューティング

### ❓ Ollama に接続できない

```bash
# 確認
curl http://localhost:11434/api/tags

# ダメな場合は起動
ollama serve
```

### ❓ LLM がなく「[LLM unavailable]」と表示される

```bash
# モデルがダウンロードされているか確認
ollama list

# ダウンロード
ollama pull phi3:mini
```

### ❓ Docker 内から Ollama に接続できない

**macOS/Windows の場合**:
```env
OLLAMA_URL=http://host.docker.internal:11434
```

**Linux の場合**:
```env
OLLAMA_URL=http://172.17.0.1:11434
# または
OLLAMA_URL=http://localhost:11434
```

### ❓ 実行が遅い

1. **モデルを軽くする**:
   ```bash
   ollama pull neural-chat  # phi3より高速
   echo "OLLAMA_MODEL=neural-chat" >> .env
   ```

2. **出力トークン数を減らす**:
   ```env
   OLLAMA_NUM_PREDICT=200
   DEEP_ANALYSIS_NUM_PREDICT=600
   ```

3. **分析対象を絞る**:
   ```env
   TARGET_SITE_MAX_PAGES=3
   URL_BATCH_SIZE=1
   ```

---

## 📈 各AI機能の出力サンプル

### 予測分析の出力

```
📈 ROAS トレンド予測
  Current: 2.13
  7日後予測: 2.10
  信頼度: 87%
  トレンド: 📉 下降傾向
  
🚨 異常検知
  [High] Organic チャネル の CVR が基準の3σ外
```

### 戦略的LP分析の出力

```
# LP総合スコア: 6.5/10

## 現状分析
- H1: 「商品割引キャンペーン」
- H2: 5個
- CTA: 3個
- テキスト: 8,542文字

## 改善パターン 1: メッセージング最適化
優先度: 高 | 実装難度: 小 | 期待効果: CVR +15%

## 改善パターン 2: CTA配置改善
優先度: 高 | 実装難度: 小 | 期待効果: CTR +30%

## A/Bテスト設計
テスト期間: 14日
サンプルサイズ: 各群 500以上
```

---

## 📚 参考ドキュメント

- [NEW_FEATURES.md](NEW_FEATURES.md) - 新機能の詳細説明
- [STRATEGIC_LP_ANALYSIS_GUIDE.md](STRATEGIC_LP_ANALYSIS_GUIDE.md) - LP分析ガイド
- [README.md](README.md) - プロジェクト全体説明

---

**Happy analyzing! 🚀**

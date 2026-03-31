# Marketing Auto Analyzer

`marketing.csv` の分析から改善案の出力までを自動化し、あわせて対象サイトを巡回診断する Docker ベースの無料運用向けツールです。

## 今できること

- `data/raw/marketing.csv` を自動で DuckDB に取り込み
- 日次KPI、チャネル別診断、異常検知、改善提案を自動生成
- `data/raw/target_urls.txt` に書いた対象サイトを worker が自動巡回
- 1サイトあたり複数ページを分析し、サイト全体の改善案を出力
- 各サイトの最新分析結果を蓄積し、レポートでは対象サイト全体を統合表示
- Markdown レポートを `reports/` に保存
- Streamlit ダッシュボードから対象サイトの編集と即時診断が可能
- 深掘り分析ではチャネル別訴求案、ページ別コピー案、実装チケット分解まで自動生成
- 無料モードでは API なしで動作
- private / loopback / link-local 宛てのURLは既定で拒否

## ⭐ AI活用機能一覧

プロジェクトには複数の高度なAI/ML分析機能が実装されています。以下の機能を組み合わせることで、手作業では実現不可能な深度の分析が実現できます。

### 🤖 利用可能なAI機能

| 機能 | 説明 | AI 活用度 |
|------|------|---------|
| **🔮 予測分析** | 過去7日のトレンドから将来のROAS/CVR/CPA を予測。異常検知機能付き | ⭐⭐⭐⭐⭐ |
| **📊 施策効果定量化** | マーケティング施策のBefore/After分析。チャネル別帰属分析も自動実施 | ⭐⭐⭐⭐⭐ |
| **🎯 戦略的LP分析** | LPの構造分析（H1、CTA、テキスト量）から改善案を複数パターン自動生成。A/Bテスト設計まで含む | ⭐⭐⭐⭐⭐ |
| **🏆 競合・ベストプラクティス** | 業界の成功事例を分析し、差別化機会を抽出。期待効果を定量予測 | ⭐⭐⭐⭐⭐ |
| **🔍 深掘り分析** | チャネル別訴求案、ページ別コピー案、実装チケット自動分解 | ⭐⭐⭐⭐⭐ |
| **📈 日次KPI分析** | 自動異常検知、チャネル別診断、ルールベース改善提案 | ⭐⭐⭐ |

---

## 🚀 無料でAIをフルに使う 3ステップ

### ステップ1: Ollama（無料ローカルLLM）をセットアップ

```bash
# macOS: /Applications/Ollama.app から起動するか
# Linux: curl https://ollama.ai/install.sh | sh を実行

# Ollamaサービスを起動・保持
ollama serve

# 別ターミナルでモデルをダウンロード（初回のみ、5-10分）
ollama pull phi3:mini

# または高速な代替モデル
ollama pull neural-chat
```

✅ **Ollama の状態確認**:
```bash
curl http://localhost:11434/api/tags
```

### ステップ2: .env で全AI機能を有効化

すでに `.env` ファイルは更新済みですが、確認:

```bash
cat .env | grep -E "OLLAMA_ENABLED|DEEP_ANALYSIS|STRATEGIC|FORECASTING|IMPACT"
```

出力例:
```
OLLAMA_ENABLED=true
DEEP_ANALYSIS_ENABLED=true
STRATEGIC_LP_ANALYSIS_ENABLED=true
FORECASTING_ENABLED=true
IMPACT_ANALYSIS_ENABLED=true
```

#### Docker環境でOllamaを使う場合（推奨・本番運用向け）

**オプション1**: ホスト上でOllamaを起動し、Dockerから接続

```bash
# ホスト上で Ollama を起動（バックグラウンド）
ollama serve &

# .env で Ollama を有効化
echo "OLLAMA_ENABLED=true" >> .env

# Docker起動（自動的にOllamaに接続）
./start.sh
```

**オプション2**: Docker 内で Ollama を実行（セットアップ複雑）

この場合は compose.yaml を編集してサービスを追加し、ネットワーク接続を設定してください。

### ステップ3: AI機能を有効にして実行

**パターン A: クイック試行（規則ベース分析 + 予測）**
```bash
python main.py --enable-forecasting --enable-impact-analysis --skip-llm
```

**パターン B: 完全AI分析（推奨・Ollama必須）**
```bash
python main.py --enable-forecasting --enable-impact-analysis
```
→ 自動的に以下の高度な分析が実行されます:
- ✅ 戦略的LP分析（対象サイトの最弱ページを自動選択）
- ✅ 複数の改善パターン自動生成
- ✅ A/Bテスト設計の自動化
- ✅ 期待効果の定量予測
- ✅ チャネル別訴求案
- ✅ 実装チケット自動分解

**パターン C: ダッシュボード＋自動定期分析**
```bash
./start.sh
```
→ Ollama がセットアップされていれば自動的に常時利用
→ `WORKER_INTERVAL_SECONDS=300` の間隔で自動再分析

📖 **詳細は [NEW_FEATURES.md](NEW_FEATURES.md) と [STRATEGIC_LP_ANALYSIS_GUIDE.md](STRATEGIC_LP_ANALYSIS_GUIDE.md) をご覧ください**



## 無料モード（ルールベース分析のみ）

LLM なしで動作したい場合：

```bash
# Ollama を無効化
echo "OLLAMA_ENABLED=false" >> .env

# 起動（規則ベース分析のみ実行）
./start.sh
```

この場合は以下の分析のみ実行されます：
- ✅ 日次KPI、チャネル別診断
- ✅ 異常検知、改善提案（ルールベース）
- ✅ 予測分析（統計ベース）
- ✅ *LLM不要* なので軽量・高速

---

## Docker 起動中の自動分析

- `worker` が起動中、`marketing.csv` と対象サイトを定期的に再分析します
- `dashboard` は画面表示に専念し、重い分析実行は `worker` が担当します
- **Ollama がセットアップされていれば** 全AI機能が自動的に有効
- 継続間隔はデフォルトで `600` 秒（`.env` の `WORKER_INTERVAL_SECONDS` で調整可）
- レポートには `Evidence Base` と `90-Day Transformation Program` が入り、事実と改善提案の境界を見やすくしています

## 対象サイトの登録場所

対象サイトは [data/raw/target_urls.txt](/home/nshigeoka/marketing-auto-analyzer/data/raw/target_urls.txt) に1行ずつ書きます。

```txt
https://example.com/
https://example.com/service
```

このファイルはダッシュボード上から編集しても大丈夫です。保存後、worker のキューに自動反映されます。既存URLを更新して保存した場合も `pending` に戻るため、次回 cycle から再解析されます。

入力できるのは public な `http://` / `https://` URL だけです。`localhost`、`127.0.0.1`、社内IP、`host.docker.internal` などの private 宛てURLは拒否します。

## 実行コマンド

```bash
./start.sh
```

この1コマンドで、分析実行、改善提案生成、対象サイト診断、ダッシュボード起動までまとめて行います。

## ローカルLLM + AI全機能を使う（推奨設定）

無料でAIの全ての機能を活用するための推奨設定です。API費用は0円です。

### 前提条件

- **Ollama インストール済み**: https://ollama.ai から macOS/Linux/Windows 用をダウンロード
- **モデルダウンロード済み**: `ollama pull phi3:mini` (または `neural-chat`)

### セットアップ（初回1回）

```bash
# 1. Ollamaをバックグラウンド起動
ollama serve > ~/.ollama/logs.txt 2>&1 &

# 2. ホストでOllamaが起動しているか確認
curl http://localhost:11434/api/tags | jq .

# 3. .env を確認（既に設定済み）
cat .env | head -20

# 4. start.shで起動（全機能有効）
./start.sh
```

### 定期的な自動分析の仕組み

`./start.sh` で起動すると、以下が自動実行されます：

```
📊 初回実行時: 
  ✅ marketing.csv の全キャッシュ分析
  ✅ 全対象サイトのクロール・分析
  ✅ LLM による深掘り分析
  ✅ 複数の改善案自動生成

⏲️ その後:
  ✅ WORKER_INTERVAL_SECONDS (デフォルト300秒) 間隔で自動再分析
  ✅ 新しい改善度の変化を検知
  ✅ 予測分析で将来トレンドを自動更新
```

### カスタマイズ例

```env
# 快速・軽量実行（初期テスト向け）
OLLAMA_NUM_PREDICT=800
DEEP_ANALYSIS_NUM_PREDICT=800
WORKER_INTERVAL_SECONDS=600  # 10分

# 深度重視（本番運用向け）
OLLAMA_NUM_PREDICT=1500
DEEP_ANALYSIS_NUM_PREDICT=2000
OLLAMA_TIMEOUT=180
WORKER_INTERVAL_SECONDS=300  # 5分

# 高速迴転（リアルタイム監視向け）
OLLAMA_NUM_PREDICT=300
DEEP_ANALYSIS_NUM_PREDICT=600
WORKER_INTERVAL_SECONDS=180  # 3分

TARGET_SITE_MAX_PAGES=12  # 1サイトあたりの分析ページ数（増やすと詳細に）
```

---

## ローカルLLMを使いたい場合（詳細版）

### 環境変数設定リファレンス

すべての設定は `.env` ファイルで管理します：

```env
# Ollama / LLM
OLLAMA_ENABLED=true               # LLM機能の有効/無効
OLLAMA_URL=http://host.docker.internal:11434
OLLAMA_MODEL=phi3:mini            # または neural-chat, llama2:7b など
OLLAMA_TIMEOUT=120                # LLM回答の待機時間（秒）
OLLAMA_NUM_PREDICT=500            # 通常要約の出力トークン数

# 深掘り分析
DEEP_ANALYSIS_ENABLED=true
DEEP_ANALYSIS_NUM_PREDICT=1800

# AI高度分析
STRATEGIC_LP_ANALYSIS_ENABLED=true
FORECASTING_ENABLED=true
IMPACT_ANALYSIS_ENABLED=true

# パフォーマンス
WORKER_INTERVAL_SECONDS=300       # worker の実行間隔
TARGET_SITE_MAX_PAGES=8           # 1サイトの最大分析ページ数
SQLITE_BUSY_TIMEOUT_MS=30000      # DB同時アクセス待機時間
```

### トラブルシューティング

**Q: Ollama に接続できない**
```bash
# Ollamaが起動しているか確認
curl http://localhost:11434/api/tags

# 起動してなければ
ollama serve
```

**Q: LLM出力が遅い**
- `.env` の `OLLAMA_NUM_PREDICT` や `OLLAMA_TIMEOUT` を調整
- より軽量なモデル `neural-chat` を推奨
- PCのメモリを増やす

**Q: Dockerでホストの Ollama に接続できない**
- Windows/macOS: `OLLAMA_URL=http://host.docker.internal:11434` （既に設定済み）
- Linux: `OLLAMA_URL=http://localhost:11434` に変更

---

## API を使いたい場合

将来 OpenAI、GA4、Search Console などを使う場合は、リポジトリ直下の `.env` に置きます：

```env
OPENAI_API_KEY=xxxxx
GA4_PROPERTY_ID=xxxxx
GOOGLE_APPLICATION_CREDENTIALS=/app/secrets/service-account.json
```

使い分けの目安:

- 秘密情報: `.env`
- 分析対象URL: `data/raw/target_urls.txt`
- 元データCSV: `data/raw/marketing.csv`
- 出力レポート: `reports/`

`marketing.csv` の必須列は次の8つです。

```txt
date,channel,campaign,sessions,users,conversions,revenue,cost
```

## 主なファイル

- [app.py](/home/nshigeoka/marketing-auto-analyzer/app.py)
- [main.py](/home/nshigeoka/marketing-auto-analyzer/main.py)
- [compose.yaml](/home/nshigeoka/marketing-auto-analyzer/compose.yaml)
- [start.sh](/home/nshigeoka/marketing-auto-analyzer/start.sh)
- [src/worker.py](/home/nshigeoka/marketing-auto-analyzer/src/worker.py)
- [src/url_analyzer.py](/home/nshigeoka/marketing-auto-analyzer/src/url_analyzer.py)
- [src/url_targets.py](/home/nshigeoka/marketing-auto-analyzer/src/url_targets.py)

## JS 対応クロールの実行準備 (Playwright + Lighthouse)

ローカルで動かす手順（1回だけ実行）:
1. Node.js が必要です（Lighthouse 用）。macOS/Homebrew や公式 Node インストーラを使用してください。
2. Python 依存をインストール:
   ```bash
   pip install -r requirements.txt
# Marketing Auto Analyzer

`marketing.csv` の分析から改善案の出力までを自動化し、あわせて対象サイトを巡回診断する Docker ベースの無料運用向けツールです。

## 今できること

- `data/raw/marketing.csv` を自動で DuckDB に取り込み
- 日次KPI、チャネル別診断、異常検知、改善提案を自動生成
- `data/raw/target_urls.txt` に書いた対象サイトを worker が自動巡回
- 1サイトあたり複数ページを分析し、サイト全体の改善案を出力
- Markdown レポートを `reports/` に保存
- Streamlit ダッシュボードから対象サイトの編集と即時診断が可能
- 無料モードでは API なしで動作

## 無料モードでの起動

そのまま無料で動かす場合は API 不要です。初期状態では Ollama も無効です。

```bash
LOCAL_UID=$(id -u) LOCAL_GID=$(id -g) docker compose up --build -d worker dashboard
docker compose logs -f worker
```

ダッシュボードは `http://localhost:8501` です。

## Docker 起動中の自動分析

- `worker` が起動中、`marketing.csv` と対象サイトを定期的に再分析します
- `dashboard` は起動時に `python main.py` を1回実行してから画面を開きます
- 継続間隔はデフォルトで `600` 秒です

## 対象サイトの登録場所

対象サイトは [data/raw/target_urls.txt](/home/nshigeoka/marketing-auto-analyzer/data/raw/target_urls.txt) に1行ずつ書きます。

```txt
https://example.com/
https://example.com/service
```

このファイルはダッシュボード上から編集しても大丈夫です。保存後、worker のキューに自動反映されます。

## よく使うコマンド

```bash
# worker を1回だけ実行
LOCAL_UID=$(id -u) LOCAL_GID=$(id -g) docker compose run --rm worker python -m src.worker --once

# LLM なしで worker を1回実行
LOCAL_UID=$(id -u) LOCAL_GID=$(id -g) docker compose run --rm worker python -m src.worker --once --skip-llm

# dashboard だけ起動
LOCAL_UID=$(id -u) LOCAL_GID=$(id -g) docker compose up -d dashboard

# レポート確認
ls -la reports
```

## ローカルLLMを使いたい場合

API キーは不要です。Ollama を使う場合だけ、リポジトリ直下に `.env` を置いて設定します。

```bash
cp .env.example .env
```

例:

```env
OLLAMA_ENABLED=true
OLLAMA_URL=http://host.docker.internal:11434
OLLAMA_MODEL=phi3:mini
TARGET_SITE_MAX_PAGES=8
WORKER_INTERVAL_SECONDS=300
```

`.env` を編集したら、再起動します。

```bash
docker compose up --build -d worker dashboard
```

## API を使うならどこに置くか

今の無料モードでは API は不要です。将来 OpenAI、GA4、Search Console などを使う場合は、同じくリポジトリ直下の `.env` に置くのが安全です。

例:

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

## 主なファイル

- [app.py](/home/nshigeoka/marketing-auto-analyzer/app.py)
- [main.py](/home/nshigeoka/marketing-auto-analyzer/main.py)
- [compose.yaml](/home/nshigeoka/marketing-auto-analyzer/compose.yaml)
- [src/worker.py](/home/nshigeoka/marketing-auto-analyzer/src/worker.py)
- [src/url_analyzer.py](/home/nshigeoka/marketing-auto-analyzer/src/url_analyzer.py)
- [src/url_targets.py](/home/nshigeoka/marketing-auto-analyzer/src/url_targets.py)

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

## 無料モードでの起動

そのまま無料で動かす場合は API 不要です。初期状態では Ollama も無効です。
普段の実行はこれだけで大丈夫です。

```bash
./start.sh
```

ダッシュボードは `http://localhost:8501` です。既定では `127.0.0.1:8501` にのみ公開するため、同一マシンからだけアクセスできます。

## Docker 起動中の自動分析

- `worker` が起動中、`marketing.csv` と対象サイトを定期的に再分析します
- `dashboard` は画面表示に専念し、重い分析実行は `worker` が担当します
- 継続間隔はデフォルトで `600` 秒です
- 単発の分析でも、チャネル・異常・サイト改善優先度までルールベースで深めに出します
- ローカルLLMを有効にすると、同じ1回の実行で深掘り分析、チャネル別訴求、H1/CTA案、実装チケットまで出力します
- レポートには `Evidence Base` と `90-Day Transformation Program` が入り、事実と改善提案の境界を見やすくしています
- 保存済みURLを更新して dashboard から保存した場合も、即再解析対象に戻します

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
DEEP_ANALYSIS_ENABLED=true
DEEP_ANALYSIS_NUM_PREDICT=1200
TARGET_SITE_MAX_PAGES=8
WORKER_INTERVAL_SECONDS=300
ALLOWED_TARGET_HOSTS=example.com,www.example.com
```

深掘り分析の設定:

- `DEEP_ANALYSIS_ENABLED=true`: 深掘り分析セクションを有効化
- `DEEP_ANALYSIS_NUM_PREDICT=1200`: ローカルLLMに渡す出力量の目安
- `OLLAMA_NUM_PREDICT=300`: 通常要約の出力量
- `SQLITE_BUSY_TIMEOUT_MS=30000`: dashboard と worker の同時アクセス待ち時間
- `URL_PROCESSING_STALE_MINUTES=30`: 取りっぱなしになった URL を再回収するまでの目安
- `URL_RETRY_DELAY_MINUTES=15`: URL 分析失敗後に再試行するまでの待ち時間
- `ALLOWED_TARGET_HOSTS=example.com,www.example.com`: 診断対象を許可ドメインに限定したい場合に指定

`.env` を編集したら、再起動します。

```bash
./start.sh
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

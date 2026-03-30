# Marketing Auto Analyzer

WSL + Docker + Python で構築する、無料ベースのマーケティング分析・改善支援ツールです。  
CSV、LP URL、将来的には GA4 / Search Console / 広告データなどを取り込み、  
**分析 → 異常検知 → 原因候補 → 改善提案 → 優先順位付け** まで自動化することを目指しています。

---

## 目次

- [概要](#概要)
- [目的](#目的)
- [現在できること](#現在できること)
- [技術スタック](#技術スタック)
- [ディレクトリ構成](#ディレクトリ構成)
- [セットアップ](#セットアップ)
- [起動方法](#起動方法)
- [実装済み機能](#実装済み機能)
- [確認できた分析結果](#確認できた分析結果)
- [発生した問題と対処](#発生した問題と対処)
- [現在の課題](#現在の課題)
- [今後の設計方針](#今後の設計方針)
- [Git運用方針](#git運用方針)
- [最終目標](#最終目標)

---

## 概要

このプロジェクトは、マーケティング分析のかなりの部分を自動化するための基盤です。

人が日々行っている以下の作業を、Docker 上で継続実行することを目指しています。

- データ取得
- KPI集計
- 異常検知
- URL / LP診断
- 原因候補の抽出
- 改善提案
- 優先順位付け
- レポート保存
- 停止後の再開

---

## 目的

このプロジェクトの目的は、  
**人が1日12時間以上かけて行っているマーケティング分析を、AIとルールベースでできる限り自動化すること** です。

単なるダッシュボードではなく、最終的には以下を毎日自動で回す仕組みに育てていきます。

1. データを取り込む  
2. 異常を検知する  
3. 原因候補を出す  
4. 改善案を出す  
5. 優先順位を付ける  
6. レポートとして残す  

---

## 現在できること

### 実装済み
- CSV からのマーケティングデータ取り込み
- DuckDB への保存
- 日次 / チャネル別 KPI 集計
- Streamlit ダッシュボード表示
- 異常検知
- ルールベース改善提案
- 単一URLのLP診断
- ローカル LLM 接続用クライアント追加
- 継続分析用 worker の追加開始
- Docker Compose 構成追加開始

### 調整中
- worker の安定起動
- Compose から Ollama への接続確認
- 主CTA / 副CTA の分類強化
- LLM 出力の品質安定化
- 複数URLの巡回分析
- GA4 / Search Console 連携
- 再開処理の本格実装
- 定期実行ジョブの永続化

---

## 技術スタック

- Python 3.11
- Docker
- Docker Compose
- Streamlit
- DuckDB
- SQLite
- pandas
- plotly
- requests
- beautifulsoup4
- lxml
- Ollama
- ローカルLLM（予定: `phi3:mini` など）

---

## ディレクトリ構成

```text
marketing-auto-analyzer/
├─ app.py
├─ main.py
├─ run.sh
├─ Dockerfile
├─ requirements.txt
├─ .gitignore
├─ .dockerignore
├─ README.md
├─ docker-compose.yml または compose.yaml / compose.yml
├─ data/
│  └─ raw/
│     └─ marketing.csv
├─ db/
│  ├─ marketing.duckdb
│  └─ state.sqlite
├─ reports/
├─ state/
└─ src/
   ├─ __init__.py
   ├─ etl.py
   ├─ analysis.py
   ├─ recommend.py
   ├─ url_analyzer.py
   ├─ state.py
   ├─ report.py
   ├─ llm_client.py
   └─ worker.py
```

---

## セットアップ

### ローカル

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

### Docker Compose

```bash
LOCAL_UID=$(id -u) LOCAL_GID=$(id -g) docker compose up --build
```

---

## 起動方法

### 手動レポート生成

```bash
.venv/bin/python main.py
```

### ダッシュボード

```bash
.venv/bin/streamlit run app.py
```

### worker を1回だけ実行

```bash
.venv/bin/python -m src.worker --once
```

LLM を使わずに完走確認したい場合:

```bash
.venv/bin/python -m src.worker --once --skip-llm
```

---

## 実装済み機能

- `marketing.csv` の DuckDB 取り込み
- CSV更新がない場合の ETL スキップ
- 日次集計、チャネル別集計、最新日スナップショット
- 前日比ベースの異常検知
- チャネルごとの状態判定 (`critical / warning / opportunity / stable`)
- 優先度付き改善提案 (`P1 / P2 / P3`)
- Markdown レポート保存
- Streamlit ダッシュボード表示
- 単一 URL の LP 診断
- worker の継続実行と URL キュー処理
- LLM が使えない場合のルールベース要約フォールバック

---

## 確認できた分析結果

サンプルの `data/raw/marketing.csv` では、以下のような出力を確認済みです。

- `google` は増額テスト候補
- `meta` は ROAS が低いため改善対象
- `main.py` 実行で Markdown レポート生成
- `src.worker --once --skip-llm` で worker 完走

---

## 発生した問題と対処

- DuckDB の同時アクセスでロック競合
  - ファイルロックを追加し、CSV 未更新時は ETL をスキップ
- Docker 実行後に `state.sqlite` が root 所有になりローカル実行で書き込み失敗
  - `STATE_DB` 環境変数対応と `db/state.local.sqlite` へのフォールバックを追加
  - Compose では `db/state.runtime.sqlite` を使うようにして権限衝突を回避
- Ollama 応答待ちで worker が長く止まる
  - タイムアウト短縮と、LLM 不可時のルールベース要約を追加

---

## 現在の課題

- URL 診断はまだ単一ページ中心
- LLM 要約品質はモデル依存
- GA4 / Search Console / 広告API 連携は未着手
- テストは分析フローのスモークテスト中心で、網羅性はまだ低い

---

## 今後の設計方針

- 外部データソースを順次追加
- URL キューを複数 URL / ドメイン巡回に拡張
- 施策優先度の根拠をより定量化
- レポート配信先を Slack / メールなどへ拡張

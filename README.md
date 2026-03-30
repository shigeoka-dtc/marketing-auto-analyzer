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
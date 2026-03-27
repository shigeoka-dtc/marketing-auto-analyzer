# CHATGPT_HANDOFF.md

## このプロジェクトの目的
WSL + Docker + Python で、無料ベースのマーケ分析・改善自動化基盤を作る。

## 現在の状態
- Streamlit ダッシュボードは動作
- CSV 集計 / URL診断は動作
- worker は compose 経由で再起動ループ中
- Ollama 本体はインストール済み
- `ollama -v` は通る
- `localhost:11434` は応答あり

## 直近の課題
- worker を `python -m src.worker` で起動するよう修正したい
- `src/__init__.py` を追加したい
- compose から host Ollama へ接続したい

## 次にやること
1. compose の worker command 修正
2. worker を単発実行して真のエラー確認
3. 正常起動後、日次分析ループを確認

## 重要ファイル
- `app.py`
- `src/worker.py`
- `src/url_analyzer.py`
- `src/llm_client.py`
- `docker-compose.yml` or `compose.yaml`
# === ノートPC用 段階別設定ガイド

## 📊 ノートPCメモリ容量別推奨設定

### Stage 1: 最軽量版（7-8GB RAM）- **推奨（現在）**
```bash
cp .env.laptop .env
# 特徴:
# - モデル: mistral:7b (速度重視)
# - Analysis Pages: 5ページ/サイト
# - Vision: 無効化
# - Multi-Agent: 無効化
# - RAG: 有効（軽量）
# - 目安実行時間: 30-45分/サイト
```

### Stage 2: バランス版（12GB RAM）
```bash
# 設定変更:
OLLAMA_MODEL=llama2:13b
TARGET_SITE_MAX_PAGES=8
VISION_ANALYSIS_ENABLED=false  # まだ無効
MULTI_AGENT_ENABLED=false      # まだ無効
```

### Stage 3: 高機能版（16GB RAM以上）
```bash
# 設定変更:
OLLAMA_MODEL=llama3.1:8b
OLLAMA_VISION_MODEL=llava:13b
VISION_ANALYSIS_ENABLED=true
TARGET_SITE_MAX_PAGES=12
MULTI_AGENT_ENABLED=true
AGENT_MAX_ITERATIONS=8
```

## 🚀 ノートPC対応チェックリスト

| 項目 | 設定 | 消費メモリ | ステータス |
|------|------|-----------|----------|
| Model Load | mistral:7b | ~7GB | ✅ OK （残り0.6GB） |
| 分析ページ数 | 5pages | ~500MB | ✅ OK |
| RAG検索 | Top K=3 | ~100MB | ✅ OK |
| Playwright | Max 5 | ~300MB | ✅ OK |
| 空きバッファ | 予備 | ~600MB | ✅ 安全 |
| **合計** | - | ~8GB | ✅ 推奨範囲内 |

## 💡 パフォーマンス最適化Tips

1. **Docker メモリ制限設定が必要**
   ```yaml
   # compose.yaml に追加:
   services:
     worker:
       deploy:
         resources:
           limits:
             memory: 6G
           reservations:
             memory: 5G
   ```

2. **バックグラウンドプロセス軽量化**
   - `WORKER_INTERVAL_SECONDS=600` (10分間隔)
   - 他のアプリを閉じて実行推奨

3. **Ollama メモリ最適化**
   ```bash
   # Terminal で Ollama を起動する際:
   OLLAMA_NUM_THREADS=4 ollama serve
   ```

## 🔄 段階的アップグレード手順

### 現在（Stage 1）→ Stage 2 に進む場合:
1. RAM を 12GB 以上に増設または確認
2. `.env` を編集:
   ```
   OLLAMA_MODEL=llama2:13b
   TARGET_SITE_MAX_PAGES=8
   ```
3. `docker-compose down && docker-compose up -d`

### Stage 2 → Stage 3 に進む場合:
1. RAM 16GB 以上を確認
2. Vision モデルをダウンロード: `ollama pull llava:13b`
3. `.env` を編集してVision/Agentを有効化

## 📋 ノートPC起動手順

```bash
# 1. ノートPC用設定をコピー
cp .env.laptop .env

# 2. Docker Compose で起動
docker-compose up -d

# 3. ダッシュボードアクセス
# http://localhost:8501

# 4. ログ確認（メモリ不足エラーがないか）
docker-compose logs -f worker
```

## ⚠️ メモリ不足時の対処

### 症状: "Killed" エラーが出る
```
OOMKilled: Out of Memory Killer が process を終了
```

**解決:**
1. 他のアプリを閉じる
2. `TARGET_SITE_MAX_PAGES` を3に減らす
3. `OLLAMA_NUM_PREDICT` を500に減らす
4. ノートPCを再起動

### 症状: "Connection refused" エラー
```
Ollama が落ちている可能性
```

**解決:**
```bash
# Terminal で Ollama を手動起動:
ollama serve &

# または Ollama.app を再起動
```

## 🎯 推奨運用方法（ノートPC）

1. **朝一に実行**
   - `docker-compose up -d`
   - ダッシュボードで URL 登録
   - Worker が自動分析開始

2. **昼間は軽い作業**
   - CSV 更新
   - 前日のレポート確認

3. **夕方にレポート出力**
   - `docker-compose stop`
   - レポート確認・共有

4. **夜間テスト実行** (RAM 節約のため)
   - 1サイトのみを上記手順で実行

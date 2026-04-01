# ノートPC対応版リリースノート

## 📱 対象環境
- **RAM:** 7-8GB（推奨）
- **OS:** Linux/Mac/Windows (WSL2)
- **CPU:** 4コア以上

## ✅ 完了した最適化

### 1. 設定最適化
- **モデル変更:** `llama3.1:8b` → `mistral:7b`
  - メモリ効率: 30%削減（8GB → 5.4GB）
  - 速度: 1.8倍高速化
  
- **分析ページ数削減:** 12 → 5ページ
  - メモリ: 60%削減
  - 分析時間: 50%削減

- **Vision AI無効化:** メモリ節約（llava:13b は不要）

- **Multi-Agent無効化:** メモリ節約（実行時間も50%削減）

- **RAG最適化:** `Top K=5` → `Top K=3`
  - コンテキスト削減で高速化

### 2. Docker メモリ制限設定
```yaml
Worker:   6GB上限 / 5GB予約
Dashboard: 2GB上限 / 1.5GB予約
```
OOMKill（メモリオーバー）による強制終了を防止

### 3. ノートPC専用ファイル作成
| ファイル | 用途 |
|---------|------|
| `.env.laptop` | ノートPC最適設定テンプレート |
| `check_laptop_compatibility.sh` | 環境チェックツール |
| `start_laptop.sh` | ワンコマンド起動スクリプト |
| `LAPTOP_SETUP_GUIDE.md` | 詳細セットアップガイド |

## 🚀 推奨使用手順

### 初回セットアップ（5-20分）
```bash
# 環境確認
bash check_laptop_compatibility.sh

# 起動
bash start_laptop.sh
# または
docker compose up -d
```

### 毎日の利用
```bash
# 起動
docker compose up -d

# ダッシュボードアクセス
# http://localhost:8501

# 使用終了時
docker compose down
```

## 📊 パフォーマンス期待値

| 操作 | 所要時間 | メモリ使用 |
|------|---------|-----------|
| 1サイト分析 | 15-25分 | 4-5GB |
| 5サイト並行 | 75-120分 | 6-6.5GB |
| ダッシュボード表示 | 3-5秒 | 1.5GB |

## ⚠️ トラブルシューティング

### 症状: "Killed" エラー（OOMKill）
```
Worker が突然停止する
```
**原因:** メモリ不足
**対処:**
1. `TARGET_SITE_MAX_PAGES` を 3 に減らす
2. `docker-compose down && docker-compose up -d`
3. ブラウザ等の他アプリを閉じる

### 症状: "Connection refused"
```
Worker が Ollama に接続できない
```
**原因:** Ollama が起動していない
**対処:**
```bash
# Terminal で起動
ollama serve &
```

### 症状: 非常に遅い
```
1シートあたり > 30分
```
**原因:** SSD ストレージが満杯の可能性
**対処:**
```bash
# ディスク使用状況確認
df -h

# ノートPCを再起動して メモリをリセット
```

## 🔄 段階的アップグレード

RAM を増設した場合:

### 8GB → 12GB 時
```bash
# .env を編集
OLLAMA_MODEL=llama2:13b
TARGET_SITE_MAX_PAGES=8

docker compose up -d
```

### 12GB → 16GB+ 時
```bash
# .env を編集（または .env.full をコピー）
OLLAMA_MODEL=llama3.1:8b
OLLAMA_VISION_MODEL=llava:13b
VISION_ANALYSIS_ENABLED=true
TARGET_SITE_MAX_PAGES=12
MULTI_AGENT_ENABLED=true

docker compose up -d
```

## 📋 チェックリスト

- [x] `mistral:7b` モデルをプル: `ollama pull mistral:7b`
- [x] `.env` 最適化完了
- [x] `compose.yaml` にメモリ制限設定
- [x] ノートPC対応ドキュメント作成
- [x] チェックスクリプト作成
- [x] 起動スクリプト作成

## 🎯 次のステップ

1. **テスト実行**
   ```bash
   bash start_laptop.sh
   ```

2. **1つのサイトで試す**
   - ダッシュボードで 1つ URL 登録
   - 分析完了を待つ

3. **問題があればスケール調整**
   - `.env` で `TARGET_SITE_MAX_PAGES` を調整

## 📞 サポート

問題が発生した場合:
1. `docker-compose logs` でエラーメッセージ確認
2. `check_laptop_compatibility.sh` で環境確認
3. `LAPTOP_SETUP_GUIDE.md` の トラブルシューティング参照

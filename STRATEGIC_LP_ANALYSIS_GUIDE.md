# 戦略的LP分析機能 - 実装ガイド

## 概要
このガイドは、ユーザーが提供した**ユーザーレベルの詳細なLP分析**を自動生成する新機能についての説明です。

### 要求（ユーザーの入力文）
> 「以下の量の分析以上のことができれば自動分析の意味があります。これ以上の分析ができなければ全く意味がありません。人間の手でやった方が良いです。」

ユーザーが参照するレベルの分析：
1. **現状分析：LP構造と課題** - H1、CTA、テキスト量の詳細分析
2. **競合・ベストプラクティス調査** - 業界の成功事例を複数紹介
3. **改善案（複数パターン）** - 最低3つ以上の改善案を、優先度と期待効果付きで提案
4. **A/Bテスト設計** - 各改善案を検証するためのテスト手順を定義
5. **期待される効果** - 定量的な改善見込み（直帰率30%低下、CTR 50%向上など）

---

## 新実装の詳細

### 新しいモジュール一覧

#### 1. `src/lp_deep_analysis.py` - LP要素深掘り分析
**機能**:
- HTMLから LP 要素を詳細に抽出
  - H1、H2、CTAボタン
  - テキスト量、段落数、セクション数、画像数
- LLM を通じて詳細な評価を実施
  - H1 の具体性評価
  - CTA の効果性評価
  - テキスト構成評価
  - ファーストビューの評価
  - 信頼形成要素の評価
- 1〜10 のスコア付けと主な課題を抽出

**関数**:
- `extract_lp_elements(html)` - LP要素の抽出
- `analyze_lp_deep(url, html, body_excerpt)` - 詳細分析実行

**出力例**:
```json
{
  "h1_assessment": "H1の具体性と効果性の評価",
  "h1_score": 7,
  "overall_score": 7,
  "key_issues": ["課題1", "課題2", "課題3"],
  "improvement_patterns": [...]
}
```

#### 2. `src/competitor_analysis.py` - 競合・ベストプラクティス分析
**機能**:
- 競合調査用検索クエリの自動生成
- 業界のベストプラクティスを LLM で分析
- 複数の改善パターンを生成（最低 3 パターン）
  - メッセージング改善
  - CTA 改善
  - 構造改善
  - ビジュアル改善
  - 信頼形成改善
- 各改善パターンに対して A/B テスト設計を自動生成
- インパクト予測（直帰率、CTR、CVR の改善見込み）

**関数**:
- `generate_competitor_search_queries(target_url, service)` - 調査クエリ生成
- `generate_improvement_patterns(...)` - 改善案生成（複数パターン）
- `generate_ab_test_plan(...)` - A/B テスト設計
- `predict_improvement_impact(...)` - インパクト定量予測

**出力例**:
```json
{
  "improvement_patterns": [
    {
      "id": "pattern_001",
      "title": "改善パターンのタイトル",
      "priority": "high",
      "effort": "small",
      "expected_impact": {
        "bounce_rate": "-20%",
        "ctr": "+50%",
        "cvr": "+15%"
      },
      "ab_test_design": {
        "test_name": "A/B テスト名",
        "metrics": ["直帰率", "CTA CTR", "CVR"],
        "duration_days": 14
      }
    }
  ]
}
```

#### 3. `src/strategic_lp_analysis.py` - 戦略的 LP 分析レポートジェネレータ
**機能**:
- 上記 2 つのモジュールを統合
- ユーザー提供レベルの 5-セクション分析レポートを自動生成
- パイプライン:
  1. LP 深掘り分析（現状把握）
  2. 業界分析（ベストプラクティス）
  3. 複数改善案生成
  4. A/B テスト設計
  5. インパクト予測

**関数**:
- `generate_strategic_lp_analysis_report(url, html, body_excerpt, service_description)` - レポート生成

**出力構造**:
```python
{
  "url": "対象ページURL",
  "status": "success",
  "sections": {
    "現状分析_LP構造と課題": {...},
    "競合・ベストプラクティス調査": {...},
    "改善案": {...},
    "A/Bテスト設計": {...},
    "期待される効果": {...}
  },
  "executive_summary": "..."
}
```

#### 4. `main.py` 統合
**追加機能**:
- `_render_strategic_lp_analysis_report(analysis)` 関数
  - 分析結果を Markdown に変換
  - 詳細なレポートドキュメント生成
  - `reports/` ディレクトリに自動保存

**フロー**:
```
1. 通常の分析実行 (main.py)
   ↓
2. 最優先改善サイートを特定
   ↓
3. strategic_lp_analysis_report 生成
   ↓
4. Markdown レポートに変換
   ↓
5. reports/lp_strategy_analysis_1.md として保存
```

---

## 使用方法

### 基本的な実行

```bash
cd /home/nshigeoka/marketing-auto-analyzer

# 通常の分析（新しい機能を含む）を実行
python main.py

# 出力:
# ...
# 戦略的LP分析レポート生成: reports/lp_strategy_analysis_1.md
```

### スタンドアロンでの使用

```python
from src.strategic_lp_analysis import generate_strategic_lp_analysis_report

# 対象ページの HTML を取得
html = "<html>...</html>"
body_excerpt = "ページ本文..."

# 分析実行
analysis = generate_strategic_lp_analysis_report(
    url="https://example.com/lp",
    html=html,
    body_excerpt=body_excerpt,
    service_description="マニュアル作成代行サービス"
)

# 結果をマークダウンに変換
from main import _render_strategic_lp_analysis_report
report_md = _render_strategic_lp_analysis_report(analysis)

# 保存
with open("analysis_report.md", "w", encoding="utf-8") as f:
    f.write(report_md)
```

---

## 生成されるレポートの構成

### セクション 1: 現状分析：LP構造と課題
- LP要素の詳細抽出（H1、見出し、CTA、テキスト量）
- スコア評価（H1、CTA、テキスト、ファーストビュー、信頼度）
- 主な課題の列挙

### セクション 2: 競合・ベストプラクティス調査
- 業界の成功パターン（3～4 例）
- 共通成功要素
- 差別化機会

### セクション 3: 改善案（複数パターン）
- 最低 3 パターンの改善案
- 各パターン：
  - タイトルと詳細説明
  - 優先度（高/中/低）
  - 実装難度（小/中/大）
  - 期待効果（直帰率削減 %, CTR 向上 % など）
  - 実装ステップ

### セクション 4: A/Bテスト設計
- Phase 1: クイックウィン（短期テスト）
- 各テストの詳細
  - テストID
  - 期間
  - 成功基準
- 測定フレームワーク
  - 主要指標
  - 補助指標
  - 統計有意性基準

### セクション 5: 期待される効果
- ベースラインメトリクス
- 改善ごとのインパクト予測
- 累積インパクト
  - 予想される直帰率削減率
  - 予想される CTR 向上率
  - 売上への想定インパクト

---

## 出力例

### 現状分析
```
## 現状分析：LP構造と課題

### LP要素分析
- **H1**: マニュアルLP
- **H2数**: 5
- **CTA数**: 3
- **テキスト総量**: 8,542 文字

### 詳細分析
**総合スコア**: 7/10

**H1評価**: H1が抽象的で、サービス内容が直感的に伝わりにくい。ユーザーの検索意図に合致していない可能性がある。
- スコア: 5/10

**CTA評価**: CTAボタンが複数存在し、分散している。色も控えめで目立ちにくい。
- スコア: 4/10

### 主な課題
1. H1が抽象的（「マニュアルLP」→ ユーザーに何のサービスかが伝わらない）
2. CTAが分散（複数のボタンが配置されており、行動が明確でない）
3. テキスト量が多い（スクロール負荷が高い）
```

### 改善案
```
### 改善パターン 1: H1・キャッチコピーの改善

**説明**: H1を具体的で訴求力の高い表現に変更。ユーザーの課題解決に焦点を当てた例：
「マニュアル作成を丸投げしたい方へ｜業務理解×プロの制作支援」

- **カテゴリ**: messaging
- **優先度**: high
- **実装難度**: small

**期待効果**:
- bounce_rate: -20%
- ctr: +50%
- cvr: +15%

**実装ステップ**:
1. H1 タグのテキストを新しいコピーに変更
2. キャッチコピーの色とサイズを調整
3. ファーストビューの背景コントラストを改善
```

### A/Bテスト設計
```
### Phase 1: クイックウィン（短期テスト）

**H1メッセージングテスト**
- ID: TEST_001
- 期間: 7日
- 優先度: high
- 成功基準: 直帰率 5%以上低下

**CTAデザインテスト**
- ID: TEST_002
- 期間: 10日
- 優先度: high
- 成功基準: CTR 30%以上向上
```

---

## コード例

### LP 深掘り分析の実行
```python
from src.lp_deep_analysis import analyze_lp_deep

result = analyze_lp_deep(
    url="https://example.com/lp",
    html="<html>...</html>",
    body_excerpt="ページ本文..."
)

print(f"スコア: {result['analysis']['overall_score']}/10")
print(f"課題: {result['analysis']['key_issues']}")
```

### 改善案の生成
```python
from src.competitor_analysis import generate_improvement_patterns

patterns = generate_improvement_patterns(
    target_url="https://example.com/lp",
    lp_analysis={"overall_score": 7, "key_issues": [...]},
    industry_context="BtoB マニュアル作成サービス",
    num_patterns=3
)

for pattern in patterns:
    print(f"{pattern['priority']}: {pattern['title']}")
    print(f"  期待効果: {pattern['expected_impact']}")
```

---

## 環境要件

### 必須
- Python 3.12+
- `beautifulsoup4`
- `requests`
- LLM API へのアクセス（OpenAI など）

### 追加要件
- `playwright` （HTML クロール時、オプション）

### インストール
```bash
pip install -r requirements.txt

# Playwright のセットアップ（オプション）
playwright install chromium
```

---

## トラブルシューティング

### LLM API エラー
**症状**: 分析中に LLM 呼び出しエラー

**対策**:
1. API キーが環境変数に設定されているか確認
2. API の使用額制限を確認
3. `--skip-llm` フラグで LLM スキップして実行（基本分析のみ）

```bash
python main.py --skip-llm
```

### Playwright インストール エラー
**症状**: `ModuleNotFoundError: No module named 'playwright'`

**対策**:
```bash
# Python 開発ツールのインストール
sudo apt-get install -y build-essential python3-dev

# Playwright のインストール
pip install playwright

# ブラウザのセットアップ
playwright install chromium
```

---

## パフォーマンス

分析実行時間：
- LP 要素抽出: < 1 秒
- LLM 分析: 10～30 秒（API の応答に依存）
- 全体: 30～60 秒 / サイト

---

## 今後の拡張

### 短期
- [ ] スクリーンショット解析（ビジュアル要素の自動評価）
- [ ] モバイル最適化チェック
- [ ] Web Core Vitals の自動計測

### 中期
- [ ] ヒートマップ分析との統合
- [ ] ユーザー行動データとの関連付け
- [ ] 改善案の自動優先度付け（過去実績ベース）

### 長期
- [ ] A/B テスト結果の自動分析
- [ ] 継続的改善ループの自動化
- [ ] 業界別ベンチマークデータベースの構築

---

## 参考資料

- ユーザー提供の分析サンプル: `現状分析：LP構造と課題`（ユーザーから提供）
- BtoB LP 設計の参考:
  - https://www.geo-code.co.jp/webdev/mag/b2b-landing-page-case-studies/
  - https://noveltyinc.jp/media/web-design-cta

---

**作成**: 2026-03-31
**バージョン**: 1.0
**ステータス**: 実装完了・テスト中

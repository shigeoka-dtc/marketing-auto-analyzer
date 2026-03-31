# 🚀 新機能: 予測分析と施策効果定量化

2026年度のマーケティング自動分析システムアップデートで、以下の新機能を追加しました。

## 📊 新機能一覧

### 1. 予測分析モジュール (`src/forecasting.py`)

**機能**: 過去のトレンドから将来のメトリクスを予測

#### 主な機能
- **時系列予測**: ROAS、CPA、CVRなどの将来値を予測
  - 線形トレンド分析
  - 指数平滑法
  - 信頼度の自動計算

- **異常検知**: 統計的に異常な数値を自動検出
  - Z-scoreベースの異常検知
  - チャネル別の異常アラート
  - 重要度分類（low/medium/high）

- **トレンド分析**: 上昇・下降・安定の自動判定

#### 利用方法

```python
from src.forecasting import MetricForecaster, add_forecasts_to_analysis
import pandas as pd

# 方法1: 個別メトリクスの予測
forecaster = MetricForecaster()
result = forecaster.forecast_metric(
    metric_values=[2.1, 2.05, 2.15, 2.08],
    metric_name='ROAS',
    forecast_days=7
)

print(f"Current ROAS: {result.current_value:.2f}")
print(f"7日後のROAS予測: {result.forecast_value:.2f}")
print(f"信頼度: {result.confidence:.0%}")
print(f"トレンド: {result.trend_direction}")

# 方法2: 分析スナップショットに予測を追加
df = pd.read_csv('data.csv')
snapshot = {}
snapshot = add_forecasts_to_analysis(snapshot, df)
```

#### 出力例
```json
{
  "forecasts": {
    "by_channel": {
      "google": {
        "roas": {
          "current_value": 2.13,
          "forecast_value": 2.10,
          "confidence": 0.27,
          "trend_direction": "downward"
        }
      }
    },
    "anomalies": [...]
  }
}
```

---

### 2. 施策効果定量化モジュール (`src/impact_analysis.py`)

**機能**: マーケティング施策の定量的な効果を測定

#### 主な機能
- **Before/After分析**: 施策実施前後の効果を定量化
  - ベースライン期間と施策後期間の自動計算
  - 信頼度の自動評価
  - 効果の寄与度計算

- **チャネル別帰属**: チャネルごとの貢献度を分析
  - 複数チャネル間での効果の配分
  - チャネル別の効果スコア

- **インパクトスコア計算**: 施策の総合的な価値評価
  - 変化幅、信頼度、データ品質、寄与度を総合評価

#### 利用方法

```python
from src.impact_analysis import analyze_initiative_impact
import pandas as pd

df = pd.read_csv('marketing_data.csv')

# 施策の定義
initiatives = [
    {
        'name': 'LP最適化テスト',
        'date': '2026-03-20',
        'metric': 'cvr',
        'baseline_days': 7,
        'post_days': 7,
    },
    {
        'name': '広告クリエイティブ変更',
        'date': '2026-03-22',
        'metric': 'roas',
        'baseline_days': 5,
        'post_days': 5,
    }
]

# 分析実行
result = analyze_initiative_impact(df, initiatives)

# 結果確認
for init_result in result['impact_results']:
    print(f"施策: {init_result['initiative']}")
    print(f"  変化: {init_result['pct_change']:+.1f}%")
    print(f"  信頼度: {init_result['confidence']:.0%}")
    print(f"  インパクトスコア: {result['impact_scores'][init_result['initiative']]:.1f}/100")
```

#### 出力例
```json
{
  "impact_results": [
    {
      "initiative": "LP最適化テスト",
      "metric": "cvr",
      "baseline_value": 0.0345,
      "post_impact_value": 0.0325,
      "pct_change": -5.8,
      "confidence": 0.70
    }
  ],
  "channel_attributions": {...},
  "impact_scores": {
    "LP最適化テスト": 42.5
  },
  "summary": {
    "total_initiatives_analyzed": 2,
    "successful_analyses": 2,
    "avg_impact_score": 58.3
  }
}
```

---

### 3. 推奨システムの強化 (`src/recommend_enhanced.py`)

**機能**: 予測分析と施策効果を組み込んだ高度な推奨生成

#### 改善点
1. **定量的な根拠**: 
   - 予測値に基づく推奨
   - 期待される効果を数値で表示
   - 信頼度を明記

2. **優先度の自動計算**:
   - ROI潜在力でランク付け
   - 実装難度を併記

3. **実行可能性の向上**:
   - 具体的なステップを指示
   - チャネル別の個別提案
   - 期待される改善度を明示

#### 利用方法

```python
from src.recommend_enhanced import enhance_recommendations_with_quantified_impact

# 既存の推奨リストを強化
enhanced_recs = enhance_recommendations_with_quantified_impact(
    original_recommendations=existing_recs,
    df=marketing_df,
    channels_df=channels_snapshot,
    impact_analysis=impact_result,
)

# 各推奨に定量情報が追加される
for rec in enhanced_recs:
    print(f"[{rec['priority']}] {rec['issue']}")
    if 'expected_impact' in rec:
        print(f"  期待される効果: {rec['expected_impact']}")
    print(f"  実装難度: {rec.get('effort_level', 'N/A')}")
    print(f"  ROIスコア: {rec.get('roi_score', 'N/A')}/100")
```

---

## 🎯 使用方法

### オプション1: 予測分析のみ有効
```bash
python main.py --enable-forecasting --skip-llm
```
- ROAS、CVR、CPAの7日予測を生成
- 異常値を検知
- トレンド方向を判定

### オプション2: 施策効果分析のみ有効
```bash
python main.py --enable-impact-analysis --initiatives '[{"name":"test","date":"2026-03-20","metric":"revenue"}]' --skip-llm
```

### オプション3: 両方有効（推奨）
```bash
python main.py --enable-forecasting --enable-impact-analysis --initiatives '[...]' --skip-llm
```
- 予測と実績を組み合わせた高度な分析
- 定量化された推奨事項を生成

---

## 📈 期待される改善効果

### 定性的改善
✅ **より科学的な意思決定**: 勘ではなくデータに基づいた判断
✅ **早期の問題検知**: トレンド低下を事前に察知
✅ **施策の効果測定**: 「本当に効いたか」を定量化

### 定量的改善（想定）
- 推奨の実行率: +20-30%（具体性向上のため）
- 施策の成功率: +15-25%（定量根拠のため）
- 分析の信頼度: +40%以上（予測と実績の検証ループ）

---

## 🔍 技術詳細

### 予測モデルの選択理由
- **線形トレンド + 指数平滑法の併用**
  - 小規模データセット（3日以上）でも動作
  - 短期予測に最適
  - オーバーフィッティングのリスクが低い
  - 従来のARIMAやProphetより実装が簡単

### 信頼度の計算方法
```
信頼度 = min(1.0, データポイント数 / 30)
```
- 30日分のデータで信頼度100%
- 3日分のデータで信頼度10%
- ユーザーに信頼性を明確に伝える

### ボラティリティの考慮
```
CV（変動係数） = 標準偏差 / 平均
信頼度 = 1.0 - min(CV, 1.0)
```
- 安定した指標ほど予測精度が高い
- ノイズの多い指標は信頼度が自動的に低下

---

## ⚠️ 注意点

1. **最小データ要件**
   - 予測: 3日以上のデータが必要
   - 施策効果: ベースライン3日 + 施策後2日最低

2. **検証の重要性**
   - 予測は参考値。市場変動には対応しない
   - 施策効果は相関であり因果ではない可能性あり
   - 定期的に予測値と実績を検証

3. **季節性・外部要因**
   - 現在の実装は季節性を考慮しない
   - 大きなイベント時は予測精度が低下する可能性
   - 将来のバージョンアップで改善予定

---

## 🚀 今後のアップグレード予定

- [ ] ARIMA/Prophetによる高度な予測
- [ ] 季節性の自動検出
- [ ] 機械学習モデルによる異常検知
- [ ] マルチタッチ・アトリビューション
- [ ] 因果推論の導入
- [ ] リアルタイム予測値の更新

---

## 📞 テクニカルサポート

新機能について質問や問題があれば、以下をご確認ください：

1. `test_new_modules.py` で動作確認
2. `src/forecasting.py` のコメント参照
3. `src/impact_analysis.py` のコメント参照

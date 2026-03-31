#!/usr/bin/env python
"""
Quick start guide for new analysis features.
This script demonstrates the new forecasting and impact analysis capabilities.
"""

import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

print("""
╔══════════════════════════════════════════════════════════════════╗
║  Marketing Auto Analyzer - 新機能デモンストレーション             ║
║  Forecasting & Impact Analysis Quick Start                       ║
╚══════════════════════════════════════════════════════════════════╝
""")

# Step 1: Generate sample data
print("\n📊 Step 1: サンプルデータの生成")
print("-" * 50)

dates = pd.date_range(start='2026-03-15', end='2026-03-22', freq='D')
sample_data = []

# Generate sample marketing data
np.random.seed(42)
for date in dates:
    for channel in ['google', 'meta']:
        sample_data.append({
            'date': date.strftime('%Y-%m-%d'),
            'channel': channel,
            'campaign': f'campaign_{channel}_A',
            'sessions': np.random.randint(900, 1500),
            'users': np.random.randint(700, 1100),
            'conversions': np.random.randint(20, 60),
            'revenue': np.random.randint(100000, 300000),
            'cost': np.random.randint(50000, 100000),
        })

df = pd.DataFrame(sample_data)
df['date'] = pd.to_datetime(df['date'])

print(f"✓ {len(df)} 行のデータを生成しました")
print(f"  期間: {df['date'].min().date()} ～ {df['date'].max().date()}")
print(f"  チャネル: {', '.join(df['channel'].unique())}")

# Step 2: Load forecasting module
print("\n" + "="*50)
print("\n🔮 Step 2: 予測分析モジュールのロード")
print("-" * 50)

try:
    from src.forecasting import MetricForecaster, AnomalyDetector, add_forecasts_to_analysis
    print("✓ 予測分析モジュールをロードしました")
except Exception as e:
    print(f"✗ エラー: {e}")
    exit(1)

# Step 3: Forecast ROAS
print("\n" + "="*50)
print("\n📈 Step 3: ROAS 7日予測")
print("-" * 50)

df['roas'] = df['revenue'] / df['cost']
df['cvr'] = df['conversions'] / df['sessions']
df['cpa'] = df['cost'] / df['conversions']

forecaster = MetricForecaster()

for channel in ['google', 'meta']:
    channel_data = df[df['channel'] == channel].sort_values('date')
    roas_values = channel_data['roas'].values.tolist()
    
    forecast = forecaster.forecast_metric(roas_values, f'ROAS ({channel})', forecast_days=7)
    
    print(f"\n📊 {channel.upper()}")
    print(f"  現在のROAS: {forecast.current_value:.2f}")
    print(f"  7日後予測: {forecast.forecast_value:.2f}")
    print(f"  変化: {((forecast.forecast_value - forecast.current_value) / forecast.current_value * 100):+.1f}%")
    print(f"  信頼度: {forecast.confidence:.0%}")
    print(f"  トレンド: {forecast.trend_direction}")

# Step 4: Load impact analysis module
print("\n" + "="*50)
print("\n📊 Step 4: 施策効果定量化モジュールのロード")
print("-" * 50)

try:
    from src.impact_analysis import analyze_initiative_impact
    print("✓ 施策効果定量化モジュールをロードしました")
except Exception as e:
    print(f"✗ エラー: {e}")
    exit(1)

# Step 5: Analyze initiative impact
print("\n" + "="*50)
print("\n💡 Step 5: 施策効果の測定")
print("-" * 50)

initiatives = [
    {
        'name': 'LP最適化テスト',
        'date': '2026-03-20',
        'metric': 'cvr',
        'baseline_days': 3,
        'post_days': 3,
    },
    {
        'name': '広告クリエイティブ変更',
        'date': '2026-03-20',
        'metric': 'roas',
        'baseline_days': 3,
        'post_days': 3,
    }
]

impact_result = analyze_initiative_impact(df, initiatives)

print(f"\n✓ {len(impact_result['impact_results'])} 件の施策を分析しました\n")

for init_result in impact_result['impact_results']:
    initiative = init_result['initiative']
    metric = init_result['metric'].upper()
    
    print(f"【{initiative}】")
    print(f"  メトリクス: {metric}")
    print(f"  ベースライン: {init_result['baseline_value']:.4f}")
    print(f"  施策後: {init_result['post_impact_value']:.4f}")
    print(f"  改善度: {init_result['pct_change']:+.1f}%")
    print(f"  信頼度: {init_result['confidence']:.0%}")
    print(f"  インパクトスコア: {impact_result['impact_scores'][initiative]:.1f}/100")
    print()

# Step 6: Generate enhanced recommendations
print("\n" + "="*50)
print("\n💡 Step 6: 定量化された推奨生成")
print("-" * 50)

try:
    from src.recommend_enhanced import EnhancedRecommendationGenerator
    print("✓ 推奨生成モジュールをロードしました")
except Exception as e:
    print(f"✗ エラー: {e}")
    exit(1)

generator = EnhancedRecommendationGenerator()

# Generate forecast-based recommendations
snapshot = {}
snapshot = add_forecasts_to_analysis(snapshot, df)

# Get channel metrics for recommendation
channels_df = df.groupby('channel').agg({
    'revenue': 'sum',
    'cost': 'sum',
    'conversions': 'sum',
    'sessions': 'sum',
    'roas': 'mean',
    'cpa': 'mean',
    'cvr': 'mean',
}).reset_index()

forecast_recs = generator.generate_from_forecasts(snapshot.get('forecasts', {}), channels_df)
impact_recs = generator.generate_from_impact_analysis(impact_result)

print(f"\n📋 予測ベースの推奨: {len(forecast_recs)} 件")
for i, rec in enumerate(forecast_recs[:2], 1):
    print(f"\n  {i}. [{rec.priority}] {rec.issue}")
    print(f"     → {rec.action}")
    print(f"     ROIスコア: {rec.roi_score:.0f}/100")

print(f"\n📋 施策効果ベースの推奨: {len(impact_recs)} 件")
for i, rec in enumerate(impact_recs[:2], 1):
    print(f"\n  {i}. [{rec.priority}] {rec.issue}")
    print(f"     → {rec.action}")
    print(f"     ROIスコア: {rec.roi_score:.0f}/100")

# Step 7: Usage examples
print("\n" + "="*50)
print("\n🚀 実装例")
print("-" * 50)

print("""
【例1】基本的な予測分析
```python
from src.forecasting import MetricForecaster
import pandas as pd

forecaster = MetricForecaster()
forecast = forecaster.forecast_metric(
    metric_values=[2.1, 2.05, 2.15, 2.08],
    metric_name='ROAS',
    forecast_days=7
)
print(f"7日後のROAS予測: {forecast.forecast_value:.2f}")
```

【例2】施策効果の測定
```python
from src.impact_analysis import analyze_initiative_impact

initiatives = [{
    'name': 'LP改善',
    'date': '2026-03-20',
    'metric': 'cvr',
    'baseline_days': 7,
    'post_days': 7,
}]

result = analyze_initiative_impact(df, initiatives)
print(f"改善度: {result['impact_results'][0]['pct_change']:.1f}%")
```

【例3】メインパイプラインでの使用
```bash
# 予測分析のみ
$ python main.py --enable-forecasting --skip-llm

# 施策効果分析のみ
$ python main.py --enable-impact-analysis \\
  --initiatives '[{"name":"test","date":"2026-03-20","metric":"revenue"}]' \\
  --skip-llm

# 両方有効（推奨）
$ python main.py --enable-forecasting --enable-impact-analysis \\
  --initiatives '[...]' --skip-llm
```
""")

print("\n" + "="*50)
print("\n✅ デモンストレーション完了!")
print("\n詳細は NEW_FEATURES.md をご覧ください")
print("="*50 + "\n")

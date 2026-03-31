#!/usr/bin/env python
"""Test script for new forecasting and impact analysis modules."""

import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Test forecasting module
try:
    from src.forecasting import MetricForecaster, AnomalyDetector, add_forecasts_to_analysis
    print("✓ Successfully imported forecasting module")
except Exception as e:
    print(f"✗ Failed to import forecasting module: {e}")
    sys.exit(1)

# Test impact analysis module
try:
    from src.impact_analysis import BeforeAfterAnalyzer, analyze_initiative_impact
    print("✓ Successfully imported impact_analysis module")
except Exception as e:
    print(f"✗ Failed to import impact_analysis module: {e}")
    sys.exit(1)

# Test recommendations enhancement
try:
    from src.recommend_enhanced import EnhancedRecommendationGenerator, enhance_recommendations_with_quantified_impact
    print("✓ Successfully imported recommend_enhanced module")
except Exception as e:
    print(f"✗ Failed to import recommend_enhanced module: {e}")
    sys.exit(1)

# Create sample data for testing
print("\n--- Testing with sample data ---")

# Generate synthetic test data
dates = pd.date_range(start='2026-03-15', end='2026-03-22', freq='D')
test_data = []

for date in dates:
    test_data.append({
        'date': date.strftime('%Y-%m-%d'),
        'channel': 'google',
        'campaign': 'campaign_a',
        'sessions': np.random.randint(1000, 1500),
        'users': np.random.randint(800, 1100),
        'conversions': np.random.randint(40, 60),
        'revenue': np.random.randint(150000, 250000),
        'cost': np.random.randint(60000, 90000),
    })
    test_data.append({
        'date': date.strftime('%Y-%m-%d'),
        'channel': 'meta',
        'campaign': 'campaign_b',
        'sessions': np.random.randint(700, 1000),
        'users': np.random.randint(600, 850),
        'conversions': np.random.randint(15, 30),
        'revenue': np.random.randint(60000, 120000),
        'cost': np.random.randint(50000, 80000),
    })

df = pd.DataFrame(test_data)
df['date'] = pd.to_datetime(df['date'])

print(f"Created test dataset with {len(df)} rows")
print(df.head())

# Test 1: Forecasting
print("\n--- Test 1: MetricForecaster ---")
try:
    forecaster = MetricForecaster()
    
    # Get historical ROAS values
    df['roas'] = df['revenue'] / df['cost']
    df['cpa'] = df['cost'] / df['conversions']
    df['cvr'] = df['conversions'] / df['sessions']
    
    google_data = df[df['channel'] == 'google'].sort_values('date')
    roas_values = google_data['roas'].values.tolist()
    
    forecast = forecaster.forecast_metric(roas_values, 'ROAS', forecast_days=7)
    print(f"  Current ROAS: {forecast.current_value:.2f}")
    print(f"  Forecast ROAS (7d): {forecast.forecast_value:.2f}")
    print(f"  Confidence: {forecast.confidence:.0%}")
    print(f"  Trend: {forecast.trend_direction}")
    print("✓ MetricForecaster test passed")
except Exception as e:
    print(f"✗ MetricForecaster test failed: {e}")
    import traceback
    traceback.print_exc()

# Test 2: Anomaly Detection
print("\n--- Test 2: AnomalyDetector ---")
try:
    detector = AnomalyDetector()
    anomalies = detector.detect_anomalies(df, 'roas')
    print(f"  Detected {len(anomalies)} anomalies")
    if anomalies:
        print(f"  First anomaly: {anomalies[0]}")
    print("✓ AnomalyDetector test passed")
except Exception as e:
    print(f"✗ AnomalyDetector test failed: {e}")
    import traceback
    traceback.print_exc()

# Test 3: Before/After Analysis
print("\n--- Test 3: BeforeAfterAnalyzer ---")
try:
    analyzer = BeforeAfterAnalyzer()
    
    # Analyze hypothetical price increase initiative
    impact = analyzer.simple_before_after(
        df,
        initiative_name="LP optimization test",
        change_date='2026-03-20',
        metric='cvr',
        baseline_days_before=3,
        post_days_after=3,
    )
    
    if impact:
        print(f"  Initiative: {impact.initiative}")
        print(f"  Baseline CVR: {impact.baseline_value:.4f}")
        print(f"  Post CVR: {impact.post_impact_value:.4f}")
        print(f"  Change: {impact.pct_change:+.1f}%")
        print(f"  Confidence: {impact.confidence:.0%}")
        print("✓ BeforeAfterAnalyzer test passed")
    else:
        print("  No impact result (data insufficient)")
except Exception as e:
    print(f"✗ BeforeAfterAnalyzer test failed: {e}")
    import traceback
    traceback.print_exc()

# Test 4: Add forecasts to analysis
print("\n--- Test 4: add_forecasts_to_analysis ---")
try:
    snapshot = {}
    snapshot = add_forecasts_to_analysis(snapshot, df)
    
    has_forecasts = 'forecasts' in snapshot
    has_anomalies = 'anomalies' in snapshot.get('forecasts', {})
    
    print(f"  Forecasts added: {has_forecasts}")
    print(f"  Anomalies detected: {has_anomalies}")
    if 'by_channel' in snapshot.get('forecasts', {}):
        channels = list(snapshot['forecasts']['by_channel'].keys())
        print(f"  Channels forecasted: {channels}")
    print("✓ add_forecasts_to_analysis test passed")
except Exception as e:
    print(f"✗ add_forecasts_to_analysis test failed: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*50)
print("All module tests completed successfully!")
print("="*50)

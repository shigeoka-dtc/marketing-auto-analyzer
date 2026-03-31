"""
Forecasting module for predictive analytics.
- Time series forecasting for key metrics (ROAS, CPA, CVR)
- Anomaly detection
- Trend analysis
"""

import numpy as np
import pandas as pd
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass


@dataclass
class ForecastResult:
    """Forecast result with confidence interval"""
    metric_name: str
    current_value: float
    forecast_value: float
    forecast_days_ahead: int
    lower_bound: float
    upper_bound: float
    confidence: float
    trend_direction: str  # 'upward', 'downward', 'stable'
    volatility: float


@dataclass
class AnomalyAlert:
    """Detected anomaly"""
    date: str
    channel: str
    metric: str
    current_value: float
    expected_value: float
    deviation_pct: float
    severity: str  # 'low', 'medium', 'high'


class SimpleForecaster:
    """Simple but effective forecasting for small datasets"""
    
    MIN_DATA_POINTS = 3
    DEFAULT_FORECAST_DAYS = 7
    
    @staticmethod
    def linear_trend(values: np.ndarray, forecast_days: int = 7) -> Tuple[float, float, float]:
        """
        Simple linear regression for trend.
        Returns: (forecast_value, lower_bound, upper_bound)
        """
        if len(values) < SimpleForecaster.MIN_DATA_POINTS:
            # Not enough data - return current value
            return values[-1], values[-1] * 0.9, values[-1] * 1.1
        
        x = np.arange(len(values))
        y = np.array(values, dtype=float)
        
        # Remove NaN values
        mask = ~np.isnan(y)
        x_clean = x[mask]
        y_clean = y[mask]
        
        if len(x_clean) < 2:
            return y_clean[-1] if len(y_clean) > 0 else values[-1], values[-1] * 0.9, values[-1] * 1.1
        
        # Linear regression
        coeffs = np.polyfit(x_clean, y_clean, 1)
        slope, intercept = coeffs[0], coeffs[1]
        
        # Forecast
        forecast_x = len(values) + forecast_days - 1
        forecast_value = slope * forecast_x + intercept
        
        # Simple confidence interval based on recent volatility
        recent_values = y_clean[-min(3, len(y_clean)):]
        volatility = np.std(recent_values) if len(recent_values) > 1 else abs(forecast_value * 0.1)
        
        return forecast_value, forecast_value - 1.96 * volatility, forecast_value + 1.96 * volatility
    
    @staticmethod
    def exponential_smoothing(values: np.ndarray, alpha: float = 0.3, forecast_days: int = 7) -> Tuple[float, float, float]:
        """
        Exponential smoothing for trend following.
        Returns: (forecast_value, lower_bound, upper_bound)
        """
        if len(values) < SimpleForecaster.MIN_DATA_POINTS:
            return values[-1], values[-1] * 0.9, values[-1] * 1.1
        
        y = np.array(values, dtype=float)
        mask = ~np.isnan(y)
        y_clean = y[mask]
        
        if len(y_clean) < 2:
            return y_clean[-1], y_clean[-1] * 0.9, y_clean[-1] * 1.1
        
        # Exponential smoothing
        smoothed = [y_clean[0]]
        for i in range(1, len(y_clean)):
            smoothed.append(alpha * y_clean[i] + (1 - alpha) * smoothed[i - 1])
        
        # Forecast (simple: use last smoothed value repeated)
        forecast_value = smoothed[-1]
        
        # Confidence interval
        errors = y_clean - np.array(smoothed)
        rmse = np.sqrt(np.mean(errors ** 2))
        
        return forecast_value, forecast_value - 1.96 * rmse, forecast_value + 1.96 * rmse


class MetricForecaster:
    """Forecast individual metrics based on historical data"""
    
    def __init__(self):
        self.forecaster = SimpleForecaster()
    
    def forecast_metric(
        self,
        metric_values: List[float],
        metric_name: str,
        current_date: str = None,
        forecast_days: int = 7,
    ) -> ForecastResult:
        """
        Forecast a metric into the future.
        
        Args:
            metric_values: List of historical values
            metric_name: Name of metric (e.g., 'ROAS', 'CVR', 'CPA')
            current_date: Current date for reference
            forecast_days: Number of days to forecast ahead
        
        Returns:
            ForecastResult with forecast and confidence interval
        """
        if not metric_values or len(metric_values) == 0:
            raise ValueError("At least one metric value required")
        
        values_array = np.array(metric_values, dtype=float)
        
        # Try multiple forecasting methods and take average for robustness
        linear_forecast, linear_lower, linear_upper = self.forecaster.linear_trend(
            values_array, forecast_days
        )
        exp_forecast, exp_lower, exp_upper = self.forecaster.exponential_smoothing(
            values_array, forecast_days=forecast_days
        )
        
        # Weighted average (favor exponential smoothing for small datasets)
        forecast_value = 0.4 * linear_forecast + 0.6 * exp_forecast
        lower_bound = min(linear_lower, exp_lower)
        upper_bound = max(linear_upper, exp_upper)
        
        # Trend direction
        if len(values_array) >= 2:
            recent_trend = values_array[-1] - values_array[-2]
            if abs(recent_trend) < values_array[-1] * 0.05:
                trend_direction = 'stable'
            elif recent_trend > 0:
                trend_direction = 'upward'
            else:
                trend_direction = 'downward'
        else:
            trend_direction = 'stable'
        
        # Volatility
        volatility = np.std(values_array) / (np.mean(values_array) + 1e-8) if len(values_array) > 1 else 0.0
        
        # Confidence (higher with more data)
        confidence = min(1.0, len(values_array) / 30.0)
        
        return ForecastResult(
            metric_name=metric_name,
            current_value=float(values_array[-1]),
            forecast_value=float(forecast_value),
            forecast_days_ahead=forecast_days,
            lower_bound=float(lower_bound),
            upper_bound=float(upper_bound),
            confidence=float(confidence),
            trend_direction=trend_direction,
            volatility=float(volatility),
        )
    
    def forecast_channel_metrics(
        self,
        df: pd.DataFrame,
        channel: str,
        forecast_days: int = 7,
    ) -> Dict[str, ForecastResult]:
        """
        Forecast key metrics for a specific channel.
        
        Args:
            df: DataFrame with columns: date, channel, and metric columns
            channel: Channel name to forecast
            forecast_days: Days ahead to forecast
        
        Returns:
            Dictionary mapping metric names to ForecastResult
        """
        channel_data = df[df['channel'] == channel].sort_values('date')
        
        if channel_data.empty:
            return {}
        
        forecasts = {}
        metric_names = ['roas', 'cpa', 'cvr', 'revenue', 'cost', 'conversions']
        
        for metric in metric_names:
            if metric not in channel_data.columns:
                continue
            
            values = channel_data[metric].values
            if len(values) >= self.forecaster.MIN_DATA_POINTS:
                forecasts[metric] = self.forecast_metric(
                    values.tolist(),
                    metric_name=metric.upper(),
                    forecast_days=forecast_days,
                )
        
        return forecasts


class AnomalyDetector:
    """Detect anomalies in metric values"""
    
    ZSCORE_THRESHOLD = 2.0
    
    @staticmethod
    def detect_anomalies(
        df: pd.DataFrame,
        metric: str,
        zscore_threshold: float = ZSCORE_THRESHOLD,
    ) -> List[AnomalyAlert]:
        """
        Detect anomalies using z-score method.
        
        Args:
            df: DataFrame with columns: date, channel, metric
            metric: Metric column name to check
            zscore_threshold: Z-score threshold for anomaly
        
        Returns:
            List of AnomalyAlert
        """
        alerts = []
        
        if metric not in df.columns:
            return alerts
        
        for channel in df['channel'].unique():
            channel_data = df[df['channel'] == channel].sort_values('date')
            values = channel_data[metric].values
            
            if len(values) < 3:
                continue
            
            mean = np.mean(values)
            std = np.std(values)
            
            if std == 0:
                continue
            
            for idx, (_, row) in enumerate(channel_data.iterrows()):
                value = row[metric]
                
                if pd.isna(value):
                    continue
                
                zscore = abs((value - mean) / std)
                
                if zscore > zscore_threshold:
                    deviation_pct = ((value - mean) / mean * 100) if mean != 0 else 0
                    
                    severity = 'high' if zscore > 3.0 else 'medium' if zscore > 2.5 else 'low'
                    
                    alerts.append(
                        AnomalyAlert(
                            date=str(row['date']),
                            channel=channel,
                            metric=metric,
                            current_value=float(value),
                            expected_value=float(mean),
                            deviation_pct=float(deviation_pct),
                            severity=severity,
                        )
                    )
        
        return sorted(alerts, key=lambda x: (x['severity'], abs(x['deviation_pct'])), reverse=True)


def add_forecasts_to_analysis(analysis_snapshot: dict, df: pd.DataFrame) -> dict:
    """
    Add forecast data to analysis snapshot.
    
    Args:
        analysis_snapshot: Existing analysis snapshot dict
        df: Marketing data DataFrame
    
    Returns:
        Updated analysis snapshot with forecasts
    """
    forecaster = MetricForecaster()
    anomaly_detector = AnomalyDetector()
    
    # Compute derived metrics if not present
    if 'roas' not in df.columns:
        df['roas'] = df['revenue'] / (df['cost'] + 1e-8)
    if 'cpa' not in df.columns:
        df['cpa'] = df['cost'] / (df['conversions'] + 1e-8)
    if 'cvr' not in df.columns:
        df['cvr'] = df['conversions'] / (df['sessions'] + 1e-8)
    
    # Forecasts by channel
    forecasts = {}
    for channel in df['channel'].unique():
        forecasts[channel] = forecaster.forecast_channel_metrics(df, channel, forecast_days=7)
    
    # Anomalies
    anomalies = anomaly_detector.detect_anomalies(df, 'roas')
    anomalies += anomaly_detector.detect_anomalies(df, 'cvr')
    
    analysis_snapshot['forecasts'] = {
        'by_channel': {ch: {m: vars(f) for m, f in fcs.items()} for ch, fcs in forecasts.items()},
        'anomalies': [vars(a) for a in anomalies[:10]],  # Top 10 anomalies
    }
    
    return analysis_snapshot

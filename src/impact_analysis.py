"""
Impact Analysis module for quantifying the effect of marketing initiatives.
- Before/After analysis
- Multi-channel effect attribution
- Confidence evaluation
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta


@dataclass
class ImpactResult:
    """Result of impact analysis"""
    initiative: str
    date_implemented: str
    metric: str
    baseline_value: float
    post_impact_value: float
    absolute_change: float
    pct_change: float
    confidence: float  # 0-1, higher means more reliable
    contribution_to_total: float  # % contribution to total metric value
    days_of_data: int


@dataclass
class ChannelAttribution:
    """Attribution of total change to specific channel"""
    channel: str
    metric: str
    baseline_value: float
    post_value: float
    absolute_contribution: float
    pct_contribution: float  # % of total change
    confidence: float


class BeforeAfterAnalyzer:
    """Analyze before/after effects of initiatives"""
    
    MIN_BASELINE_DAYS = 3
    MIN_POST_DAYS = 2
    
    @staticmethod
    def calculate_period_metrics(
        df: pd.DataFrame,
        start_date: str,
        end_date: str,
        metric: str,
    ) -> Dict[str, float]:
        """
        Calculate aggregated metrics for a period.
        
        Args:
            df: DataFrame with date column
            start_date: Period start (YYYY-MM-DD)
            end_date: Period end (YYYY-MM-DD)
            metric: Metric to aggregate
        
        Returns:
            Dict with 'sum', 'mean', 'std', 'count'
        """
        period_df = df[(df['date'] >= start_date) & (df['date'] <= end_date)]
        
        if period_df.empty:
            return {'sum': 0, 'mean': 0, 'std': 0, 'count': 0}
        
        values = period_df[metric].values
        return {
            'sum': float(np.sum(values)),
            'mean': float(np.mean(values)),
            'std': float(np.std(values)) if len(values) > 1 else 0.0,
            'count': len(values),
        }
    
    @staticmethod
    def simple_before_after(
        df: pd.DataFrame,
        initiative_name: str,
        change_date: str,
        metric: str,
        baseline_days_before: int = 7,
        post_days_after: int = 7,
    ) -> Optional[ImpactResult]:
        """
        Simple before/after analysis.
        
        Args:
            df: DataFrame with date, channel, metric columns
            initiative_name: Name of initiative
            change_date: Implementation date (YYYY-MM-DD)
            metric: Metric to measure (e.g., 'revenue', 'conversions', 'roas')
            baseline_days_before: Days before change for baseline
            post_days_after: Days after change for post-period
        
        Returns:
            ImpactResult if analysis successful, None otherwise
        """
        try:
            change_dt = pd.to_datetime(change_date)
            baseline_start = (change_dt - timedelta(days=baseline_days_before)).strftime('%Y-%m-%d')
            baseline_end = (change_dt - timedelta(days=1)).strftime('%Y-%m-%d')
            post_start = change_dt.strftime('%Y-%m-%d')
            post_end = (change_dt + timedelta(days=post_days_after)).strftime('%Y-%m-%d')
            
            # Get baseline and post metrics
            baseline = BeforeAfterAnalyzer.calculate_period_metrics(
                df, baseline_start, baseline_end, metric
            )
            post = BeforeAfterAnalyzer.calculate_period_metrics(
                df, post_start, post_end, metric
            )
            
            if baseline['count'] < BeforeAfterAnalyzer.MIN_BASELINE_DAYS or \
               post['count'] < BeforeAfterAnalyzer.MIN_POST_DAYS:
                return None
            
            baseline_value = baseline['mean']
            post_value = post['mean']
            
            # Calculate confidence based on data consistency
            # Higher std = lower confidence
            baseline_cv = baseline['std'] / (baseline_value + 1e-8) if baseline_value > 0 else 0.5
            post_cv = post['std'] / (post_value + 1e-8) if post_value > 0 else 0.5
            
            # Confidence: lower CV = higher confidence
            avg_cv = (baseline_cv + post_cv) / 2
            confidence = max(0.3, 1.0 - min(avg_cv, 1.0))  # Scale to 0.3-1.0
            
            absolute_change = post_value - baseline_value
            pct_change = (absolute_change / baseline_value * 100) if baseline_value > 0 else 0.0
            
            # Contribution to total
            total_value = post['sum'] if post['sum'] > 0 else 1
            contribution = (absolute_change * post['count'] / total_value * 100) if total_value > 0 else 0
            
            return ImpactResult(
                initiative=initiative_name,
                date_implemented=change_date,
                metric=metric,
                baseline_value=float(baseline_value),
                post_impact_value=float(post_value),
                absolute_change=float(absolute_change),
                pct_change=float(pct_change),
                confidence=float(confidence),
                contribution_to_total=float(contribution),
                days_of_data=baseline['count'] + post['count'],
            )
        except Exception as e:
            print(f"Error in before/after analysis: {e}")
            return None


class MultiChannelAttribution:
    """Attribute impact across multiple channels"""
    
    @staticmethod
    def channel_contribution(
        df: pd.DataFrame,
        start_date: str,
        end_date: str,
        metric: str,
    ) -> List[ChannelAttribution]:
        """
        Analyze contribution of each channel to metric.
        
        Args:
            df: DataFrame with date, channel, metric columns
            start_date: Analysis period start
            end_date: Analysis period end
            metric: Metric to analyze
        
        Returns:
            List of ChannelAttribution
        """
        period_df = df[(df['date'] >= start_date) & (df['date'] <= end_date)]
        
        if period_df.empty:
            return []
        
        contributions = []
        total_changes = {}
        
        # Get baseline (first half) and post (second half)
        period_dates = sorted(period_df['date'].unique())
        midpoint_idx = len(period_dates) // 2
        
        if midpoint_idx < 1 or midpoint_idx >= len(period_dates) - 1:
            return []
        
        baseline_end_date = str(period_dates[midpoint_idx])
        post_start_date = str(period_dates[midpoint_idx + 1])
        
        for channel in period_df['channel'].unique():
            channel_df = period_df[period_df['channel'] == channel]
            
            baseline_data = channel_df[channel_df['date'] <= baseline_end_date]
            post_data = channel_df[channel_df['date'] >= post_start_date]
            
            if baseline_data.empty or post_data.empty:
                continue
            
            baseline_value = baseline_data[metric].mean()
            post_value = post_data[metric].mean()
            
            absolute_contribution = post_value - baseline_value
            total_changes[channel] = absolute_contribution
        
        # Calculate percentage contributions
        total_change = sum(total_changes.values()) if total_changes else 1
        
        for channel, absolute_contrib in total_changes.items():
            pct_contrib = (absolute_contrib / total_change * 100) if total_change != 0 else 0
            
            # Confidence based on data volume
            channel_data = period_df[period_df['channel'] == channel]
            data_days = len(channel_data)
            confidence = min(1.0, data_days / 10.0)
            
            # Get values for attribution
            baseline_vals = channel_data[channel_data['date'] <= baseline_end_date][metric]
            post_vals = channel_data[channel_data['date'] >= post_start_date][metric]
            
            baseline_value = baseline_vals.mean() if len(baseline_vals) > 0 else 0
            post_value = post_vals.mean() if len(post_vals) > 0 else 0
            
            contributions.append(
                ChannelAttribution(
                    channel=channel,
                    metric=metric,
                    baseline_value=float(baseline_value),
                    post_value=float(post_value),
                    absolute_contribution=float(absolute_contrib),
                    pct_contribution=float(pct_contrib),
                    confidence=float(confidence),
                )
            )
        
        return sorted(contributions, key=lambda x: abs(x.absolute_contribution), reverse=True)


class ImpactScoreCalculator:
    """Calculate impact scores for initiatives with different metrics"""
    
    @staticmethod
    def calculate_impact_score(
        impact_results: List[ImpactResult],
    ) -> Dict[str, float]:
        """
        Calculate weighted impact score across multiple initiatives.
        
        Score considers:
        - Magnitude of change (%)
        - Confidence in measurement
        - Days of data
        - Contribution to total
        
        Args:
            impact_results: List of ImpactResult from analyses
        
        Returns:
            Dict mapping initiative names to scores (0-100)
        """
        scores = {}
        
        for result in impact_results:
            # Base score from % change
            pct_component = min(abs(result.pct_change), 50) / 50 * 30  # Max 30 points
            
            # Confidence component
            confidence_component = result.confidence * 30  # Max 30 points
            
            # Data quality component
            data_component = min(result.days_of_data / 14, 1.0) * 20  # Max 20 points
            
            # Contribution component
            contribution_component = min(result.contribution_to_total, 100) / 100 * 20  # Max 20 points
            
            total_score = pct_component + confidence_component + data_component + contribution_component
            scores[result.initiative] = float(total_score)
        
        return scores


def analyze_initiative_impact(
    df: pd.DataFrame,
    initiatives: List[Dict],
) -> Dict:
    """
    Comprehensive impact analysis for multiple initiatives.
    
    Args:
        df: Marketing data DataFrame
        initiatives: List of dicts with keys:
            - name: Initiative name
            - date: Implementation date (YYYY-MM-DD)
            - metric: Metric to measure
            - baseline_days: Days before (default 7)
            - post_days: Days after (default 7)
    
    Returns:
        Dict with impact results and scores
    """
    analyzer = BeforeAfterAnalyzer()
    attrib = MultiChannelAttribution()
    scorer = ImpactScoreCalculator()
    
    results = []
    attributions = {}
    
    for init in initiatives:
        impact = analyzer.simple_before_after(
            df,
            initiative_name=init.get('name', 'Unknown'),
            change_date=init['date'],
            metric=init.get('metric', 'revenue'),
            baseline_days_before=init.get('baseline_days', 7),
            post_days_after=init.get('post_days', 7),
        )
        
        if impact:
            results.append(impact)
            
            # Get channel attribution
            change_dt = pd.to_datetime(init['date'])
            post_end = (change_dt + timedelta(days=init.get('post_days', 7))).strftime('%Y-%m-%d')
            
            attributions[impact.initiative] = attrib.channel_contribution(
                df,
                init['date'],
                post_end,
                init.get('metric', 'revenue'),
            )
    
    scores = scorer.calculate_impact_score(results)
    
    return {
        'impact_results': [vars(r) for r in results],
        'channel_attributions': {
            name: [vars(a) for a in attrs] for name, attrs in attributions.items()
        },
        'impact_scores': scores,
        'summary': {
            'total_initiatives_analyzed': len(initiatives),
            'successful_analyses': len(results),
            'avg_impact_score': float(np.mean(list(scores.values()))) if scores else 0.0,
        }
    }

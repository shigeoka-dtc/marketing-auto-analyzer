"""
Enhanced recommendation system using forecasting and impact analysis.
- Generates recommendations based on predictions
- Quantifies expected impact
- Prioritizes by ROI potential
"""

import pandas as pd
from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class QuantifiedRecommendation:
    """Recommendation with quantified expected impact"""
    priority: str  # P1, P2, P3
    channel: str
    issue: str
    action: str
    reason: str
    confidence: float
    expected_impact: Dict  # e.g., {'metric': 'ROAS', 'delta_pct': 15.5}
    effort_level: str  # 'low', 'medium', 'high'
    roi_score: float  # 0-100


class EnhancedRecommendationGenerator:
    """Generate recommendations using predictive and impact data"""
    
    @staticmethod
    def generate_from_forecasts(
        forecasts: Dict,
        channels_df: pd.DataFrame,
    ) -> List[QuantifiedRecommendation]:
        """
        Generate recommendations based on forecast analysis.
        
        Args:
            forecasts: Dict from forecasting.add_forecasts_to_analysis()
            channels_df: Current channel metrics DataFrame
        
        Returns:
            List of QuantifiedRecommendation
        """
        recs = []
        
        for channel, metrics_forecast in forecasts.get('by_channel', {}).items():
            if not metrics_forecast:
                continue
            
            # Find the channel row
            channel_row = channels_df[channels_df['channel'] == channel]
            if channel_row.empty:
                continue
            
            current_roas = float(channel_row.iloc[0].get('roas', 0))
            current_revenue = float(channel_row.iloc[0].get('revenue', 0))
            
            # Analyze ROAS forecast
            if 'roas' in metrics_forecast:
                roas_fc = metrics_forecast['roas']
                forecast_roas = roas_fc['forecast_value']
                confidence = roas_fc['confidence']
                trend = roas_fc['trend_direction']
                
                roas_change_pct = ((forecast_roas - roas_fc['current_value']) / (roas_fc['current_value'] + 1e-8)) * 100
                
                # Downtrend = concern
                if trend == 'downward' and roas_change_pct < -10:
                    expected_impact = {
                        'metric': 'ROAS',
                        'current': roas_fc['current_value'],
                        'forecast_7d': forecast_roas,
                        'delta_pct': roas_change_pct,
                    }
                    
                    if current_roas < 1.5:
                        priority = 'P1'
                        effort = 'high'
                        action = f"{channel}のROAS低下トレンドが継続。配信面・訴求の即時刷新が必要です。まずはターゲティング設定を確認し、低効率の配信面を停止してください。"
                    else:
                        priority = 'P2'
                        effort = 'medium'
                        action = f"{channel}のROAS低下が予測されます。効率が回復する訴求にA/Bテストで切り替えるか、配信予算の調整を検討してください。"
                    
                    roi_score = max(40, 100 - abs(roas_change_pct))  # Higher score = more urgent
                    
                    recs.append(
                        QuantifiedRecommendation(
                            priority=priority,
                            channel=channel,
                            issue=f"ROAS低下トレンド（予測: {roas_change_pct:.1f}%）",
                            action=action,
                            reason=f"過去データから7日後のROAS低下が予測されます（確度 {confidence:.0%}）",
                            confidence=confidence,
                            expected_impact=expected_impact,
                            effort_level=effort,
                            roi_score=roi_score,
                        )
                    )
                
                # Uptrend = opportunity
                elif trend == 'upward' and roas_change_pct > 10 and confidence > 0.6:
                    expected_impact = {
                        'metric': 'ROAS',
                        'current': roas_fc['current_value'],
                        'forecast_7d': forecast_roas,
                        'delta_pct': roas_change_pct,
                    }
                    
                    priority = 'P3'
                    action = f"{channel}のROAS改善トレンドが見られます。この勝ちパターンを維持しながら、小刻みに予算増額テストを実施して破綻を確認してください。"
                    roi_score = max(20, int(roas_change_pct))
                    
                    recs.append(
                        QuantifiedRecommendation(
                            priority=priority,
                            channel=channel,
                            issue=f"ROAS改善トレンド（予測: +{roas_change_pct:.1f}%）",
                            action=action,
                            reason=f"過去7日のROAS改善が継続する見込み（確度 {confidence:.0%}）",
                            confidence=confidence,
                            expected_impact=expected_impact,
                            effort_level='low',
                            roi_score=roi_score,
                        )
                    )
            
            # Analyze CVR forecast
            if 'cvr' in metrics_forecast:
                cvr_fc = metrics_forecast['cvr']
                forecast_cvr = cvr_fc['forecast_value']
                confidence = cvr_fc['confidence']
                trend = cvr_fc['trend_direction']
                
                cvr_change_pct = ((forecast_cvr - cvr_fc['current_value']) / (cvr_fc['current_value'] + 1e-8)) * 100
                
                if trend == 'downward' and cvr_change_pct < -10 and confidence > 0.5:
                    expected_impact = {
                        'metric': 'CVR',
                        'current': cvr_fc['current_value'],
                        'forecast_7d': forecast_cvr,
                        'delta_pct': cvr_change_pct,
                    }
                    
                    priority = 'P2'
                    action = f"{channel}のCVR低下が予測されます。ユーザー体験に変化がないか、LPの読み込み速度やフォーム設計を点検してください。また、流入ユーザーのセグメント変化も確認してください。"
                    roi_score = 65
                    
                    recs.append(
                        QuantifiedRecommendation(
                            priority=priority,
                            channel=channel,
                            issue=f"CVR低下予測（-{abs(cvr_change_pct):.1f}%）",
                            action=action,
                            reason=f"直近のCVR低下が続く場合、さらに{abs(cvr_change_pct):.0f}%の低下が見込まれます",
                            confidence=confidence,
                            expected_impact=expected_impact,
                            effort_level='medium',
                            roi_score=roi_score,
                        )
                    )
        
        return recs
    
    @staticmethod
    def generate_from_impact_analysis(
        impact_analysis: Dict,
    ) -> List[QuantifiedRecommendation]:
        """
        Generate recommendations based on measured initiative impacts.
        
        Args:
            impact_analysis: Dict from impact_analysis.analyze_initiative_impact()
        
        Returns:
            List of QuantifiedRecommendation
        """
        recs = []
        
        for init_result in impact_analysis.get('impact_results', []):
            initiative = init_result['initiative']
            metric = init_result['metric']
            pct_change = init_result['pct_change']
            confidence = init_result['confidence']
            
            if pct_change > 10 and confidence > 0.6:
                # Positive impact - scale it up
                priority = 'P3'
                action = f"施策「{initiative}」が{metric}を{pct_change:.1f}%改善しました。同様の施策を他のチャネルでも試行するか、本施策の継続と最適化を推奨します。"
                expected_impact = {
                    'metric': metric.upper(),
                    'measured_change_pct': pct_change,
                    'confidence': confidence,
                }
                roi_score = min(100, int(pct_change))
                
                recs.append(
                    QuantifiedRecommendation(
                        priority=priority,
                        channel='cross-channel',
                        issue=f"成功施策を横展開: {initiative}",
                        action=action,
                        reason=f"定量効果が確認されており、確度{confidence:.0%}の信頼性があります",
                        confidence=confidence,
                        expected_impact=expected_impact,
                        effort_level='low',
                        roi_score=roi_score,
                    )
                )
            
            elif pct_change < -10 and confidence > 0.7:
                # Negative impact - stop or modify
                priority = 'P1'
                action = f"施策「{initiative}」が{metric}を{abs(pct_change):.1f}%悪化させています。即座に施策を見直すか停止してください。改善点を特定してから再展開してください。"
                expected_impact = {
                    'metric': metric.upper(),
                    'measured_change_pct': pct_change,
                    'confidence': confidence,
                }
                roi_score = 95
                
                recs.append(
                    QuantifiedRecommendation(
                        priority=priority,
                        channel='cross-channel',
                        issue=f"施策評価: {initiative}（ネガティブ）",
                        action=action,
                        reason=f"定量データから明確な負の効果が測定されています（確度{confidence:.0%}）",
                        confidence=confidence,
                        expected_impact=expected_impact,
                        effort_level='high',
                        roi_score=roi_score,
                    )
                )
        
        return recs
    
    @staticmethod
    def combine_recommendations(
        forecast_recs: List[QuantifiedRecommendation],
        impact_recs: List[QuantifiedRecommendation],
        rule_based_recs: List[Dict],
    ) -> List[Dict]:
        """
        Combine forecast, impact, and rule-based recommendations.
        Deduplicate and prioritize by ROI score.
        
        Args:
            forecast_recs: From generate_from_forecasts()
            impact_recs: From generate_from_impact_analysis()
            rule_based_recs: Existing rule-based recommendations (legacy format)
        
        Returns:
            Combined list of dicts, sorted by priority and ROI
        """
        # Convert quantified recs to dict format
        all_recs = []
        
        for rec in forecast_recs + impact_recs:
            all_recs.append({
                'priority': rec.priority,
                'channel': rec.channel,
                'issue': rec.issue,
                'action': rec.action,
                'reason': rec.reason,
                'confidence': rec.confidence,
                'expected_impact': rec.expected_impact,
                'effort_level': rec.effort_level,
                'roi_score': rec.roi_score,
                'score': int(rec.roi_score),  # For backward compatibility
                'source': 'quantified',
            })
        
        # Add existing rule-based recs
        for rec in rule_based_recs:
            rec['source'] = 'rule-based'
            all_recs.append(rec)
        
        # Deduplicate by (channel, issue)
        seen = set()
        deduped = []
        
        priority_rank = {"P1": 0, "P2": 1, "P3": 2}
        
        for rec in sorted(
            all_recs,
            key=lambda x: (
                priority_rank.get(x.get('priority', 'P3'), 99),
                -x.get('roi_score', x.get('score', 0)),
            ),
        ):
            key = (rec.get('channel', ''), rec.get('issue', ''))
            if key not in seen:
                seen.add(key)
                deduped.append(rec)
        
        return deduped[:15]  # Return top 15 recommendations


def enhance_recommendations_with_quantified_impact(
    original_recommendations: List[Dict],
    df: pd.DataFrame,
    channels_df: pd.DataFrame = None,
    impact_analysis: Dict = None,
) -> List[Dict]:
    """
    Enhance existing recommendations with forecast and impact data.
    
    Args:
        original_recommendations: List of existing recommendations
        df: Marketing data DataFrame
        channels_df: Current channel metrics
        impact_analysis: Optional impact analysis result
    
    Returns:
        Enhanced recommendations list
    """
    from src.forecasting import add_forecasts_to_analysis
    
    # Add forecasting
    snapshot = {}
    snapshot = add_forecasts_to_analysis(snapshot, df)
    
    generator = EnhancedRecommendationGenerator()
    
    # Generate forecast-based recommendations
    forecast_recs = []
    if channels_df is not None:
        forecast_recs = generator.generate_from_forecasts(
            snapshot.get('forecasts', {}),
            channels_df,
        )
    
    # Generate impact-based recommendations
    impact_recs = []
    if impact_analysis:
        impact_recs = generator.generate_from_impact_analysis(impact_analysis)
    
    # Combine all
    combined = generator.combine_recommendations(
        forecast_recs,
        impact_recs,
        original_recommendations,
    )
    
    return combined

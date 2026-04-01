"""
Analyst Agent - データ分析エージェント

深掘りデータ分析を実施し、隠れた原因や機会を発掘
"""

import logging
from typing import Dict, List, Any
from src.llm_client import ask_llm
from src import llm_helper

logger = logging.getLogger(__name__)


class AnalystAgent:
    """深掘り分析を行うエージェント"""
    
    def __init__(self):
        self.name = "Analyst"
        self.role = "analyst"
    
    def analyze_anomalies(self, df_summary: Dict, alerts: List[str]) -> Dict[str, Any]:
        """
        データの異常値を多角的に分析
        
        Args:
            df_summary: DuckDB 読み込み結果サマリ
            alerts: 既に検出されたアラート
        
        Returns:
            {
                "anomalies": "異常分析結果",
                "root_causes": ["原因1", "原因2", ...],
                "opportunities": ["機会1", "機会2", ...]
            }
        """
        try:
            context = {
                "data_summary": df_summary,
                "existing_alerts": alerts
            }
            
            prompt = llm_helper.build_agent_prompt(
                self.role,
                "Analyze the data deeply and identify 3-5 root causes for the anomalies. Also suggest 3-5 opportunities.",
                context
            )
            
            analysis = ask_llm(prompt, num_predict=2500, use_rag=True)
            
            return {
                "skipped": False,
                "analysis": analysis
            }
        except Exception as e:
            logger.error(f"Analyst anomaly analysis failed: {e}")
            return {"skipped": True, "reason": str(e)}
    
    def compare_benchmarks(self, channel_metrics: Dict, industry_benchmarks: Dict) -> str:
        """
        業界ベンチマークとの比較分析
        """
        prompt = f"""
Our Metrics:
{channel_metrics}

Industry Benchmarks:
{industry_benchmarks}

Analyze the gaps and identify which channels are underperforming vs. overperforming.
"""
        return ask_llm(prompt, num_predict=1500)

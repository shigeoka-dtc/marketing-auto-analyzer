"""
Planner Agent - 戦略立案エージェント

経営層向けの施策方針を立案し、優先順位付けを行う
"""

import logging
from typing import Dict, List, Any
from src.llm_client import ask_llm
from src import llm_helper

logger = logging.getLogger(__name__)


class PlannerAgent:
    """戦略立案を行うエージェント"""
    
    def __init__(self):
        self.name = "Planner"
        self.role = "planner"
    
    def plan_strategy(self, context: Dict[str, Any], max_iterations: int = 3) -> Dict[str, Any]:
        """
        データとレコメンデーションから戦略を立案
        
        Args:
            context: スナップショット、レコメンデーション等をまとめた辞書
            max_iterations: LLMの推論ステップ数
        
        Returns:
            {
                "strategy": "戦略概要文",
                "initiatives": [
                    {"name": "施策名", "impact": "予想効果", "priority": 1}
                ],
                "timeline": "実行スケジュール",
                "budget_allocation": "予算配分案"
            }
        """
        try:
            # Planner 用プロンプト組み立て
            prompt = llm_helper.build_agent_prompt(
                self.role,
                f"Given context of marketing data, create a 3-6 month strategy with prioritized initiatives. Max iterations: {max_iterations}",
                context
            )
            
            # LLM で戦略を生成
            strategy_text = ask_llm(
                prompt,
                num_predict=2500,
                use_rag=True
            )
            
            if strategy_text.startswith("["):
                logger.warning(f"Planner LLM failed: {strategy_text}")
                return {
                    "skipped": True,
                    "reason": strategy_text
                }
            
            # テキスト解析して構造化（簡易版）
            return {
                "skipped": False,
                "strategy": strategy_text,
                "iterations": max_iterations
            }
        
        except Exception as e:
            logger.error(f"Planner strategy generation failed: {e}")
            return {"skipped": True, "reason": str(e)}
    
    def refine_strategy(self, initial_strategy: str, feedback: List[str]) -> str:
        """
        初期戦略をフィードバックで洗練
        """
        prompt = f"""
Initial Strategy:
{initial_strategy}

Feedback for Refinement:
{chr(10).join(f"- {f}" for f in feedback)}

Please refine the strategy considering the feedback above.
"""
        return ask_llm(prompt, num_predict=2000)

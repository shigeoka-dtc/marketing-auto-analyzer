"""
Validator Agent - 検証・最適化エージェント

提案の現実性を検証し、ROI を最大化するための最適化を行う
"""

import logging
from typing import Dict, List, Any
from src.llm_client import ask_llm
from src import llm_helper

logger = logging.getLogger(__name__)


class ValidatorAgent:
    """提案の検証と最適化を行うエージェント"""
    
    def __init__(self):
        self.name = "Validator"
        self.role = "validator"
    
    def validate_strategy(self, strategy: str, constraints: Dict) -> Dict[str, Any]:
        """
        戦略の実現可能性を検証
        
        Args:
            strategy: 提案される戦略
            constraints: コスト、期間、リソース等の制約情報
        
        Returns:
            {
                "is_feasible": bool,
                "risk_factors": ["リスク1", "リスク2"],
                "mitigation_plans": ["対策1", "対策2"],
                "expected_roi": "ROI見積もり"
            }
        """
        try:
            context = {
                "strategy": strategy,
                "constraints": constraints
            }
            
            prompt = llm_helper.build_agent_prompt(
                self.role,
                "Validate the strategy feasibility. Identify risks and propose mitigation. Estimate ROI.",
                context
            )
            
            validation = ask_llm(prompt, num_predict=2500)
            
            return {
                "skipped": False,
                "validation": validation
            }
        except Exception as e:
            logger.error(f"Validator strategy validation failed: {e}")
            return {"skipped": True, "reason": str(e)}
    
    def optimize_for_roi(self, initiatives: List[Dict], budget: float) -> Dict[str, Any]:
        """
        与えられた予算で ROI を最大化するために施策を最適化
        """
        prompt = f"""
Initiatives to Prioritize (for ROI maximization):
{chr(10).join(f"- {init['name']}: Expected Impact {init['impact']}" for init in initiatives)}

Available Budget: ${budget}

Please recommend the optimal allocation of budget across initiatives to maximize ROI.
Consider:
1. Quick wins (high impact, low cost)
2. Strategic initiatives (medium-term growth)
3. Infrastructure improvements (foundational)
"""
        return ask_llm(prompt, num_predict=2000)

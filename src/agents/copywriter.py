"""
Copywriter Agent - コピー・施策提案エージェント

改善提案を実装可能な施策テキストに変換
"""

import logging
from typing import Dict, List, Any
from src.llm_client import ask_llm
from src import llm_helper

logger = logging.getLogger(__name__)


class CopywriterAgent:
    """施策テキスト生成を行うエージェント"""
    
    def __init__(self):
        self.name = "Copywriter"
        self.role = "copywriter"
    
    def generate_copy_variations(self, page_data: Dict, num_variations: int = 3) -> List[str]:
        """
        ページ改善用のコピー案を複数パターン生成
        
        Args:
            page_data: ページ分析結果
            num_variations: 生成するバリエーション数
        
        Returns:
            生成されたコピー案リスト
        """
        try:
            context = {
                "current_title": page_data.get("title", ""),
                "current_h1": page_data.get("h1", []),
                "current_ctas": page_data.get("unique_ctas", []),
                "findings": page_data.get("findings", []),
                "score": page_data.get("score", 0)
            }
            
            prompt = llm_helper.build_agent_prompt(
                self.role,
                f"Generate {num_variations} variations of improved page title, H1, and CTA copy. Focus on clarity, urgency, and conversion.",
                context
            )
            
            variations = ask_llm(prompt, num_predict=2000)
            return variations.split("\n\n") if variations else []
        
        except Exception as e:
            logger.error(f"Copywriter variation generation failed: {e}")
            return []
    
    def create_implementation_tickets(self, recommendations: List[str]) -> str:
        """
        レコメンデーションを実装チケットに変換
        """
        prompt = f"""
Marketing Recommendations:
{chr(10).join(f"- {r}" for r in recommendations)}

Convert each recommendation into a concrete implementation ticket with:
- Ticket Title
- Description
- AC (Acceptance Criteria)
- Effort Estimate (S/M/L)
- Expected Impact (%)
"""
        return ask_llm(prompt, num_predict=2500)

"""
Error Handling & Observability
エラーが隠れないように、失敗をメトリクス化し、レポートに degraded status を含める
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)


class AnalysisStatus:
    """分析ステップごとの成功/失敗を記録"""
    
    def __init__(self):
        self.statuses: Dict[str, Dict[str, Any]] = {}
    
    def record_success(self, step_name: str, message: str = ""):
        """記録: 成功"""
        self.statuses[step_name] = {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "message": message,
        }
        logger.info(f"✓ {step_name}: {message}")
    
    def record_failure(self, step_name: str, error: Exception, is_critical: bool = False):
        """記録: 失敗"""
        self.statuses[step_name] = {
            "status": "failed",
            "timestamp": datetime.now().isoformat(),
            "error": str(error),
            "error_type": type(error).__name__,
            "critical": is_critical,
        }
        level = logger.error if is_critical else logger.warning
        level(f"✗ {step_name} {'[CRITICAL]' if is_critical else '[NON-CRITICAL]'}: {error}")
    
    def record_skipped(self, step_name: str, reason: str = ""):
        """記録: スキップ"""
        self.statuses[step_name] = {
            "status": "skipped",
            "timestamp": datetime.now().isoformat(),
            "reason": reason,
        }
        logger.info(f"⊘ {step_name} skipped: {reason}")
    
    def get_summary(self) -> Dict[str, Any]:
        """サマリーを取得"""
        total = len(self.statuses)
        successful = sum(1 for s in self.statuses.values() if s["status"] == "success")
        failed = sum(1 for s in self.statuses.values() if s["status"] == "failed")
        critical_failed = sum(
            1 for s in self.statuses.values() 
            if s["status"] == "failed" and s.get("critical", False)
        )
        skipped = sum(1 for s in self.statuses.values() if s["status"] == "skipped")
        
        return {
            "total_steps": total,
            "successful": successful,
            "failed": failed,
            "critical_failures": critical_failed,
            "skipped": skipped,
            "overall_status": "failed" if critical_failed > 0 else "degraded" if failed > 0 else "success",
            "details": self.statuses,
        }
    
    def is_critical_failure(self) -> bool:
        """クリティカルな失敗があるか"""
        return any(
            s.get("status") == "failed" and s.get("critical", False)
            for s in self.statuses.values()
        )
    
    def get_degraded_block(self) -> str:
        """レポート用の degraded status ブロックを生成"""
        summary = self.get_summary()
        
        if summary["overall_status"] == "success":
            return ""
        
        lines = [
            "---",
            "",
            "## ⚠️ Analysis Status & Warnings",
            "",
            f"**Overall Status**: {summary['overall_status'].upper()}",
            f"- Successful Steps: {summary['successful']}/{summary['total_steps']}",
            f"- Failed Steps: {summary['failed']}",
            f"- Critical Failures: {summary['critical_failures']}",
            f"- Skipped Steps: {summary['skipped']}",
            "",
        ]
        
        # List failed steps
        failed_steps = [
            (name, details) for name, details in summary["details"].items()
            if details["status"] == "failed"
        ]
        
        if failed_steps:
            lines.append("### Failed Components")
            lines.append("")
            for step_name, details in failed_steps:
                lines.append(f"**{step_name}** [{details.get('error_type', 'Unknown')}]")
                lines.append(f"- Error: {details.get('error', 'Unknown')}")
                if details.get("critical"):
                    lines.append("- **CRITICAL**: This component failure may affect accuracy")
                lines.append("")
        
        lines.extend([
            "### Impact on Analysis",
            "",
            "Some analysis components failed during execution. "
            "The report above includes available data, but the following should be reviewed:",
            "",
        ])
        
        # Describe impact
        impacts = []
        if "forecasting" in summary["details"]:
            impacts.append("- **Forecasting**: Predictions may be unavailable or outdated")
        if "impact_analysis" in summary["details"]:
            impacts.append("- **Impact Analysis**: Initiative impact estimates may be incomplete")
        if "llm_enhancement" in summary["details"]:
            impacts.append("- **Recommendations**: Enhanced recommendations may not be generated")
        if "site_analysis" in summary["details"]:
            impacts.append("- **Site Analysis**: Competitor/strategic analysis may be incomplete")
        
        if impacts:
            for impact in impacts:
                lines.append(impact)
            lines.append("")
        
        lines.extend([
            "---",
            "",
        ])
        
        return "\n".join(lines)


# Global instance for tracking analysis
_global_status = AnalysisStatus()


def get_analysis_status() -> AnalysisStatus:
    """Get the global analysis status tracker"""
    return _global_status


def reset_analysis_status():
    """Reset the global status tracker"""
    global _global_status
    _global_status = AnalysisStatus()

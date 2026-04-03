"""
Marketing Auto Analyzer - Main Entry Point
Simplified orchestration using DataService, AnalysisService, EnhancementService, ReportService
"""

import argparse
import json
import logging
import os
from pathlib import Path

from src.orchestration import (
    DataService,
    AnalysisService,
    EnhancementService,
    ReportService,
)

TARGET_SITE_MAX_PAGES = int(os.getenv("TARGET_SITE_MAX_PAGES", "5"))


def configure_logger():
    logger = logging.getLogger("marketing_analyzer")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger


def run_analysis(
    force_reload: bool = False,
    max_site_pages: int = TARGET_SITE_MAX_PAGES,
    skip_llm: bool = False,
    skip_site_analysis: bool = False,
    dry_run: bool = False,
    save_json: bool = False,
    strategic_lp_analysis_count: int = 1,
) -> dict:
    """
    Orchestrate analysis pipeline using service layers
    
    Args:
        force_reload: Force reload of data from source
        max_site_pages: Maximum pages to analyze per site
        skip_llm: Skip LLM-based enhancements
        skip_site_analysis: Skip site analysis
        dry_run: Skip report generation and site visits
        save_json: Save JSON summary output
        strategic_lp_analysis_count: Number of strategic LP analyses to generate (default: 1)
        
    Returns:
        Analysis result dictionary
    """
    logger = configure_logger()
    
    try:
        # 1. Load and prepare data
        logger.info("Loading and preparing data...")
        snapshot, mart = DataService.load_and_prepare(force_reload=force_reload)
        snapshot["strategic_lp_analysis_count"] = strategic_lp_analysis_count
        logger.info("Data loaded successfully")
        
        # 2. Run core analysis
        logger.info("Running core analysis...")
        snapshot = AnalysisService.run_core_analysis(
            snapshot,
            skip_site_analysis=skip_site_analysis or dry_run
        )
        
        # 3. Run enhancements (forecasting, impact analysis, LLM)
        logger.info("Running enhancements...")
        snapshot = EnhancementService.run_enhancements(snapshot, skip_llm=skip_llm)
        
        # 4. Generate and save report
        logger.info("Generating report...")
        report_path = ReportService.generate_and_save_report(snapshot)
        
        # Optional: Save JSON summary
        if save_json:
            try:
                json_path = Path(report_path).parent / "analysis_snapshot.json"
                with open(json_path, "w") as f:
                    # Only serialize JSON-serializable parts
                    json.dump({
                        "snapshot_keys": list(snapshot.keys()),
                        "status": "completed",
                    }, f, indent=2)
                logger.info(f"JSON summary saved to: {json_path}")
            except Exception as e:
                logger.warning(f"Failed to save JSON summary: {e}")
        
        logger.info("Analysis complete")
        
        return {
            "status": "success",
            "snapshot": snapshot,
            "report_path": report_path,
        }
        
    except Exception as e:
        logger.error(f"Analysis failed: {e}", exc_info=True)
        return {
            "status": "failed",
            "error": str(e),
        }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Marketing Auto Analyzer - Comprehensive Marketing Analysis Pipeline"
    )
    parser.add_argument(
        "--force-reload",
        action="store_true",
        help="Force reload data from source CSV"
    )
    parser.add_argument(
        "--max-site-pages",
        type=int,
        default=TARGET_SITE_MAX_PAGES,
        help=f"Maximum pages to analyze per site (default: {TARGET_SITE_MAX_PAGES})"
    )
    parser.add_argument(
        "--skip-llm",
        action="store_true",
        help="Skip LLM-based enhancements (forecasting, recommendations, etc.)"
    )
    parser.add_argument(
        "--skip-site-analysis",
        action="store_true",
        help="Skip site analysis and web crawling"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Dry run: skip site analysis and report generation"
    )
    parser.add_argument(
        "--save-json",
        action="store_true",
        help="Save JSON summary alongside markdown report"
    )
    parser.add_argument(
        "--strategic-lp-count",
        type=int,
        default=1,
        help="Number of strategic LP analyses to generate (default: 1, for weakest sites)"
    )
    
    args = parser.parse_args()
    
    result = run_analysis(
        force_reload=args.force_reload,
        max_site_pages=args.max_site_pages,
        skip_llm=args.skip_llm,
        skip_site_analysis=args.skip_site_analysis,
        dry_run=args.dry_run,
        save_json=args.save_json,
        strategic_lp_analysis_count=args.strategic_lp_count,
    )
    
    if result["status"] == "success":
        print(f"\n✓ Analysis complete. Report: {result['report_path']}")
    else:
        print(f"\n✗ Analysis failed: {result.get('error', 'unknown error')}")
        exit(1)

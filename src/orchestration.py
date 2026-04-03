"""
Analysis Orchestration Service
責務をサービス単位に分割:
- DataService: ETL、データ読み込み
- AnalysisService: 分析処理
- EnhancementService: 予測、impact analysis などの拡張分析
- ReportService: レポート生成、永続化

エラーは "落ちにくい" 一方、"気づきにくい" リスクに対応
失敗をメトリクス化し、レポートに degraded status を含める
"""

import logging
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
import os

from src.observability import get_analysis_status

logger = logging.getLogger(__name__)


class DataService:
    """データ読み込みと準備処理"""
    
    @staticmethod
    def load_and_prepare(force_reload: bool = False) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        ETL からマート読み込みまでを担当
        
        Returns:
            (snapshot, mart): 分析用データセット
        """
        status = get_analysis_status()
        
        from src.etl import load_csv_to_duckdb
        from src.analysis import build_analysis_snapshot, read_mart
        
        try:
            if force_reload:
                load_csv_to_duckdb()
            
            snapshot = build_analysis_snapshot()
            mart = read_mart()
            
            status.record_success("data_loading", "Data loaded and prepared")
            return snapshot, mart
        except Exception as e:
            status.record_failure("data_loading", e, is_critical=True)
            raise


class AnalysisService:
    """コア分析処理層"""
    
    @staticmethod
    def run_core_analysis(snapshot: Dict[str, Any], 
                         skip_site_analysis: bool = False) -> Dict[str, Any]:
        """
        コア分析を実行（サイト分析、要約など）
        
        Args:
            snapshot: データスナップショット
            skip_site_analysis: サイト分析をスキップするか
            
        Returns:
            更新された snapshot
        """
        status = get_analysis_status()
        
        from src.deep_analysis import generate_deep_analysis
        from src.summary_service import generate_summary
        from src.url_targets import load_target_urls
        from src.url_analyzer import analyze_site
        from src.state import init_state, upsert_site_analysis_result
        from src.site_results_service import (
            build_site_error_result,
            is_actionable_site_result,
        )
        
        logger.info("Starting core analysis...")
        
        # Deep analysis
        try:
            snapshot["deep"] = generate_deep_analysis(snapshot)
            status.record_success("deep_analysis")
        except Exception as e:
            status.record_failure("deep_analysis", e, is_critical=False)
            snapshot["deep"] = {}
        
        # Summary
        try:
            snapshot["summary"] = generate_summary(snapshot)
            status.record_success("summary_generation")
        except Exception as e:
            status.record_failure("summary_generation", e, is_critical=False)
            snapshot["summary"] = {}
        
        # Site analysis (optional)
        if not skip_site_analysis:
            try:
                init_state()
                target_urls = load_target_urls()
                sites_analyzed = 0
                sites_failed = 0
                
                for url in target_urls[:5]:  # Limit to 5 sites
                    try:
                        result = analyze_site(url)
                        upsert_site_analysis_result(url, result)
                        sites_analyzed += 1
                    except Exception as e:
                        logger.warning(f"Site analysis failed for {url}: {e}")
                        error_result = build_site_error_result(url, str(e))
                        upsert_site_analysis_result(url, error_result)
                        sites_failed += 1
                        
                status.record_success("site_analysis", f"Analyzed {sites_analyzed} sites, {sites_failed} failed")
            except Exception as e:
                status.record_failure("site_analysis", e, is_critical=False)
        else:
            status.record_skipped("site_analysis", "Skipped by user")
        
        return snapshot


class EnhancementService:
    """拡張分析（予測、impact analysis など）"""
    
    @staticmethod
    def run_enhancements(snapshot: Dict[str, Any],
                        skip_llm: bool = False) -> Dict[str, Any]:
        """
        拡張分析を実行（失敗してもレポートは生成される）
        
        Args:
            snapshot: データスナップショット
            skip_llm: LLM 依存処理をスキップするか
            
        Returns:
            更新された snapshot
        """
        status = get_analysis_status()
        
        logger.info("Starting enhancements...")
        
        # 1. Forecasting
        try:
            from src.forecasting import add_forecasts_to_analysis
            add_forecasts_to_analysis(snapshot)
            status.record_success("forecasting")
        except Exception as e:
            status.record_failure("forecasting", e, is_critical=False)
            snapshot.setdefault("forecast_status", "failed")
        
        # 2. Impact Analysis
        try:
            from src.impact_analysis import analyze_initiative_impact
            if "initiatives" in snapshot:
                analyze_initiative_impact(snapshot)
                status.record_success("impact_analysis")
        except Exception as e:
            status.record_failure("impact_analysis", e, is_critical=False)
            snapshot.setdefault("impact_status", "failed")
        
        # 3. Recommendations & LLM Enhancement
        if not skip_llm:
            try:
                from src.recommend import generate_recommendations
                recommendations = generate_recommendations(snapshot)
                snapshot["recommendations"] = recommendations
                status.record_success("recommendations_generation")
                
                # Enhance with LLM
                try:
                    from src.recommend_enhanced import enhance_recommendations_with_quantified_impact
                    enhanced = enhance_recommendations_with_quantified_impact(
                        snapshot, 
                        recommendations
                    )
                    snapshot["recommendations_enhanced"] = enhanced
                    status.record_success("llm_enhancement")
                except Exception as e:
                    status.record_failure("llm_enhancement", e, is_critical=False)
                    
            except Exception as e:
                status.record_failure("recommendations_generation", e, is_critical=False)
        else:
            status.record_skipped("llm_enhancement", "LLM processing skipped by user")
        
        return snapshot


class ReportService:
    """レポート生成と永続化"""
    
    @staticmethod
    def generate_and_save_report(snapshot: Dict[str, Any],
                                 output_dir: Optional[str] = None) -> str:
        """
        スナップショットからレポートを生成して保存
        
        Args:
            snapshot: 分析済みスナップショット
            output_dir: 出力ディレクトリ（デフォルト: reports/）
            
        Returns:
            保存されたレポートファイルパス
        """
        status = get_analysis_status()
        
        from src.report import render_marketing_report, save_report
        from src.strategic_lp_analysis import generate_strategic_lp_analysis_report
        
        logger.info("Generating report...")
        
        # Strategic LP Analysis (configurable count)
        strategic_count = snapshot.get("strategic_lp_analysis_count", 1)
        strategic_reports = []
        
        try:
            # 最弱サイトの戦略LP分析（複数可能）
            if "worst_site" in snapshot and "worst_site_url" in snapshot:
                worst_url = snapshot["worst_site_url"]
                logger.info(f"Generating {strategic_count} strategic LP analysis for: {worst_url}")
                
                worst_site_data = snapshot.get("worst_site", {})
                strategic_input = {
                    "url": worst_url,
                    "site_data": worst_site_data,
                }
                
                try:
                    for i in range(strategic_count):
                        strategic_report = generate_strategic_lp_analysis_report(strategic_input)
                        strategic_reports.append(strategic_report)
                    status.record_success("strategic_lp_analysis", f"Generated {strategic_count} analyses")
                except Exception as e:
                    status.record_failure("strategic_lp_analysis", e, is_critical=False)
                    
        except Exception as e:
            status.record_failure("strategic_lp_analysis", e, is_critical=False)
        
        snapshot["strategic_reports"] = strategic_reports
        
        # Main Report with degraded status block
        report_md = render_marketing_report(snapshot)
        
        # Add observability block if there are issues
        degraded_block = status.get_degraded_block()
        if degraded_block:
            report_md += "\n" + degraded_block
        
        # Save
        if output_dir is None:
            output_dir = "reports/"
        
        try:
            report_path = save_report(report_md, output_dir=output_dir)
            status.record_success("report_generation", f"Report saved to {report_path}")
            logger.info(f"Report saved to: {report_path}")
            return report_path
        except Exception as e:
            status.record_failure("report_generation", e, is_critical=True)
            raise

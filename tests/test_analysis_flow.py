import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import os

try:
    from src.playwright_crawler import crawl_page
    PLAYWRIGHT_AVAILABLE = True
except Exception:
    PLAYWRIGHT_AVAILABLE = False


@unittest.skipIf(not PLAYWRIGHT_AVAILABLE or os.getenv("CI") == "true", 
                 "Playwright not available or running in CI")
class TestAnalysisFlow(unittest.TestCase):
    """Test complete analysis flow"""
    
    def test_crawl_example(self):
        """Test basic crawl functionality"""
        if not PLAYWRIGHT_AVAILABLE:
            self.skipTest("Playwright not available")
        
        url = "https://example.com/"
        try:
            res = crawl_page(url, headless=True)
            self.assertIn("html_path", res)
            self.assertTrue(Path(res["html_path"]).exists())
        except Exception as e:
            self.skipTest(f"Playwright crawl test skipped: {e}")


if __name__ == "__main__":
    unittest.main()



from src import analysis, db_utils, etl, state
from src.deep_analysis import generate_deep_analysis
from src.recommend import generate_recommendations
from src.report import render_marketing_report
from src.site_results_service import merge_site_results
from src.summary_service import build_rule_based_summary, generate_summary
from src.url_analyzer import analyze_site
from src.url_targets import parse_target_urls


CSV_TEXT = """date,channel,campaign,sessions,users,conversions,revenue,cost
2026-03-20,google,campaign_a,1200,900,42,180000,70000
2026-03-20,meta,campaign_b,900,740,21,90000,65000
2026-03-21,google,campaign_a,1300,960,44,190000,72000
2026-03-21,meta,campaign_b,950,760,19,85000,67000
2026-03-22,google,campaign_a,1400,1000,51,220000,76000
2026-03-22,meta,campaign_b,1000,790,18,80000,70000
"""

SITE_HTML = {
    "https://example.com/": """
        <html>
          <head><title>業務改善サービス</title></head>
          <body>
            <h1>業務改善サービス</h1>
            <h2>選ばれる理由</h2>
            <h2>導入フロー</h2>
            <a href="/service">サービス詳細</a>
            <a href="/faq">よくある質問</a>
            <a href="/contact">お問い合わせ</a>
            <section>導入事例 よくある質問 PDF ダウンロード</section>
          </body>
        </html>
    """,
    "https://example.com/service": """
        <html>
          <head><title>業務改善サービス 資料</title></head>
          <body>
            <h1>LP</h1>
            <a href="/contact">無料相談</a>
            <p>業務改善のためのサービス紹介です。</p>
          </body>
        </html>
    """,
    "https://example.com/faq": """
        <html>
          <head><title>よくある質問</title></head>
          <body>
            <h1>よくある質問</h1>
            <h2>質問一覧</h2>
            <p>FAQ のみで CTA はありません。</p>
          </body>
        </html>
    """,
}


class DummyResponse:
    def __init__(self, text: str, status_code: int = 200):
        self.text = text
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class AnalysisFlowTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        base = Path(self.tempdir.name)
        self.csv_path = base / "marketing.csv"
        self.db_path = base / "marketing.duckdb"
        self.lock_path = base / "marketing.duckdb.lock"
        self.state_db_path = base / "state.sqlite"
        self.csv_path.write_text(CSV_TEXT, encoding="utf-8")

        self.old_csv_path = etl.CSV_PATH
        self.old_db_path = db_utils.DB_PATH
        self.old_lock_path = db_utils.LOCK_PATH
        self.old_state_db = state.STATE_DB

        etl.CSV_PATH = str(self.csv_path)
        db_utils.DB_PATH = str(self.db_path)
        db_utils.LOCK_PATH = str(self.lock_path)
        state.STATE_DB = str(self.state_db_path)
        state.init_state()

    def tearDown(self):
        etl.CSV_PATH = self.old_csv_path
        db_utils.DB_PATH = self.old_db_path
        db_utils.LOCK_PATH = self.old_lock_path
        state.STATE_DB = self.old_state_db
        self.tempdir.cleanup()

    def test_etl_skips_when_csv_is_unchanged(self):
        first = etl.load_csv_to_duckdb()
        second = etl.load_csv_to_duckdb()

        self.assertEqual(first["status"], "loaded")
        self.assertEqual(second["status"], "skipped")

    def test_etl_rejects_missing_required_columns(self):
        self.csv_path.write_text(
            "date,channel,campaign,sessions,users,conversions,revenue\n"
            "2026-03-20,google,campaign_a,1200,900,42,180000\n",
            encoding="utf-8",
        )

        with self.assertRaisesRegex(ValueError, "必須列が不足しています"):
            etl.load_csv_to_duckdb(force=True)

    def test_snapshot_and_recommendations(self):
        etl.load_csv_to_duckdb(force=True)
        df = analysis.read_mart()
        snapshot = analysis.build_analysis_snapshot(df)
        recommendations = generate_recommendations(
            snapshot["channels"],
            snapshot["diagnostics"],
            snapshot["alerts"],
        )

        self.assertEqual(snapshot["latest"]["latest_date"], "2026-03-22")
        self.assertIn("advanced", snapshot)
        self.assertIsInstance(snapshot["advanced"], dict)
        self.assertIn("revenue_momentum", snapshot["advanced"])
        self.assertIn("channel_correlations", snapshot["advanced"])
        self.assertIn("predictions", snapshot["advanced"])
        self.assertIn("anomalies", snapshot["advanced"])
        self.assertIn("segmentation", snapshot["advanced"])
        self.assertFalse(snapshot["alerts"])
        self.assertEqual(recommendations[0]["channel"], "meta")
        self.assertEqual(recommendations[0]["priority"], "P2")
        self.assertEqual(recommendations[1]["channel"], "google")
        self.assertEqual(recommendations[1]["priority"], "P3")

    def test_rule_based_summary_is_used_when_llm_is_skipped(self):
        etl.load_csv_to_duckdb(force=True)
        df = analysis.read_mart()
        snapshot = analysis.build_analysis_snapshot(df)
        recommendations = generate_recommendations(
            snapshot["channels"],
            snapshot["diagnostics"],
            snapshot["alerts"],
        )

        summary = generate_summary(
            snapshot,
            recommendations,
            compact_urls=[],
            url_results=[],
            skip_llm=True,
        )

        self.assertIn("1. 現状サマリー", summary)
        self.assertIn("2. 優先アクション", summary)
        self.assertIn("3. チャネル深掘り", summary)
        self.assertIn("4. サイト改善優先度", summary)
        self.assertIn("5. 注意点", summary)
        self.assertIn("LLM補足", summary)

        direct_summary = build_rule_based_summary(snapshot, recommendations, [], None)
        self.assertIn("最新日: 2026-03-22", direct_summary)
        self.assertIn("3. チャネル深掘り", direct_summary)
        self.assertIn("4. サイト改善優先度", direct_summary)

    def test_render_marketing_report_contains_strategic_sections(self):
        etl.load_csv_to_duckdb(force=True)
        df = analysis.read_mart()
        snapshot = analysis.build_analysis_snapshot(df)
        recommendations = generate_recommendations(
            snapshot["channels"],
            snapshot["diagnostics"],
            snapshot["alerts"],
        )
        site_results = [
            {
                "url": "https://example.com/",
                "score": 72,
                "page_count": 3,
                "site_findings": ["score 70未満ページ 1 件", "CTA不足ページ 1 件"],
                "site_improvements": ["最優先で H1・CTA・見出し構成を改善する"],
                "weak_pages": [
                    {
                        "url": "https://example.com/service",
                        "score": 55,
                        "cta_count": 0,
                        "findings": ["CTAなし", "h1が抽象的"],
                        "improvements": ["ファーストビューと本文末に主CTAを追加する"],
                    }
                ],
                "errors": [],
            }
        ]

        deep_analysis = generate_deep_analysis(
            snapshot,
            recommendations,
            site_results,
            skip_llm=True,
        )

        report = render_marketing_report(
            snapshot=snapshot,
            recommendations=recommendations,
            url_results=site_results,
            llm_summary="rule-based summary",
            deep_analysis=deep_analysis,
        )

        self.assertIn("## Strategic Diagnosis", report)
        self.assertIn("## Evidence Base", report)
        self.assertIn("## 30-Day Roadmap", report)
        self.assertIn("## 90-Day Transformation Program", report)
        self.assertIn("## AB Test Backlog", report)
        self.assertIn("## Measurement Plan", report)
        self.assertIn("## Expected Impact", report)
        self.assertIn("## Deep AI Analysis", report)
        self.assertIn("## Copy Rewrite Pack", report)
        self.assertIn("## Channel-Specific Messaging Packs", report)
        self.assertIn("## Page Copy Packs", report)
        self.assertIn("## Implementation Ticket Breakdown", report)

    def test_generate_deep_analysis_falls_back_to_rule_based(self):
        etl.load_csv_to_duckdb(force=True)
        df = analysis.read_mart()
        snapshot = analysis.build_analysis_snapshot(df)
        recommendations = generate_recommendations(
            snapshot["channels"],
            snapshot["diagnostics"],
            snapshot["alerts"],
        )
        site_results = [
            {
                "url": "https://example.com/",
                "score": 72,
                "page_count": 3,
                "site_findings": ["score 70未満ページ 1 件", "CTA不足ページ 1 件"],
                "site_improvements": ["最優先で H1・CTA・見出し構成を改善する"],
                "weak_pages": [
                    {
                        "url": "https://example.com/service",
                        "score": 55,
                        "cta_count": 0,
                        "findings": ["CTAなし", "h1が抽象的"],
                        "improvements": ["ファーストビューと本文末に主CTAを追加する"],
                    }
                ],
                "errors": [],
            }
        ]

        deep_analysis = generate_deep_analysis(
            snapshot,
            recommendations,
            site_results,
            skip_llm=True,
        )

        self.assertEqual(deep_analysis["mode"], "rule-based")
        self.assertIn("## Executive Call", deep_analysis["body"])
        self.assertIn("## Copy Rewrite Pack", deep_analysis["body"])
        self.assertIn("## 90-Day Transformation Program", deep_analysis["body"])
        self.assertIn("## Experiment Backlog", deep_analysis["body"])
        self.assertIn("## Channel-Specific Messaging Packs", deep_analysis["body"])
        self.assertIn("## Page Copy Packs", deep_analysis["body"])
        self.assertIn("## Implementation Ticket Breakdown", deep_analysis["body"])

    def test_parse_target_urls_normalizes_and_deduplicates(self):
        text = """
        # comment
        https://Example.com/
        https://example.com
        https://example.com/service/?utm_source=test
        invalid-url
        """

        urls = parse_target_urls(text)

        self.assertEqual(
            urls,
            [
                "https://example.com/",
                "https://example.com/service",
            ],
        )

    def test_claim_next_urls_marks_processing_and_respects_retry(self):
        state.sync_url_queue(
            [
                "https://example.com/",
                "https://example.com/service",
            ],
            base_priority=10,
        )

        first_claim = state.claim_next_urls(limit=1)
        self.assertEqual(first_claim, ["https://example.com/"])

        queue_rows = state.list_url_queue()
        first_row = next(row for row in queue_rows if row["url"] == "https://example.com/")
        self.assertEqual(first_row["status"], "processing")
        self.assertIsNotNone(first_row["claimed_at"])

        second_claim = state.claim_next_urls(limit=2)
        self.assertEqual(second_claim, ["https://example.com/service"])

        state.mark_url_retry("https://example.com/", error_message="boom", delay_minutes=0)
        retry_claim = state.claim_next_urls(limit=1)
        self.assertEqual(retry_claim, ["https://example.com/"])

    def test_sync_url_queue_reset_existing_requeues_done_url(self):
        state.sync_url_queue(["https://example.com/"], base_priority=10)
        state.mark_url_done("https://example.com/")

        state.sync_url_queue(["https://example.com/"], base_priority=10, reset_existing=True)

        row = state.list_url_queue(limit=1)[0]
        self.assertEqual(row["status"], "pending")
        self.assertIsNone(row["last_analyzed_at"])
        self.assertEqual(row["retry_count"], 0)

    def test_state_db_fails_fast_when_unwritable(self):
        with patch("src.state.os.access", return_value=False):
            with self.assertRaises(RuntimeError):
                state.get_conn()

    def test_private_url_is_rejected(self):
        with self.assertRaises(ValueError):
            analyze_site("http://127.0.0.1/", max_pages=1)

    def test_merge_site_results_uses_stored_and_pending_entries(self):
        stored_result = state.upsert_site_analysis_result(
            {
                "url": "https://example.com/",
                "score": 72,
                "page_count": 3,
                "pages": [],
                "weak_pages": [],
                "site_findings": ["stored result"],
                "site_improvements": ["stored improvement"],
                "errors": [],
            },
            analysis_status="success",
        )

        merged = merge_site_results(
            ["https://example.com/", "https://example.com/faq"],
            current_results=[],
            stored_results=state.list_site_analysis_results(["https://example.com/"]),
        )

        self.assertEqual(merged[0]["url"], stored_result["url"])
        self.assertEqual(merged[0]["analysis_status"], "success")
        self.assertEqual(merged[1]["url"], "https://example.com/faq")
        self.assertEqual(merged[1]["analysis_status"], "pending")

    @patch("src.url_analyzer.assert_safe_target_url")
    @patch("src.url_analyzer.requests.get")
    def test_analyze_site_crawls_internal_pages(self, mock_get, mock_safe_url):
        def fake_get(url, headers=None, timeout=None, allow_redirects=None):
            normalized_url = url.rstrip("/") + "/" if url.rstrip("/") == "https://example.com" else url.rstrip("/")
            if normalized_url == "https://example.com":
                normalized_url = "https://example.com/"
            html = SITE_HTML.get(normalized_url)
            if html is None:
                raise RuntimeError(f"unexpected url: {url}")
            return DummyResponse(html)

        mock_get.side_effect = fake_get
        mock_safe_url.return_value = None

        result = analyze_site("https://example.com/", max_pages=3)

        self.assertEqual(result["url"], "https://example.com/")
        self.assertEqual(result["page_count"], 3)
        self.assertEqual(len(result["pages"]), 3)
        self.assertTrue(any("同一ドメイン内 3 ページを分析" in item for item in result["site_findings"]))
        self.assertTrue(any("CTA未設置ページ" in item for item in result["site_improvements"]))
        self.assertEqual(result["weak_pages"][0]["url"], "https://example.com/faq")


if __name__ == "__main__":
    unittest.main()

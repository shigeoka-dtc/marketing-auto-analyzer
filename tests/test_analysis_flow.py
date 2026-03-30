import tempfile
import unittest
from pathlib import Path

from src import analysis, db_utils, etl
from src.recommend import generate_recommendations
from src.worker import build_rule_based_summary, generate_summary


CSV_TEXT = """date,channel,campaign,sessions,users,conversions,revenue,cost
2026-03-20,google,campaign_a,1200,900,42,180000,70000
2026-03-20,meta,campaign_b,900,740,21,90000,65000
2026-03-21,google,campaign_a,1300,960,44,190000,72000
2026-03-21,meta,campaign_b,950,760,19,85000,67000
2026-03-22,google,campaign_a,1400,1000,51,220000,76000
2026-03-22,meta,campaign_b,1000,790,18,80000,70000
"""


class AnalysisFlowTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        base = Path(self.tempdir.name)
        self.csv_path = base / "marketing.csv"
        self.db_path = base / "marketing.duckdb"
        self.lock_path = base / "marketing.duckdb.lock"
        self.csv_path.write_text(CSV_TEXT, encoding="utf-8")

        self.old_csv_path = etl.CSV_PATH
        self.old_db_path = db_utils.DB_PATH
        self.old_lock_path = db_utils.LOCK_PATH

        etl.CSV_PATH = str(self.csv_path)
        db_utils.DB_PATH = str(self.db_path)
        db_utils.LOCK_PATH = str(self.lock_path)

    def tearDown(self):
        etl.CSV_PATH = self.old_csv_path
        db_utils.DB_PATH = self.old_db_path
        db_utils.LOCK_PATH = self.old_lock_path
        self.tempdir.cleanup()

    def test_etl_skips_when_csv_is_unchanged(self):
        first = etl.load_csv_to_duckdb()
        second = etl.load_csv_to_duckdb()

        self.assertEqual(first["status"], "loaded")
        self.assertEqual(second["status"], "skipped")

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
        self.assertIn("3. 注意点", summary)
        self.assertIn("LLM補足", summary)

        direct_summary = build_rule_based_summary(snapshot, recommendations, [], None)
        self.assertIn("最新日: 2026-03-22", direct_summary)


if __name__ == "__main__":
    unittest.main()

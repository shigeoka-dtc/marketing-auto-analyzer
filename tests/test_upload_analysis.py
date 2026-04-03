import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.upload_analysis import (
    analyze_uploaded_csv,
    analyze_uploaded_image,
    analyze_uploaded_marketing_assets,
)


CSV_TEXT = """date,channel,campaign,impressions,clicks,conversions,revenue,cost
2026-04-01,google,brand,10000,200,20,300000,100000
2026-04-01,meta,prospecting,12000,80,2,20000,90000
2026-04-02,google,brand,10500,210,22,320000,105000
2026-04-02,meta,prospecting,13000,75,1,10000,95000
"""


class UploadAnalysisTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.base = Path(self.tempdir.name)
        self.csv_path = self.base / "upload_metrics.csv"
        self.csv_path.write_text(CSV_TEXT, encoding="utf-8")
        self.image_path = self.base / "heatmap.png"
        self.image_path.write_bytes(b"fake-image-bytes")

    def tearDown(self):
        self.tempdir.cleanup()

    def test_analyze_uploaded_csv_detects_major_issue(self):
        result = analyze_uploaded_csv(self.csv_path)

        issue_codes = {issue["issue_code"] for issue in result["issues"]}
        subjects = {issue["subject"] for issue in result["issues"]}

        self.assertIn("low_roas_high_spend", issue_codes)
        self.assertIn("low_cvr", issue_codes)
        self.assertIn("meta", subjects)
        self.assertEqual(result["dimension"], "channel")
        self.assertIn("upload_metrics.csv", result["markdown"])

    @patch("src.upload_analysis.OLLAMA_ENABLED", False)
    @patch("src.upload_analysis.VISION_ANALYSIS_ENABLED", False)
    def test_analyze_uploaded_image_skips_when_vision_disabled(self):
        result = analyze_uploaded_image(self.image_path)

        self.assertEqual(result["status"], "skipped")
        self.assertIn("disabled", result["reason"].lower())

    @patch("src.upload_analysis.ask_llm", return_value="[LLM unavailable] mock")
    @patch("src.upload_analysis.ask_llm_vision")
    @patch("src.upload_analysis.VISION_ANALYSIS_ENABLED", True)
    @patch("src.upload_analysis.OLLAMA_ENABLED", True)
    def test_analyze_uploaded_marketing_assets_combines_csv_and_image(
        self,
        mock_vision,
        _mock_llm,
    ):
        mock_vision.return_value = """### 1. 何が起きているか
- ファーストビューでCTAに視線が集まっていません。

### 2. なぜCVに悪影響 or 好影響か
- CTA視認性が弱く、比較導線が散っています。
"""

        result = analyze_uploaded_marketing_assets(
            csv_paths=[str(self.csv_path)],
            image_paths=[str(self.image_path)],
            notes="Meta広告の失速要因を見たい",
            skip_llm=False,
            save_outputs=False,
        )

        self.assertEqual(result["status"], "success")
        self.assertIsNone(result["report_path"])
        self.assertEqual(len(result["csv_analyses"]), 1)
        self.assertEqual(len(result["image_analyses"]), 1)
        self.assertIn("CVR低下", result["final_markdown"])
        self.assertIn("CTA", result["final_markdown"])
        self.assertIn("最優先アクション", result["final_markdown"])

    def test_analyze_uploaded_marketing_assets_requires_input(self):
        with self.assertRaisesRegex(ValueError, "At least one CSV or image path is required"):
            analyze_uploaded_marketing_assets(save_outputs=False)


if __name__ == "__main__":
    unittest.main()

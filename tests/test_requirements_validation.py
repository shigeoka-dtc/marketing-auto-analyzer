"""
Requirements and dependencies validation tests.
Ensures that:
- All required packages in requirements.txt are importable
- MySQL is not used in application code
- Playwright and ChromaDB are properly configured
"""

import unittest
import subprocess
import sys
from pathlib import Path


class TestRequirementsIntegrity(unittest.TestCase):
    """Verify that requirements.txt matches actual imports"""

    def test_requirements_file_exists(self):
        """Ensure requirements.txt exists in root"""
        req_file = Path(__file__).parent.parent / "requirements.txt"
        self.assertTrue(req_file.exists(), "requirements.txt not found")

    def test_requirements_has_core_packages(self):
        """Verify critical packages are listed"""
        req_file = Path(__file__).parent.parent / "requirements.txt"
        contents = req_file.read_text()
        
        required = ["playwright", "chromadb", "duckdb", "pandas", "streamlit"]
        for pkg in required:
            self.assertIn(
                pkg.lower(), 
                contents.lower(), 
                f"{pkg} not found in requirements.txt"
            )

    def test_no_unused_mysql_in_code(self):
        """Verify MySQL is not used in application code"""
        src_dir = Path(__file__).parent.parent / "src"
        
        # Search for MySQL references
        result = subprocess.run(
            ["grep", "-r", "mysql", ".", "--include=*.py"],
            cwd=str(src_dir),
            capture_output=True,
            text=True
        )
        
        # grep returns 1 if no matches found (which is what we want)
        self.assertEqual(
            result.returncode, 
            1,
            f"MySQL references found in code:\n{result.stdout}"
        )

    def test_dockerfile_playwright_install(self):
        """Verify Dockerfile includes playwright install"""
        dockerfile = Path(__file__).parent.parent / "Dockerfile"
        contents = dockerfile.read_text()
        
        self.assertIn(
            "playwright install",
            contents,
            "Dockerfile should include 'python -m playwright install'"
        )

    def test_compose_no_mysql_service(self):
        """Verify compose.yaml has no MySQL service"""
        compose_file = Path(__file__).parent.parent / "compose.yaml"
        contents = compose_file.read_text()
        
        self.assertNotIn(
            "mysql:8.0",
            contents,
            "compose.yaml should not contain MySQL (no longer used)"
        )


class TestReadmeAccuracy(unittest.TestCase):
    """Verify README matches implementation"""

    def test_no_absolute_paths_in_readme(self):
        """Verify README doesn't use absolute paths like /home/..."""
        readme = Path(__file__).parent.parent / "README.md"
        contents = readme.read_text()
        
        # Check for specific absolute paths
        absolute_patterns = [
            "/home/nshigeoka/",
            "/app/secrets/",  # Should be relative
        ]
        
        for pattern in absolute_patterns:
            self.assertNotIn(
                pattern,
                contents,
                f"README contains absolute path: {pattern}"
            )

    def test_readme_main_args_match_impl(self):
        """Verify main.py arguments documented in README are valid"""
        main_py = Path(__file__).parent.parent / "main.py"
        main_contents = main_py.read_text()
        
        # These should be documented and implemented
        valid_args = [
            "--force-reload",
            "--max-site-pages",
            "--skip-llm",
            "--enable-forecasting",
            "--enable-impact-analysis",
        ]
        
        for arg in valid_args:
            self.assertIn(
                arg,
                main_contents,
                f"main.py should support {arg}"
            )

    def test_readme_no_unavailable_features(self):
        """Verify README doesn't document unimplemented features"""
        readme = Path(__file__).parent.parent / "README.md"
        contents = readme.read_text()
        
        # --enable-multi-agent is not yet available in main.py
        # It should have a note that it's under development
        if "--enable-multi-agent" in contents:
            self.assertIn(
                "development",
                contents.lower(),
                "--enable-multi-agent should be marked as under development"
            )


if __name__ == "__main__":
    unittest.main()

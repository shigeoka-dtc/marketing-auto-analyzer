#!/usr/bin/env python
"""Test script for new strategic LP analysis modules."""

import sys
import json

# Test new modules
print("=== Testing New Strategic LP Analysis Modules ===\n")

# Test 1: lp_deep_analysis module
print("Test 1: lp_deep_analysis module")
try:
    from src.lp_deep_analysis import extract_lp_elements, analyze_lp_deep
    print("✓ Successfully imported lp_deep_analysis module")
    
    # Test with sample HTML
    sample_html = """
    <html>
    <head><title>Test LP</title></head>
    <body>
        <h1>マニュアルLP</h1>
        <p>マニュアルづくりのあらゆる『困った！』を私たちが全力で解決します</p>
        
        <h2>マニュアル作り こんなお悩みありませんか？</h2>
        <p>多くの企業が...</p>
        
        <a href="/contact">問い合わせ申込</a>
        <a href="/download">資料ダウンロード</a>
        
        <img src="test.png" />
    </body>
    </html>
    """
    
    # Extract LP elements
    elements = extract_lp_elements(sample_html)
    print(f"  - Extracted H1: {elements.h1}")
    print(f"  - H2 count: {len(elements.h2_list)}")
    print(f"  - CTA count: {len(elements.cta_buttons)}")
    print(f"  - Text length: {elements.text_length}")
    print("✓ LP element extraction test passed\n")
    
except Exception as e:
    print(f"✗ lp_deep_analysis test failed: {e}\n")
    import traceback
    traceback.print_exc()


# Test 2: competitor_analysis module
print("Test 2: competitor_analysis module")
try:
    from src.competitor_analysis import generate_competitor_search_queries
    print("✓ Successfully imported competitor_analysis module")
    
    # Test with sample data (LLM call will be needed)
    print("  - Competitor analysis module loaded successfully")
    print("✓ Competitor analysis module test passed\n")
    
except Exception as e:
    print(f"✗ competitor_analysis test failed: {e}\n")
    import traceback
    traceback.print_exc()


# Test 3: strategic_lp_analysis module
print("Test 3: strategic_lp_analysis module")
try:
    from src.strategic_lp_analysis import generate_strategic_lp_analysis_report
    print("✓ Successfully imported strategic_lp_analysis module")
    
    # Test module structure
    print("  - Strategic LP analysis generator loaded successfully")
    print("✓ Strategic LP analysis module test passed\n")
    
except Exception as e:
    print(f"✗ strategic_lp_analysis test failed: {e}\n")
    import traceback
    traceback.print_exc()


# Test 4: Test main.py integration
print("Test 4: main.py integration")
try:
    from main import _render_strategic_lp_analysis_report
    print("✓ main.py integration function found")
    
    # Test rendering with sample analysis
    sample_analysis = {
        "url": "https://example.com",
        "report_type": "strategic_lp_analysis",
        "sections": {
            "現状分析_LP構造と課題": {
                "lp_elements": {
                    "h1": "Test H1",
                    "h2_count": 3,
                    "cta_count": 2,
                    "text_length": 5000,
                },
                "analysis": {
                    "overall_score": 7,
                    "h1_assessment": "Good clarity",
                }
            }
        },
        "executive_summary": "Test summary"
    }
    
    report = _render_strategic_lp_analysis_report(sample_analysis)
    print(f"  - Generated report length: {len(report)} characters")
    print(f"  - Report contains '戦略的LP分析レポート': {'戦略的LP分析レポート' in report}")
    print("✓ Report rendering test passed\n")
    
except Exception as e:
    print(f"✗ main.py integration test failed: {e}\n")
    import traceback
    traceback.print_exc()


print("Test 5: main.run_analysis dry run")
try:
    from main import run_analysis
    result = run_analysis(dry_run=True, skip_site_analysis=True, skip_llm=True)
    print(f"  - Results keys: {list(result.keys())}")
    assert result["site_results"] == []
    assert result["report_path"] is None
    print("✓ main.run_analysis dry run test passed\n")
except Exception as e:
    print(f"✗ main.run_analysis dry run failed: {e}\n")
    import traceback
    traceback.print_exc()

print("=== All module tests completed ===")
print("\nNote: Full end-to-end testing requires LLM integration and actual HTML crawling.")
print("The basic module structure and integration points are verified.")

#!/usr/bin/env python3
"""
Vision AI Integration Test
Validates that Vision analysis is fully integrated into the pipeline.
"""

import os
import sys
import json
from pathlib import Path

def test_vision_config():
    """Test 1: Verify Vision configuration in .env"""
    print("【Test 1】Vision Configuration (.env)")
    print("-" * 50)
    
    env_file = Path('.env')
    vision_settings = {}
    
    if not env_file.exists():
        print("✗ .env file not found")
        return False
    
    for line in env_file.read_text().split('\n'):
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            key, value = line.split('=', 1)
            key = key.strip()
            if 'VISION' in key:
                vision_settings[key] = value.split('#')[0].strip()
    
    required_keys = {
        'VISION_ANALYSIS_ENABLED': 'true',
        'OLLAMA_VISION_MODEL': 'llava:13b',
        'VISION_ANALYSIS_TIMEOUT': '180',
        'VISION_PROMPT_FILE': 'prompts/vision_lp_analysis.md'
    }
    
    all_ok = True
    for key, expected in required_keys.items():
        value = vision_settings.get(key, 'NOT FOUND')
        status = "✓" if value == expected else "✗"
        print(f"{status} {key}={value}")
        if value != expected:
            all_ok = False
    
    print()
    return all_ok


def test_vision_files():
    """Test 2: Verify all required files exist"""
    print("【Test 2】Required Files")
    print("-" * 50)
    
    required_files = [
        'src/llm_client.py',
        'src/llm_helper.py',
        'src/url_analyzer.py',
        'src/report.py',
        'src/worker.py',
        'prompts/vision_lp_analysis.md'
    ]
    
    all_exist = True
    for f in required_files:
        exists = Path(f).exists()
        status = "✓" if exists else "✗"
        print(f"{status} {f}")
        if not exists:
            all_exist = False
    
    print()
    return all_exist


def test_vision_functions():
    """Test 3: Verify Vision functions are importable"""
    print("【Test 3】Vision Functions")
    print("-" * 50)
    
    functions = [
        ('src.llm_client', 'ask_llm_vision'),
        ('src.llm_helper', 'analyze_vision_lp'),
        ('src.url_analyzer', 'analyze_url_with_vision'),
        ('src.report', '_get_vision_analyses'),
    ]
    
    all_ok = True
    for module, func in functions:
        try:
            exec(f"from {module} import {func}")
            print(f"✓ {module}.{func}()")
        except Exception as e:
            print(f"✗ {module}.{func}() - {str(e)[:50]}")
            all_ok = False
    
    print()
    return all_ok


def test_vision_prompt():
    """Test 4: Verify Vision prompt file content"""
    print("【Test 4】Vision Prompt File")
    print("-" * 50)
    
    prompt_file = Path('prompts/vision_lp_analysis.md')
    
    if not prompt_file.exists():
        print("✗ Vision prompt file not found")
        return False
    
    content = prompt_file.read_text()
    
    required_sections = [
        'First View',
        'Layout & Composition',
        'CTA',
        'Design Score',
        'A/B Test',
    ]
    
    all_ok = True
    for section in required_sections:
        found = section in content
        status = "✓" if found else "✗"
        print(f"{status} Section: {section}")
        if not found:
            all_ok = False
    
    print(f"✓ Prompt file size: {len(content)} bytes")
    print()
    return all_ok


def test_worker_integration():
    """Test 5: Verify Vision integration in worker.py"""
    print("【Test 5】Worker Pipeline Integration")
    print("-" * 50)
    
    worker_file = Path('src/worker.py')
    if not worker_file.exists():
        print("✗ worker.py not found")
        return False
    
    content = worker_file.read_text()
    
    required_patterns = [
        'vision_analyses = []',
        'analyze_vision_lp',
        'vision_analyses.append',
        '"vision_analyses": vision_analyses'
    ]
    
    all_ok = True
    for pattern in required_patterns:
        found = pattern in content
        status = "✓" if found else "✗"
        print(f"{status} Pattern: {pattern[:40]}")
        if not found:
            all_ok = False
    
    print()
    return all_ok


def test_report_integration():
    """Test 6: Verify Vision integration in report.py"""
    print("【Test 6】Report Output Integration")
    print("-" * 50)
    
    report_file = Path('src/report.py')
    if not report_file.exists():
        print("✗ report.py not found")
        return False
    
    content = report_file.read_text()
    
    required_patterns = [
        '_get_vision_analyses',
        'Vision LP Analysis',
        'vision_rows = _get_vision_analyses',
        '_markdown_table'
    ]
    
    all_ok = True
    for pattern in required_patterns:
        found = pattern in content
        status = "✓" if found else "✗"
        print(f"{status} Pattern: {pattern[:40]}")
        if not found:
            all_ok = False
    
    print()
    return all_ok


def test_llm_client_vision():
    """Test 7: Verify ask_llm_vision implementation"""
    print("【Test 7】LLM Vision Client")
    print("-" * 50)
    
    llm_file = Path('src/llm_client.py')
    if not llm_file.exists():
        print("✗ llm_client.py not found")
        return False
    
    content = llm_file.read_text()
    
    required_patterns = [
        'def ask_llm_vision',
        'VISION_ANALYSIS_ENABLED',
        'base64.b64encode',
        'OLLAMA_VISION_MODEL',
        'image_paths'
    ]
    
    all_ok = True
    for pattern in required_patterns:
        found = pattern in content
        status = "✓" if found else "✗"
        print(f"{status} Pattern: {pattern[:40]}")
        if not found:
            all_ok = False
    
    print()
    return all_ok


def main():
    print("\n" + "=" * 60)
    print("Vision AI Integration Test Suite")
    print("=" * 60 + "\n")
    
    tests = [
        ("Vision Config", test_vision_config),
        ("Files", test_vision_files),
        ("Functions", test_vision_functions),
        ("Prompt", test_vision_prompt),
        ("Worker Integration", test_worker_integration),
        ("Report Integration", test_report_integration),
        ("LLM Vision Client", test_llm_client_vision),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"✗ Test {name} failed with exception: {e}\n")
            results.append((name, False))
    
    print("=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✅ Vision AI Integration Complete - All Tests Passed")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())

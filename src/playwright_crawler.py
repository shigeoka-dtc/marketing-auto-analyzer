"""
Playwright を使ったクロールモジュール（同期API想定）。
機能:
- JS を実行してレンダリング後の HTML を取得
- スクリーンショットを保存
- DOM スナップショット / メタ情報を返す
注意:
- 実行前に `python -m playwright install` が必要
"""
import os
import time
import hashlib
from urllib.parse import urlparse
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List

from playwright.sync_api import sync_playwright

REPORTS_DIR = Path("reports")

def _make_output_dir(url: str) -> Path:
    parsed = urlparse(url)
    domain = parsed.netloc.replace(":", "_")
    ts = int(time.time())
    out = REPORTS_DIR / f"{domain}" / str(ts)
    out.mkdir(parents=True, exist_ok=True)
    return out

def _safe_filename(url: str) -> str:
    h = hashlib.sha1(url.encode("utf-8")).hexdigest()[:10]
    return f"{h}.html"

def crawl_page(url: str, max_wait: int = 5000, viewport: Tuple[int,int]=(1280,800), headless: bool=True) -> Dict[str, Any]:
    """
    URL を Playwright で開きレンダリング済み HTML とスクリーンショットを保存し、メタ情報を返す。
    戻り値:
      {
        "url": url,
        "output_dir": str(Path),
        "html_path": str,
        "screenshot_path": str,
        "title": str,
        "status": int,
        "meta": { "description": "...", ... },
      }
    """
    out_dir = _make_output_dir(url)
    html_path = out_dir / _safe_filename(url)
    screenshot_path = out_dir / "screenshot.png"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(viewport={"width": viewport[0], "height": viewport[1]})
        page = context.new_page()
        try:
            response = page.goto(url, wait_until="networkidle", timeout=max_wait)
            status = response.status if response else None
        except Exception:
            # タイムアウトなど許容して継続
            status = None

        # wait a bit to allow client-side navs
        try:
            page.wait_for_timeout(500)
        except Exception:
            pass

        try:
            title = page.title()
        except Exception:
            title = ""

        # DOM content after render
        content = page.content()
        html_path.write_text(content, encoding="utf-8")

        # screenshot
        try:
            page.screenshot(path=str(screenshot_path), full_page=True)
        except Exception:
            # 柔軟にエラー回避
            pass

        # extract some meta tags
        meta = {}
        try:
            meta_description = page.locator("head > meta[name='description']").get_attribute("content")
            if meta_description:
                meta["description"] = meta_description
        except Exception:
            pass

        browser.close()

    return {
        "url": url,
        "output_dir": str(out_dir),
        "html_path": str(html_path),
        "screenshot_path": str(screenshot_path),
        "title": title,
        "status": status,
        "meta": meta,
    }

# 小さなユーティリティ: 複数ページクロール（target pages list）
def crawl_pages(urls: List[str], headless: bool=True, max_pages: int=8) -> List[Dict[str, Any]]:
    results = []
    for i, u in enumerate(urls):
        if i >= max_pages:
            break
        try:
            r = crawl_page(u, headless=headless)
            results.append(r)
        except Exception as e:
            results.append({"url": u, "error": str(e)})
    return results
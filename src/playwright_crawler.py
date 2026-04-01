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
import logging
from urllib.parse import urlparse
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List

from playwright.sync_api import sync_playwright

logger = logging.getLogger(__name__)

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

def crawl_page(url: str, max_wait: int = 5000, viewport: Tuple[int,int]=(1280,800), headless: bool=True, full_page: bool=True) -> Dict[str, Any]:
    """
    URL を Playwright で開きレンダリング済み HTML とスクリーンショットを保存し、メタ情報を返す。
    
    Args:
        url: クロール対象URL
        max_wait: ページロード待機時間（ms）
        viewport: ブラウザウィンドウサイズ (width, height)
        headless: ヘッドレスモード（通常: True）
        full_page: フルページスクリーンショット取得（True: 全ページ、False: viewport）
    
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
        except Exception as e:
            # タイムアウトなど許容して継続
            logger.warning(f"Page load failed for {url}: {e}")
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

        # screenshot（フルページまたはビューポート）
        screenshot_saved = False
        try:
            page.screenshot(path=str(screenshot_path), full_page=full_page)
            # ファイル存在確認
            if screenshot_path.exists():
                logger.info(f"Screenshot saved: {screenshot_path} ({screenshot_path.stat().st_size} bytes)")
                screenshot_saved = True
            else:
                logger.warning(f"Screenshot file not created: {screenshot_path}")
        except Exception as e:
            logger.error(f"Screenshot capture failed for {url}: {e}")

        # extract some meta tags
        meta = {}
        try:
            meta_description = page.locator("head > meta[name='description']").get_attribute("content")
            if meta_description:
                meta["description"] = meta_description
        except Exception:
            pass

        browser.close()

    result = {
        "url": url,
        "output_dir": str(out_dir),
        "html_path": str(html_path),
        "screenshot_path": str(screenshot_path) if screenshot_saved else None,
        "title": title,
        "status": status,
        "meta": meta,
    }
    
    return result

# 小さなユーティリティ: 複数ページクロール（target pages list）
def crawl_pages(urls: List[str], headless: bool=True, max_pages: int=8) -> List[Dict[str, Any]]:
    """複数URLをクロール"""
    results = []
    for i, u in enumerate(urls):
        if i >= max_pages:
            break
        try:
            logger.info(f"Crawling {i+1}/{min(len(urls), max_pages)}: {u}")
            r = crawl_page(u, headless=headless)
            results.append(r)
        except Exception as e:
            logger.error(f"Crawl failed for {u}: {e}", exc_info=True)
            results.append({"url": u, "error": str(e)})
    return results
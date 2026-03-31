import os
import re
from collections import Counter, deque
from urllib.parse import urljoin, urlsplit, urlunsplit

import requests
from bs4 import BeautifulSoup

from src.url_security import assert_safe_target_url
from src.playwright_crawler import crawl_page as _crawl_with_playwright

USE_PLAYWRIGHT = os.getenv("USE_PLAYWRIGHT", "false").lower() in ("1","true","yes")

def analyze_url(url: str, include_internal_links: bool = False) -> dict:
    if USE_PLAYWRIGHT:
        # Render with Playwright and read the generated HTML
        pd = _crawl_with_playwright(url, headless=os.getenv("PLAYWRIGHT_HEADLESS","true").lower() in ("1","true","yes"))
        html_path = pd.get("html_path")
        if not html_path:
            # fallback to existing fetch behaviour
            final_url, html = _fetch_html(url)
        else:
            final_url = url  # playwright returns content of the requested URL
            with open(html_path, "r", encoding="utf-8") as fh:
                html = fh.read()
    else:
        final_url, html = _fetch_html(url)

    return _analyze_html(final_url, html, include_internal_links=include_internal_links)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/123 Safari/537.36"
    )
}
URL_ANALYSIS_TIMEOUT = int(os.getenv("URL_ANALYSIS_TIMEOUT", "20"))
MAX_INTERNAL_LINKS_PER_PAGE = int(os.getenv("MAX_INTERNAL_LINKS_PER_PAGE", "20"))
URL_ANALYSIS_MAX_REDIRECTS = int(os.getenv("URL_ANALYSIS_MAX_REDIRECTS", "5"))

EXCLUDED_LINK_PREFIXES = ("mailto:", "tel:", "javascript:", "#")
EXCLUDED_EXTENSIONS = (
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".svg",
    ".webp",
    ".pdf",
    ".zip",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".ppt",
    ".pptx",
)


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _unique_keep_order(values: list[str]) -> list[str]:
    seen = set()
    unique_values = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        unique_values.append(value)
    return unique_values


def _normalize_cta(text: str) -> str:
    text = (text or "").replace("\u3000", " ")
    text = _clean(text)
    text = text.replace("  ", " ")
    text = text.replace("を 申込む", "を申込む")
    text = text.replace("カウンセリング ", "カウンセリング")
    return text


def _normalize_url(url: str) -> str:
    value = (url or "").strip()
    if not value:
        return ""

    parsed = urlsplit(value)
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
        return ""

    path = parsed.path or "/"
    if path != "/":
        path = path.rstrip("/")

    return urlunsplit(
        (
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            path,
            "",
            "",
        )
    )


def _is_cta(text: str, href: str) -> bool:
    href_l = (href or "").lower()

    if text in {"詳しくはこちら", "詳細はこちら", "請負", "常駐", "派遣"}:
        return False

    if "詳しくはこちら" in text:
        return False

    primary_keywords = [
        "お問い合わせ",
        "問合せ",
        "申込",
        "申し込み",
        "お申込み",
        "相談",
    ]
    secondary_keywords = [
        "ダウンロード",
        "資料請求",
        "資料",
    ]

    if any(keyword in text for keyword in primary_keywords + secondary_keywords):
        return len(text) <= 40

    if any(hint in href_l for hint in ["contact", "inquiry", "form", "download", "pdf"]):
        return len(text) <= 40

    return False


def _extract_internal_links(base_url: str, soup: BeautifulSoup) -> list[str]:
    base = urlsplit(base_url)
    links = []

    for anchor in soup.find_all("a", href=True):
        href = (anchor.get("href") or "").strip()
        if not href or href.startswith(EXCLUDED_LINK_PREFIXES):
            continue

        absolute_url = _normalize_url(urljoin(base_url, href))
        if not absolute_url:
            continue

        candidate = urlsplit(absolute_url)
        if candidate.netloc != base.netloc:
            continue

        if candidate.path.lower().endswith(EXCLUDED_EXTENSIONS):
            continue

        links.append(absolute_url)

    return _unique_keep_order(links)[:MAX_INTERNAL_LINKS_PER_PAGE]


def _analyze_html(url: str, html: str, include_internal_links: bool = False) -> dict:
    soup = BeautifulSoup(html, "lxml")

    title = _clean(soup.title.get_text()) if soup.title else ""
    h1_list = [_clean(node.get_text(" ", strip=True)) for node in soup.find_all("h1")]
    h2_list = [_clean(node.get_text(" ", strip=True)) for node in soup.find_all("h2")]

    links = []
    for anchor in soup.find_all("a"):
        text = _clean(anchor.get_text(" ", strip=True))
        href = anchor.get("href", "")
        if text:
            links.append({"text": text, "href": href})

    ctas = []
    for link in links:
        text = _normalize_cta(link["text"])
        href = link["href"]
        if _is_cta(text, href):
            ctas.append(text)

    unique_ctas = sorted(set(ctas))
    body_text = _clean(soup.get_text(" ", strip=True))
    text_length = len(body_text)

    has_faq = "よくある質問" in body_text or "FAQ" in body_text
    has_case = "支援事例" in body_text or "導入事例" in body_text or "事例" in body_text
    has_pdf = "PDF" in body_text or "ダウンロード" in body_text

    score = 100
    findings = []
    improvements = []

    if not title:
        score -= 15
        findings.append("titleなし")
        improvements.append("titleにサービス名と検索意図が伝わる訴求を入れる")
    elif len(title) < 20:
        score -= 5
        findings.append("titleが短い")
        improvements.append("titleを20-32文字程度で具体化する")

    if not h1_list:
        score -= 20
        findings.append("h1なし")
        improvements.append("H1でページの価値提案を明確にする")

    if h1_list and any(h1 == "LP" or h1.endswith("LP") for h1 in h1_list):
        score -= 10
        findings.append("h1が抽象的")
        improvements.append("H1を検索意図に沿った具体的な表現へ変更する")

    if h1_list and title and "マニュアル作成サービス" in title and "マニュアルLP" in h1_list:
        score -= 5
        improvements.append("titleとH1の意味を揃える")

    if len(h2_list) < 2:
        score -= 5
        findings.append("見出しが少ない")
        improvements.append("H2を増やして価値訴求と導線を整理する")

    if len(unique_ctas) == 0:
        score -= 15
        findings.append("CTAなし")
        improvements.append("ファーストビューと本文末に主CTAを追加する")
    elif len(unique_ctas) >= 4:
        score -= 8
        findings.append("CTAが分散")
        improvements.append("CTAが分散しているため主CVを1つに寄せる")

    if text_length < 400:
        score -= 5
        findings.append("本文量が少ない")
        improvements.append("比較情報や導入メリットを追記する")

    if has_case:
        findings.append("事例あり")
        improvements.append("事例に定量成果を追加すると説得力が上がる")
    else:
        findings.append("事例なし")
        improvements.append("導入事例や実績を追加して信頼性を高める")

    if has_faq:
        findings.append("FAQあり")
    else:
        findings.append("FAQなし")
        improvements.append("FAQを追加して導入前の不安を減らす")

    if has_pdf:
        findings.append("PDF導線あり")
    else:
        findings.append("PDF導線なし")
        improvements.append("資料請求やホワイトペーパー導線を追加する")

    result = {
        "url": url,
        "title": title,
        "h1": h1_list,
        "h2_count": len(h2_list),
        "cta_count": len(ctas),
        "unique_ctas": unique_ctas,
        "has_faq": has_faq,
        "has_case": has_case,
        "has_pdf": has_pdf,
        "text_length": text_length,
        "score": max(score, 0),
        "findings": _unique_keep_order(findings),
        "improvements": _unique_keep_order(improvements),
    }

    if include_internal_links:
        result["internal_links"] = _extract_internal_links(url, soup)

    return result


def _fetch_html(url: str) -> tuple[str, str]:
    current_url = url
    for _ in range(URL_ANALYSIS_MAX_REDIRECTS + 1):
        assert_safe_target_url(current_url)
        response = requests.get(
            current_url,
            headers=HEADERS,
            timeout=URL_ANALYSIS_TIMEOUT,
            allow_redirects=False,
        )
        headers = getattr(response, "headers", {}) or {}
        status_code = getattr(response, "status_code", 200)

        if 300 <= status_code < 400:
            location = headers.get("Location") or headers.get("location")
            if not location:
                raise RuntimeError("リダイレクト先がありません")
            redirected_url = _normalize_url(urljoin(current_url, location))
            if not redirected_url:
                raise RuntimeError("リダイレクト先URLが不正です")
            current_url = redirected_url
            continue

        response.raise_for_status()
        content_type = (headers.get("Content-Type") or headers.get("content-type") or "").lower()
        if content_type and not any(token in content_type for token in ["text/html", "application/xhtml+xml", "text/plain"]):
            raise ValueError(f"HTMLではないレスポンスです: {content_type}")
        return current_url, response.text

    raise RuntimeError(f"リダイレクトが多すぎます: {URL_ANALYSIS_MAX_REDIRECTS} 回超")


def analyze_url(url: str, include_internal_links: bool = False) -> dict:
    final_url, html = _fetch_html(url)
    return _analyze_html(final_url, html, include_internal_links=include_internal_links)


def _build_site_summary(start_url: str, pages: list[dict], errors: list[dict]) -> dict:
    page_scores = [page["score"] for page in pages]
    weak_pages = sorted(pages, key=lambda page: (page.get("score", 0), page.get("url", "")))[:3]

    site_findings = [f"同一ドメイン内 {len(pages)} ページを分析"]
    site_improvements = []

    low_score_pages = [page for page in pages if page["score"] < 70]
    no_cta_pages = [page for page in pages if page["cta_count"] == 0]
    no_case_pages = [page for page in pages if not page["has_case"]]
    no_faq_pages = [page for page in pages if not page["has_faq"]]
    no_pdf_pages = [page for page in pages if not page["has_pdf"]]
    no_h1_pages = [page for page in pages if not page["h1"]]

    if low_score_pages:
        site_findings.append(f"score 70未満ページ {len(low_score_pages)} 件")
        weakest = min(low_score_pages, key=lambda page: page["score"])
        site_improvements.append(
            f"最優先で {weakest['url']} のH1・CTA・見出し構成を改善する"
        )

    if no_cta_pages:
        site_findings.append(f"CTA不足ページ {len(no_cta_pages)} 件")
        site_improvements.append(
            f"CTA未設置ページ {len(no_cta_pages)} 件に主CTAを追加する"
        )

    if no_h1_pages:
        site_improvements.append(
            f"H1未設定ページ {len(no_h1_pages)} 件のメイン訴求を明確にする"
        )

    if len(no_case_pages) >= max(1, (len(pages) + 1) // 2):
        site_improvements.append("複数ページに導入事例・実績を追加して信頼性を補強する")

    if len(no_faq_pages) >= max(1, (len(pages) + 1) // 2):
        site_improvements.append("FAQを横断的に整備して問い合わせ前の不安を減らす")

    if len(no_pdf_pages) >= max(1, (len(pages) + 1) // 2):
        site_improvements.append("資料請求やホワイトペーパー導線を横断的に追加する")

    titles = [page["title"] for page in pages if page["title"]]
    duplicate_titles = [title for title, count in Counter(titles).items() if count >= 2]
    if duplicate_titles:
        site_findings.append("title重複あり")
        site_improvements.append("重複titleを解消してページごとの検索意図を分ける")

    repeated_improvements = Counter(
        improvement
        for page in pages
        for improvement in page.get("improvements", [])
    )
    for improvement, count in repeated_improvements.most_common(2):
        if count >= 2:
            site_improvements.append(f"{count}ページで共通: {improvement}")

    if errors:
        site_findings.append(f"取得失敗ページ {len(errors)} 件")

    return {
        "url": start_url,
        "score": round(sum(page_scores) / len(page_scores)),
        "page_count": len(pages),
        "pages": sorted(pages, key=lambda page: (page.get("score", 0), page.get("url", ""))),
        "weak_pages": weak_pages,
        "site_findings": _unique_keep_order(site_findings),
        "site_improvements": _unique_keep_order(site_improvements),
        "errors": errors,
    }


def analyze_site(start_url: str, max_pages: int = 5) -> dict:
    normalized_start = _normalize_url(start_url)
    if not normalized_start:
        raise ValueError("分析対象URLは http:// または https:// で始めてください")
    assert_safe_target_url(normalized_start)

    pending = deque([normalized_start])
    visited = set()
    pages = []
    errors = []
    page_limit = max(1, int(max_pages))

    while pending and len(pages) < page_limit:
        current_url = pending.popleft()
        if current_url in visited:
            continue

        visited.add(current_url)

        try:
            page_result = analyze_url(current_url, include_internal_links=True)
        except Exception as exc:
            errors.append({"url": current_url, "error": str(exc)})
            continue

        final_url = page_result.get("url", current_url)
        visited.add(final_url)
        internal_links = page_result.pop("internal_links", [])
        pages.append(page_result)

        for internal_link in internal_links:
            if internal_link in visited or internal_link in pending:
                continue
            if len(pages) + len(pending) >= page_limit * 4:
                break
            pending.append(internal_link)

    if not pages:
        first_error = errors[0]["error"] if errors else "ページを取得できませんでした"
        raise RuntimeError(f"サイト分析に失敗しました: {first_error}")

    return _build_site_summary(normalized_start, pages, errors)

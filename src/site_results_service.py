from datetime import UTC, datetime


def site_result_status(result: dict) -> str:
    return result.get("analysis_status", "success")


def is_actionable_site_result(result: dict) -> bool:
    status = site_result_status(result)
    score = result.get("score")
    return status == "success" and score is not None


def build_site_error_result(url: str, error_message: str) -> dict:
    return {
        "url": url,
        "score": None,
        "page_count": 0,
        "pages": [],
        "weak_pages": [],
        "site_findings": [f"分析失敗: {error_message}"],
        "site_improvements": ["URL到達性、robots、認証、タイムアウト設定を確認する"],
        "errors": [{"url": url, "error": error_message}],
        "analysis_status": "error",
        "analyzed_at": datetime.now(UTC).isoformat(),
    }


def build_pending_site_result(url: str) -> dict:
    return {
        "url": url,
        "score": None,
        "page_count": 0,
        "pages": [],
        "weak_pages": [],
        "site_findings": ["まだサイト分析が実行されていません"],
        "site_improvements": ["worker が最初のサイト巡回を完了するまで待機"],
        "errors": [],
        "analysis_status": "pending",
        "analyzed_at": None,
    }


def compact_site_results(url_results: list[dict]) -> list[dict]:
    compact = []
    for result in url_results:
        compact.append(
            {
                "url": result.get("url"),
                "score": result.get("score"),
                "page_count": result.get("page_count"),
                "analysis_status": site_result_status(result),
                "analyzed_at": result.get("analyzed_at"),
                "site_findings": result.get("site_findings", [])[:3],
                "site_improvements": result.get("site_improvements", [])[:3],
                "weak_pages": [
                    {
                        "url": page.get("url"),
                        "score": page.get("score"),
                    }
                    for page in result.get("weak_pages", [])[:2]
                ],
            }
        )
    return compact


def merge_site_results(target_urls: list[str], current_results: list[dict], stored_results: list[dict]) -> list[dict]:
    current_by_url = {result.get("url"): result for result in current_results if result.get("url")}
    stored_by_url = {result.get("url"): result for result in stored_results if result.get("url")}

    merged = []
    for url in target_urls:
        merged.append(
            current_by_url.get(url)
            or stored_by_url.get(url)
            or build_pending_site_result(url)
        )

    if merged:
        return merged

    merged.extend(current_results)
    merged.extend(
        result for result in stored_results
        if result.get("url") not in {item.get("url") for item in merged}
    )
    return merged

def get_strategic_analysis_input(site_result: dict) -> list[dict]:
    """
    戦略LP分析に必要な入力を、初回クロール済みの site_result から取り出す。
    weak_pages に対応する pages の内容を優先して返し、再クロールを避ける。
    """
    pages = site_result.get("pages", []) or []
    weak_pages = site_result.get("weak_pages", []) or []

    page_by_url = {}
    for page in pages:
        url = page.get("url")
        if url:
            page_by_url[url] = page

    results = []
    for weak_page in weak_pages:
        url = weak_page.get("url") or site_result.get("url")
        if not url:
            continue

        page = page_by_url.get(url, {})

        service_description = ""
        findings = weak_page.get("findings", [])
        if findings:
            service_description = findings[0]

        if not service_description:
            page_findings = page.get("findings", [])
            if page_findings:
                service_description = page_findings[0]

        results.append(
            {
                "url": url,
                "title": page.get("title", weak_page.get("title", "")),
                "html": page.get("html", ""),
                "excerpt": page.get("excerpt", page.get("body_excerpt", "")),
                "body_excerpt": page.get("body_excerpt", page.get("excerpt", "")),
                "service_description": service_description,
                "findings": weak_page.get("findings", page.get("findings", [])),
                "score": weak_page.get("score", page.get("score")),
            }
        )

    if results:
        return results

    fallback_url = site_result.get("url")
    if fallback_url and pages:
        page = pages[0]
        return [
            {
                "url": page.get("url", fallback_url),
                "title": page.get("title", ""),
                "html": page.get("html", ""),
                "excerpt": page.get("excerpt", page.get("body_excerpt", "")),
                "body_excerpt": page.get("body_excerpt", page.get("excerpt", "")),
                "service_description": "",
                "findings": page.get("findings", []),
                "score": page.get("score"),
            }
        ]

    return []
import re
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123 Safari/537.36"
}

CTA_KEYWORDS = [
    "お問い合わせ", "問合せ", "申込", "申し込み", "お申込み",
    "相談", "無料", "ダウンロード", "資料"
]

def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()

def analyze_url(url: str) -> dict:
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()

    soup = BeautifulSoup(r.text, "lxml")

    title = _clean(soup.title.get_text()) if soup.title else ""
    h1_list = [_clean(x.get_text(" ", strip=True)) for x in soup.find_all("h1")]
    h2_list = [_clean(x.get_text(" ", strip=True)) for x in soup.find_all("h2")]

    links = []
    for a in soup.find_all("a"):
        text = _clean(a.get_text(" ", strip=True))
        href = a.get("href", "")
        if text:
            links.append({"text": text, "href": href})

    ctas = []
    for link in links:
        if any(k in link["text"] for k in CTA_KEYWORDS):
            ctas.append(link["text"])

    unique_ctas = sorted(set(ctas))
    body_text = _clean(soup.get_text(" ", strip=True))

    has_faq = "よくある質問" in body_text
    has_case = "支援事例" in body_text or "導入事例" in body_text
    has_pdf = "PDF" in body_text or "ダウンロード" in body_text

    score = 100
    findings = []
    improvements = []

    if not title:
        score -= 15
        findings.append("titleなし")
    if not h1_list:
        score -= 20
        findings.append("h1なし")
    if h1_list and any("LP" == h1 or h1.endswith("LP") for h1 in h1_list):
        score -= 10
        improvements.append("H1を『マニュアル作成サービス』のような検索意図に合う表現へ変更")
    if len(unique_ctas) >= 3:
        score -= 8
        improvements.append("CTAが分散しているため主CVを1つに寄せる")
    if has_case:
        improvements.append("事例に定量成果を追加すると説得力が上がる")
    if has_faq:
        findings.append("FAQあり")
    if has_pdf:
        findings.append("PDF導線あり")

    return {
        "url": url,
        "title": title,
        "h1": h1_list,
        "h2_count": len(h2_list),
        "cta_count": len(ctas),
        "unique_ctas": unique_ctas,
        "has_faq": has_faq,
        "has_case": has_case,
        "has_pdf": has_pdf,
        "score": max(score, 0),
        "findings": findings,
        "improvements": improvements,
    }

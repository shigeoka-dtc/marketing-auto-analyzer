import re
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123 Safari/537.36"
}

CTA_KEYWORDS = [
    "お問い合わせ", "問合せ", "申込", "申し込み", "お申込み",
    "相談", "ダウンロード", "資料請求", "資料"
]

CTA_HREF_HINTS = [
    "contact", "inquiry", "form", "download", "pdf"
]

def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()

def _normalize_cta(text: str) -> str:
    text = _clean(text)
    text = text.replace("  ", " ")
    text = text.replace("を 申込む", "を申込む")
    text = text.replace("カウンセリング ", "カウンセリング")
    return text

def _is_cta(text: str, href: str) -> bool:
    href_l = (href or "").lower()

    exclude_texts = [
        "詳しくはこちら",
        "詳細はこちら",
    ]

    if text in exclude_texts:
        return False

    if "詳しくはこちら" in text:
        return False

    if text in ["請負", "常駐", "派遣"]:
        return False

    primary_keywords = [
        "お問い合わせ", "問合せ", "申込", "申し込み", "お申込み", "相談"
    ]
    secondary_keywords = [
        "ダウンロード", "資料請求", "資料"
    ]

    if any(k in text for k in primary_keywords + secondary_keywords):
        return len(text) <= 40

    if any(h in href_l for h in ["contact", "inquiry", "form", "download", "pdf"]):
        return len(text) <= 40

    return False
    
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
        text = _normalize_cta(link["text"])
        href = link["href"]

        if _is_cta(text, href):
            ctas.append(text)

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

    if h1_list and title and "マニュアル作成サービス" in title and "マニュアルLP" in h1_list:
        score -= 5
        improvements.append("TitleとH1の意味を揃える")

    if len(unique_ctas) >= 4:
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

import os
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

TARGET_URLS_FILE = os.getenv("TARGET_URLS_FILE", "data/raw/target_urls.txt")


def normalize_target_url(url: str) -> str:
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


def parse_target_urls(text: str) -> list[str]:
    urls = []
    seen = set()

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        normalized = normalize_target_url(line)
        if not normalized or normalized in seen:
            continue

        seen.add(normalized)
        urls.append(normalized)

    return urls


def target_urls_to_text(urls: list[str]) -> str:
    if not urls:
        return ""
    return "\n".join(urls) + "\n"


def load_target_urls() -> list[str]:
    path = Path(TARGET_URLS_FILE)
    if not path.exists():
        return []
    return parse_target_urls(path.read_text(encoding="utf-8"))


def target_urls_file_exists() -> bool:
    return Path(TARGET_URLS_FILE).exists()


def save_target_urls(urls: list[str]) -> str:
    path = Path(TARGET_URLS_FILE)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(target_urls_to_text(urls), encoding="utf-8")
    return str(path)

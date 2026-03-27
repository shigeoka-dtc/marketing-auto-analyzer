from pathlib import Path
from datetime import datetime

def save_report(title: str, body: str):
    Path("reports").mkdir(parents=True, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    path = Path("reports") / f"{ts}_{title}.md"
    path.write_text(body, encoding="utf-8")
    return str(path)
"""下载并清洗来源清单中的国家税务总局公开政策页面。"""

import hashlib
import json
import logging
import time
from datetime import UTC, datetime
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data" / "manifests" / "official_tax_sources.json"
RAW_DIR = ROOT / "data" / "raw" / "official"
PROCESSED_DIR = ROOT / "data" / "processed" / "official"
logger = logging.getLogger("taxmind.data.download")


def extract_text(html: str) -> str:
    """删除脚本与导航噪声，保留政策页可见正文。"""
    soup = BeautifulSoup(html, "html.parser")
    for node in soup(["script", "style", "noscript"]):
        node.decompose()
    lines = [line.strip() for line in soup.get_text("\n").splitlines() if line.strip()]
    return "\n".join(dict.fromkeys(lines))


def download_sources(client: httpx.Client, sources: list[dict], retries: int = 3) -> list[dict]:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    results = []
    for source in sources:
        error = None
        for attempt in range(retries):
            try:
                response = client.get(source["url"])
                response.raise_for_status()
                raw = response.content
                text = extract_text(response.text)
                (RAW_DIR / f"{source['id']}.html").write_bytes(raw)
                (PROCESSED_DIR / f"{source['id']}.md").write_text(
                    f"# {source['title']}\n\n{text}", encoding="utf-8"
                )
                results.append(
                    {
                        **source,
                        "sha256": hashlib.sha256(raw).hexdigest(),
                        "downloaded_at": datetime.now(UTC).isoformat(),
                    }
                )
                logger.info("官方政策下载成功 source_id=%s", source["id"])
                break
            except Exception as exc:  # 网络失败需要记录最后一次异常并继续其他来源。
                error = str(exc)
                time.sleep(min(2**attempt, 4))
        else:
            logger.error("官方政策下载失败 source_id=%s error=%s", source["id"], error)
            results.append({**source, "error": error})
    return results


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    sources = json.loads(MANIFEST.read_text(encoding="utf-8"))
    with httpx.Client(
        timeout=30,
        follow_redirects=True,
        headers={"User-Agent": "TaxMind/0.1 official-policy-import"},
    ) as client:
        results = download_sources(client, sources)
    (ROOT / "data" / "manifests" / "official_tax_downloads.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()

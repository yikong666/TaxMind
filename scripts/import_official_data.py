"""通过 TaxMind 正式 API 批量导入已下载的官方政策。"""

import json
import logging
import os
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
logger = logging.getLogger("taxmind.data.import")


def import_sources(
    client: httpx.Client, base_url: str, knowledge_base_id: int, sources: list[dict]
) -> None:
    detail = client.get(f"{base_url}/knowledge-bases/{knowledge_base_id}")
    detail.raise_for_status()
    existing_urls = {
        item.get("policy_metadata", {}).get("source_url")
        for item in detail.json()["data"].get("documents", [])
        if item.get("policy_metadata")
    }
    for source in sources:
        if source["url"] in existing_urls:
            logger.info("官方政策已存在，跳过 source_id=%s", source["id"])
            continue
        path = ROOT / "data" / "processed" / "official" / f"{source['id']}.md"
        if not path.exists():
            logger.warning("跳过未下载来源 source_id=%s", source["id"])
            continue
        with path.open("rb") as stream:
            uploaded = client.post(
                f"{base_url}/knowledge-bases/{knowledge_base_id}/documents",
                files={"files": (path.name, stream, "text/markdown")},
            )
        uploaded.raise_for_status()
        document_id = uploaded.json()["data"][0]["id"]
        client.post(f"{base_url}/documents/{document_id}/parse", json={}).raise_for_status()
        metadata = {
            key: source.get(key)
            for key in (
                "title",
                "doc_no",
                "region",
                "tax_type",
                "taxpayer_type",
                "publish_date",
                "effective_start",
                "effective_end",
                "policy_status",
                "url",
            )
        }
        metadata["policy_title"] = metadata.pop("title")
        metadata["source_url"] = metadata.pop("url")
        client.put(
            f"{base_url}/documents/{document_id}/policy-metadata", json=metadata
        ).raise_for_status()
        if source["policy_status"] == "active":
            client.post(f"{base_url}/documents/{document_id}/index", timeout=300).raise_for_status()
        logger.info("官方政策导入完成 source_id=%s document_id=%s", source["id"], document_id)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    token = os.environ.get("TAXMIND_ACCESS_TOKEN")
    knowledge_base_id = os.environ.get("TAXMIND_KNOWLEDGE_BASE_ID")
    if not token or not knowledge_base_id:
        raise SystemExit("请设置 TAXMIND_ACCESS_TOKEN 和 TAXMIND_KNOWLEDGE_BASE_ID")
    sources = json.loads(
        (ROOT / "data" / "manifests" / "official_tax_sources.json").read_text(encoding="utf-8")
    )
    with httpx.Client(headers={"Authorization": f"Bearer {token}"}, timeout=120) as client:
        import_sources(
            client,
            os.environ.get("TAXMIND_API_URL", "http://127.0.0.1:8000/api/v1"),
            int(knowledge_base_id),
            sources,
        )


if __name__ == "__main__":
    main()

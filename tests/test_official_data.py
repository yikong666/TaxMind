"""官方数据清洗与 50 条评测种子生成测试。"""

from scripts.build_evaluation_seed import build_records
from scripts.download_official_data import extract_text


def test_official_html_cleaning_removes_scripts_and_preserves_policy_lines() -> None:
    html = "<script>bad()</script><h1>政策标题</h1><p>正文</p><p>正文</p>"
    text = extract_text(html)
    assert "bad" not in text
    assert text.splitlines() == ["政策标题", "正文", "正文"]


def test_evaluation_seed_has_50_unique_complete_records() -> None:
    records = build_records()
    assert len(records) == 50
    assert len({item["id"] for item in records}) == 50
    assert len({item["id"].rsplit("-", 1)[0] for item in records}) == 25
    assert all(item["expected_region"] == "全国" for item in records)
    assert {item["expected_risk"] for item in records} >= {
        "LOW",
        "MEDIUM",
        "HIGH",
        "PROHIBITED",
    }

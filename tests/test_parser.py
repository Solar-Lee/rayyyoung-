"""解析層單元測試（不需連網）。"""
from __future__ import annotations

import json
from pathlib import Path

from scraper.parser import (
    extract_pk_from_url,
    parse_amount,
    parse_detail_html,
    parse_list_html,
    parse_roc_datetime,
)

FIXTURE = Path(__file__).parent / "fixtures" / "detail_sample.html"


def test_parse_roc_datetime():
    assert parse_roc_datetime("113/06/25") == "2024-06-25"
    assert parse_roc_datetime("113/07/15 17:00") == "2024-07-15 17:00"
    assert parse_roc_datetime("113年6月25日") == "2024-06-25"
    assert parse_roc_datetime("") == ""


def test_parse_amount():
    assert parse_amount("新臺幣 12,500,000 元") == 12500000
    assert parse_amount("1,000元") == 1000
    assert parse_amount("無") is None


def test_extract_pk_from_url():
    url = "https://web.pcc.gov.tw/tps/QueryTender/query/searchTenderDetail?pkPmsMain=ABC123"
    assert extract_pk_from_url(url) == "ABC123"


def test_parse_detail_html():
    html = FIXTURE.read_text(encoding="utf-8")
    url = "https://web.pcc.gov.tw/tps/QueryTender/query/searchTenderDetail?pkPmsMain=XYZ999"
    rec = parse_detail_html(html, detail_url=url, pcc_pk="XYZ999")

    assert rec["org_name"] == "臺北市政府資訊局"
    assert rec["job_number"] == "113-IT-0001"
    assert rec["title"] == "市政資訊系統雲端維運服務採購案"
    assert rec["tender_type"] == "公開招標"
    assert rec["award_type"] == "最有利標"
    assert rec["budget_amount"] == 12500000
    assert rec["publish_date"] == "2024-06-25"
    assert rec["deadline"] == "2024-07-15 17:00"
    assert rec["location"] == "臺北市"
    assert rec["pcc_pk"] == "XYZ999"

    attachments = json.loads(rec["attachments"])
    assert len(attachments) == 2
    assert attachments[0]["name"] == "招標文件.pdf"
    assert attachments[0]["url"].startswith("https://web.pcc.gov.tw/")


def test_parse_list_html():
    html = """
    <table><tr><td>
      <a href="/tps/QueryTender/query/searchTenderDetail?pkPmsMain=AAA">案件甲</a></td></tr>
      <tr><td><a href="/tps/QueryTender/query/searchTenderDetail?pkPmsMain=BBB">案件乙</a></td></tr>
      <tr><td><a href="/tps/QueryTender/query/searchTenderDetail?pkPmsMain=AAA">重複</a></td></tr>
    </table>
    """
    items = parse_list_html(html)
    assert len(items) == 2
    assert {i["pcc_pk"] for i in items} == {"AAA", "BBB"}

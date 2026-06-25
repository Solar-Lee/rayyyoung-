"""把政府電子採購網的 HTML 轉成結構化欄位（純函式，方便用 fixture 測試）。

PCC 詳情頁本質是一連串 <tr><th>欄位名</th><td>值</td></tr>。
策略：先把整頁壓成「欄位名 -> 值」的扁平 map，再用容錯的關鍵字對映到 schema。
不硬綁定特定 DOM 結構，未來頁面微調也不易壞。
"""
from __future__ import annotations

import json
import re
from typing import Optional
from urllib.parse import parse_qs, urljoin, urlparse

from bs4 import BeautifulSoup

# label 關鍵字（用「包含」比對，容錯）→ schema 欄位
_LABEL_MAP: list[tuple[str, list[str]]] = [
    ("org_name", ["機關名稱"]),
    ("org_address", ["機關地址"]),
    ("contact", ["聯絡人", "聯絡電話", "聯絡資訊"]),
    ("job_number", ["標案案號", "標案編號"]),
    ("title", ["標案名稱", "採購名稱"]),
    ("tender_type", ["招標方式"]),
    ("award_type", ["決標方式"]),
    ("procurement_nature", ["採購性質", "標的種類"]),
    ("category", ["標的分類", "財物採購性質", "工程採購性質", "勞務採購性質"]),
    ("budget_range", ["採購金額級距", "金額級距"]),
    ("budget_amount", ["預算金額"]),
    ("publish_date", ["公告日", "公開徵求公告日期", "招標公告日期"]),
    ("deadline", ["截止投標", "收件截止", "投標截止"]),
    ("open_date", ["開標時間"]),
    ("location", ["履約地點", "履約執行地點"]),
    ("multiple_award", ["是否複數決標"]),
]


def parse_roc_datetime(text: str) -> str:
    """民國日期 → 西元 'YYYY-MM-DD' 或 'YYYY-MM-DD HH:MM'。

    範例：'113/06/25 17:00' -> '2024-06-25 17:00'；'113年6月25日' -> '2024-06-25'。
    無法解析時回傳原字串去空白。
    """
    if not text:
        return ""
    t = text.strip()
    # 113/06/25 或 113-06-25，可帶時間
    m = re.search(r"(\d{2,3})[/\-年](\d{1,2})[/\-月](\d{1,2})", t)
    if not m:
        return t
    roc_y, mth, day = int(m.group(1)), int(m.group(2)), int(m.group(3))
    year = roc_y + 1911 if roc_y < 1911 else roc_y
    date = f"{year:04d}-{mth:02d}-{day:02d}"
    tm = re.search(r"(\d{1,2}):(\d{2})", t)
    if tm:
        return f"{date} {int(tm.group(1)):02d}:{tm.group(2)}"
    return date


def parse_amount(text: str) -> Optional[int]:
    """'新臺幣 1,234,567 元' -> 1234567。抓不到回傳 None。"""
    if not text:
        return None
    digits = re.sub(r"[^\d]", "", text.split("元")[0])
    return int(digits) if digits else None


def extract_pk_from_url(url: str) -> str:
    """從詳情頁 URL 取出穩定主鍵（primaryKey / pkPmsMain / 整段 query）。"""
    if not url:
        return ""
    qs = parse_qs(urlparse(url).query)
    for key in ("pkPmsMain", "primaryKey", "fn", "tenderCaseNo"):
        if key in qs and qs[key]:
            return qs[key][0]
    # 退而求其次：用整段 query 當識別
    return urlparse(url).query or url


def _flatten_labels(soup: BeautifulSoup) -> dict[str, str]:
    """把表格壓成 {欄位名: 值}。處理 th/td 與 td/td 兩種排版。"""
    pairs: dict[str, str] = {}
    for row in soup.find_all("tr"):
        cells = row.find_all(["th", "td"], recursive=False)
        if len(cells) < 2:
            continue
        # 以兩兩一組（標籤, 值）解析，支援一列多欄
        for i in range(0, len(cells) - 1, 2):
            label = cells[i].get_text(" ", strip=True)
            value = cells[i + 1].get_text(" ", strip=True)
            label = re.sub(r"\s+", "", label).rstrip("：:")
            if label and label not in pairs:
                pairs[label] = value
    return pairs


def _match_field(labels: dict[str, str], keywords: list[str]) -> str:
    for label, value in labels.items():
        for kw in keywords:
            if kw in label:
                return value
    return ""


def parse_detail_html(html: str, detail_url: str = "", pcc_pk: str = "") -> dict:
    """詳情頁 HTML → 結構化標案 dict。"""
    soup = BeautifulSoup(html, "lxml")
    labels = _flatten_labels(soup)

    record: dict = {}
    for field, keywords in _LABEL_MAP:
        record[field] = _match_field(labels, keywords)

    # 後處理
    record["budget_amount"] = parse_amount(record.get("budget_amount", ""))
    for date_field in ("publish_date", "deadline", "open_date"):
        record[date_field] = parse_roc_datetime(record.get(date_field, ""))

    # 附件
    attachments = []
    for a in soup.find_all("a", href=True):
        text = a.get_text(strip=True)
        href = a["href"]
        if any(ext in href.lower() for ext in (".pdf", ".doc", ".odt", ".zip", "download")):
            attachments.append({"name": text or href, "url": urljoin(detail_url, href)})
    record["attachments"] = json.dumps(attachments, ensure_ascii=False)

    record["detail_url"] = detail_url
    record["pcc_pk"] = pcc_pk or extract_pk_from_url(detail_url) or record.get("job_number", "")
    record["raw"] = json.dumps(labels, ensure_ascii=False)
    return record


def parse_list_html(html: str, base_url: str = "https://web.pcc.gov.tw") -> list[dict]:
    """招標查詢結果頁 → [{pcc_pk, detail_url, title, org_name, job_number, publish_date}]。

    盡力解析：抓含詳情連結的列。
    """
    soup = BeautifulSoup(html, "lxml")
    results: list[dict] = []
    seen: set[str] = set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "tenderDetail" not in href and "searchTenderDetail" not in href:
            continue
        detail_url = urljoin(base_url, href)
        pk = extract_pk_from_url(detail_url)
        if not pk or pk in seen:
            continue
        seen.add(pk)
        results.append(
            {
                "pcc_pk": pk,
                "detail_url": detail_url,
                "title": a.get_text(" ", strip=True),
            }
        )
    return results

"""用 Playwright 真實瀏覽器爬取政府電子採購網招標公告。

設計重點：
- 用真實 Chromium + 合理 User-Agent + 隨機延遲，禮貌爬取、降低被反爬蟲攔截機率。
- 導覽/取列表的邏輯放這裡；HTML→欄位的解析交給 scraper.parser（純函式、可單測）。
- 線上頁面的 DOM 結構偶有調整，必要時微調 _SEARCH_URL 與選擇器即可，解析層不受影響。

注意：實際 selector 需對線上頁面驗證。本模組以官方查詢端點與容錯解析為基礎，
若官方改版，請依 README「維護爬蟲」一節調整。
"""
from __future__ import annotations

import random
import time
from datetime import date

from app.config import (
    PCC_BASE,
    SCRAPE_MAX_DELAY,
    SCRAPE_MAX_DETAILS,
    SCRAPE_MIN_DELAY,
    USER_AGENT,
)
from scraper.parser import parse_detail_html, parse_list_html

# 招標公告進階查詢（可帶公告日期）
_SEARCH_URL = (
    PCC_BASE
    + "/prkms/tender/common/advanced/readTenderAdvanced"
)
_BASIC_SEARCH_URL = (
    PCC_BASE + "/prkms/tender/common/basic/indexTenderBasic"
)


def _polite_sleep() -> None:
    time.sleep(random.uniform(SCRAPE_MIN_DELAY, SCRAPE_MAX_DELAY))


def _roc(d: date) -> str:
    """西元 date → 民國 'YYY/MM/DD'（PCC 表單格式）。"""
    return f"{d.year - 1911:03d}/{d.month:02d}/{d.day:02d}"


def scrape_by_date(target_date: date, max_details: int | None = None,
                   headless: bool = True) -> list[dict]:
    """爬取指定公告日期的招標標案詳情，回傳結構化 dict 清單。"""
    from playwright.sync_api import sync_playwright  # 延遲匯入，避免無瀏覽器時 import 失敗

    max_details = SCRAPE_MAX_DETAILS if max_details is None else max_details
    roc_date = _roc(target_date)
    results: list[dict] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(
            user_agent=USER_AGENT,
            locale="zh-TW",
            viewport={"width": 1366, "height": 900},
        )
        page = context.new_page()

        # 1) 取得指定日期的招標公告列表（逐頁）
        listings = _collect_listings(page, roc_date)
        print(f"[scraper] {roc_date} 取得 {len(listings)} 筆列表項目")

        # 2) 逐筆抓詳情
        for i, item in enumerate(listings):
            if max_details and i >= max_details:
                break
            detail = _scrape_detail(page, item)
            if detail:
                results.append(detail)
            _polite_sleep()

        context.close()
        browser.close()

    return results


def _collect_listings(page, roc_date: str, max_pages: int = 30) -> list[dict]:
    """送出查詢並翻頁蒐集列表項目（pcc_pk + detail_url + title）。"""
    items: list[dict] = []
    seen: set[str] = set()

    # 直接以查詢字串請求進階查詢結果（公告日期區間 = 當日）
    url = (
        f"{_SEARCH_URL}?firstSearch=true&searchType=basic"
        f"&tenderStartDate={roc_date}&tenderEndDate={roc_date}"
    )
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=45000)
    except Exception as exc:  # noqa: BLE001
        print(f"[scraper] 查詢頁載入失敗，改用基本查詢頁：{exc}")
        page.goto(_BASIC_SEARCH_URL, wait_until="domcontentloaded", timeout=45000)

    for _ in range(max_pages):
        _polite_sleep()
        html = page.content()
        page_items = parse_list_html(html, base_url=PCC_BASE)
        new = [it for it in page_items if it["pcc_pk"] not in seen]
        for it in new:
            seen.add(it["pcc_pk"])
        items.extend(new)

        # 嘗試點「下一頁」
        if not _go_next_page(page):
            break

    return items


def _go_next_page(page) -> bool:
    """有下一頁就點擊並回 True，否則 False。容錯多種分頁樣式。"""
    for selector in [
        "a:has-text('下一頁')",
        "a[title='下一頁']",
        "a.next",
        "li.next a",
    ]:
        try:
            el = page.query_selector(selector)
            if el and el.is_enabled():
                el.click()
                page.wait_for_load_state("domcontentloaded", timeout=30000)
                return True
        except Exception:  # noqa: BLE001
            continue
    return False


def _scrape_detail(page, item: dict) -> dict | None:
    try:
        page.goto(item["detail_url"], wait_until="domcontentloaded", timeout=45000)
        html = page.content()
        record = parse_detail_html(html, detail_url=item["detail_url"], pcc_pk=item["pcc_pk"])
        # 列表標題作為 title 後援
        if not record.get("title"):
            record["title"] = item.get("title", "")
        return record
    except Exception as exc:  # noqa: BLE001
        print(f"[scraper] 抓取詳情失敗 {item.get('detail_url')}: {exc}")
        return None

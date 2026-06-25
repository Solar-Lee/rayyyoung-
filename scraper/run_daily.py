"""每日爬取入口：抓指定日期招標公告 → 寫 data/raw/YYYYMMDD.json → 匯入 SQLite。

用法：
    python -m scraper.run_daily                 # 抓今日
    python -m scraper.run_daily --date 2026-06-25
    python -m scraper.run_daily --days 2        # 抓今日往前 2 天
    python -m scraper.run_daily --no-headless   # 顯示瀏覽器（除錯）
"""
from __future__ import annotations

import argparse
import json
from datetime import date, datetime, timedelta
from pathlib import Path

from app.config import RAW_DIR
from app.ingest import ingest_all


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="每日爬取政府電子採購網招標公告")
    parser.add_argument("--date", help="指定公告日期 YYYY-MM-DD（預設今日）")
    parser.add_argument("--days", type=int, default=1, help="從指定日期往前共抓幾天（預設 1）")
    parser.add_argument("--max-details", type=int, default=None, help="單日詳情頁上限（除錯用）")
    parser.add_argument("--no-headless", action="store_true", help="顯示瀏覽器視窗")
    return parser.parse_args()


def _target_dates(args: argparse.Namespace) -> list[date]:
    base = (
        datetime.strptime(args.date, "%Y-%m-%d").date() if args.date else date.today()
    )
    return [base - timedelta(days=i) for i in range(max(1, args.days))]


def scrape_and_save(target: date, max_details, headless) -> int:
    # 延遲匯入，避免無 Playwright 環境時 import 失敗
    from scraper.pcc_scraper import scrape_by_date

    records = scrape_by_date(target, max_details=max_details, headless=headless)
    out_path = Path(RAW_DIR) / f"{target.strftime('%Y%m%d')}.json"

    # 與既有檔案合併去重（冪等，可重跑）
    existing: dict[str, dict] = {}
    if out_path.exists():
        prev = json.loads(out_path.read_text(encoding="utf-8"))
        for r in prev.get("tenders", []):
            if r.get("pcc_pk"):
                existing[r["pcc_pk"]] = r
    for r in records:
        if r.get("pcc_pk"):
            existing[r["pcc_pk"]] = r

    payload = {
        "scraped_date": target.isoformat(),
        "scraped_at": datetime.now().isoformat(timespec="seconds"),
        "count": len(existing),
        "tenders": list(existing.values()),
    }
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[run_daily] {target} 寫入 {out_path}（{len(existing)} 筆）")
    return len(records)


def main() -> None:
    args = _parse_args()
    total = 0
    for target in _target_dates(args):
        try:
            total += scrape_and_save(target, args.max_details, not args.no_headless)
        except Exception as exc:  # noqa: BLE001
            print(f"[run_daily] {target} 爬取失敗：{exc}")

    # 匯入資料庫
    n = ingest_all()
    print(f"[run_daily] 完成。本次新抓 {total} 筆；資料庫已同步 {n} 筆。")


if __name__ == "__main__":
    main()

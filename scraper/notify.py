"""關鍵字訂閱 Email 通知。

比對「今日（或指定日期）爬取到的新標案」與 config/subscriptions.yml 的關鍵字，
命中者彙整成 HTML 摘要寄出。支援 --dry-run（只印不寄）。

用法：
    python -m scraper.notify                  # 比對今日資料並寄信
    python -m scraper.notify --date 2026-06-25
    python -m scraper.notify --dry-run
"""
from __future__ import annotations

import argparse
import json
import smtplib
from datetime import date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from app.config import (
    NOTIFY_FROM,
    PCC_BASE,
    RAW_DIR,
    SMTP_HOST,
    SMTP_PASS,
    SMTP_PORT,
    SMTP_USER,
)
from app.subs_store import load_subscriptions


def load_day_tenders(target: date) -> list[dict]:
    path = Path(RAW_DIR) / f"{target.strftime('%Y%m%d')}.json"
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("tenders", [])


def match(tenders: list[dict], keywords: list[str]) -> list[dict]:
    hits = []
    for t in tenders:
        haystack = f"{t.get('title','')} {t.get('org_name','')} {t.get('category','')}"
        if any(kw and kw in haystack for kw in keywords):
            hits.append(t)
    return hits


def build_email_html(hits: list[dict], keywords: list[str], target: date) -> str:
    rows = ""
    for t in hits:
        url = t.get("detail_url") or PCC_BASE
        budget = t.get("budget_amount")
        budget_str = f"{int(budget):,} 元" if budget else "—"
        rows += (
            f"<tr>"
            f"<td style='padding:6px;border-bottom:1px solid #eee'>{t.get('org_name','—')}</td>"
            f"<td style='padding:6px;border-bottom:1px solid #eee'>"
            f"<a href='{url}'>{t.get('title','—')}</a></td>"
            f"<td style='padding:6px;border-bottom:1px solid #eee'>{budget_str}</td>"
            f"<td style='padding:6px;border-bottom:1px solid #eee'>{t.get('deadline','—')}</td>"
            f"</tr>"
        )
    return (
        f"<h2>政府標案每日通知 — {target.isoformat()}</h2>"
        f"<p>命中關鍵字：{'、'.join(keywords)}，共 <b>{len(hits)}</b> 筆符合的新標案。</p>"
        f"<table style='border-collapse:collapse;width:100%;font-size:14px'>"
        f"<tr style='background:#0f172a;color:#fff'>"
        f"<th style='padding:6px;text-align:left'>機關</th>"
        f"<th style='padding:6px;text-align:left'>標案名稱</th>"
        f"<th style='padding:6px;text-align:left'>預算</th>"
        f"<th style='padding:6px;text-align:left'>截止投標</th></tr>"
        f"{rows}</table>"
        f"<p style='color:#888;font-size:12px'>資料來源：政府電子採購網。本信由標案平台自動發送。</p>"
    )


def send_email(to: str, subject: str, html: str) -> None:
    if not (SMTP_HOST and SMTP_USER and SMTP_PASS):
        raise RuntimeError("SMTP 未設定（SMTP_HOST/SMTP_USER/SMTP_PASS）。")
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = NOTIFY_FROM or SMTP_USER
    msg["To"] = to
    msg.attach(MIMEText(html, "html", "utf-8"))
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.sendmail(msg["From"], [to], msg.as_string())


def run(target: date, dry_run: bool) -> int:
    tenders = load_day_tenders(target)
    if not tenders:
        print(f"[notify] {target} 無當日標案資料，略過。")
        return 0

    subs = load_subscriptions()
    sent = 0
    for sub in subs:
        if not sub.get("active", True):
            continue
        hits = match(tenders, sub["keywords"])
        if not hits:
            print(f"[notify] {sub['email']} 無命中，略過。")
            continue
        html = build_email_html(hits, sub["keywords"], target)
        subject = f"【政府標案】{target.isoformat()} 有 {len(hits)} 筆符合您的關鍵字"
        if dry_run:
            print(f"[notify][dry-run] → {sub['email']}：{len(hits)} 筆命中")
            print(html[:400] + " ...")
        else:
            try:
                send_email(sub["email"], subject, html)
                print(f"[notify] 已寄送 → {sub['email']}（{len(hits)} 筆）")
                sent += 1
            except Exception as exc:  # noqa: BLE001
                print(f"[notify] 寄送失敗 → {sub['email']}：{exc}")
    return sent


def main() -> None:
    parser = argparse.ArgumentParser(description="關鍵字訂閱 Email 通知")
    parser.add_argument("--date", help="指定日期 YYYY-MM-DD（預設今日）")
    parser.add_argument("--dry-run", action="store_true", help="只印不寄")
    args = parser.parse_args()
    target = (
        date.fromisoformat(args.date) if args.date else date.today()
    )
    run(target, args.dry_run)


if __name__ == "__main__":
    main()

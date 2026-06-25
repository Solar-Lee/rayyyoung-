"""依目前篩選條件匯出標案為 CSV / Excel。"""
from __future__ import annotations

import csv
import io
from datetime import date

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from openpyxl import Workbook
from sqlmodel import Session

from app.database import get_session
from app.queries import TenderFilter, all_matching
from app.routers.tenders import filter_from_query

router = APIRouter(tags=["export"])

# (欄位, 中文標題)
COLUMNS = [
    ("publish_date", "公告日期"),
    ("deadline", "截止投標"),
    ("org_name", "機關名稱"),
    ("job_number", "標案案號"),
    ("title", "標案名稱"),
    ("tender_type", "招標方式"),
    ("award_type", "決標方式"),
    ("category", "標的分類"),
    ("budget_amount", "預算金額"),
    ("location", "履約地點"),
    ("detail_url", "詳情連結"),
]


def _rows(session: Session, f: TenderFilter):
    for t in all_matching(session, f):
        yield [getattr(t, col, "") if getattr(t, col, "") is not None else "" for col, _ in COLUMNS]


@router.get("/export.csv")
def export_csv(
    f: TenderFilter = Depends(filter_from_query),
    session: Session = Depends(get_session),
):
    buf = io.StringIO()
    buf.write("﻿")  # BOM，Excel 開啟中文不亂碼
    writer = csv.writer(buf)
    writer.writerow([title for _, title in COLUMNS])
    for row in _rows(session, f):
        writer.writerow(row)
    buf.seek(0)
    fname = f"tenders_{date.today().isoformat()}.csv"
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )


@router.get("/export.xlsx")
def export_xlsx(
    f: TenderFilter = Depends(filter_from_query),
    session: Session = Depends(get_session),
):
    wb = Workbook()
    ws = wb.active
    ws.title = "標案"
    ws.append([title for _, title in COLUMNS])
    for row in _rows(session, f):
        ws.append(row)
    stream = io.BytesIO()
    wb.save(stream)
    stream.seek(0)
    fname = f"tenders_{date.today().isoformat()}.xlsx"
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )

"""HTML 頁面：儀表板、搜尋列表、標案詳情、追蹤清單、訂閱管理。"""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlmodel import Session, func, select

from app import subs_store
from app.database import get_session
from app.models import WATCHLIST_STATUSES, Tender, Watchlist
from app.queries import TenderFilter, distinct_values, search_tenders
from app.routers.tenders import filter_from_query
from app.templating import templates

router = APIRouter(include_in_schema=False)


@router.get("/", response_class=HTMLResponse)
def dashboard(request: Request, session: Session = Depends(get_session)):
    today = date.today().isoformat()
    soon = (date.today() + timedelta(days=3)).isoformat()

    total = session.exec(select(func.count(Tender.id))).one()
    today_count = session.exec(
        select(func.count(Tender.id)).where(Tender.publish_date == today)
    ).one()
    closing_soon = session.exec(
        select(Tender)
        .where(Tender.deadline >= today, Tender.deadline <= soon + " 23:59")
        .order_by(Tender.deadline.asc())
        .limit(10)
    ).all()
    watch_count = session.exec(select(func.count(Watchlist.id))).one()

    latest = session.exec(
        select(Tender).order_by(Tender.publish_date.desc(), Tender.id.desc()).limit(15)
    ).all()

    # 依機關統計 Top
    org_rows = session.exec(
        select(Tender.org_name, func.count(Tender.id).label("c"))
        .group_by(Tender.org_name)
        .order_by(func.count(Tender.id).desc())
        .limit(8)
    ).all()
    top_orgs = [(name or "（未填）", c) for name, c in org_rows]

    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "active": "dashboard",
            "total": total,
            "today_count": today_count,
            "watch_count": watch_count,
            "closing_soon": closing_soon,
            "latest": latest,
            "top_orgs": top_orgs,
        },
    )


@router.get("/tenders", response_class=HTMLResponse)
def tenders_page(
    request: Request,
    f: TenderFilter = Depends(filter_from_query),
    session: Session = Depends(get_session),
):
    f.page_size = min(f.page_size, 50)
    rows, total = search_tenders(session, f)
    pages = max(1, (total + f.page_size - 1) // f.page_size)

    categories = distinct_values(session, Tender.category)
    tender_types = distinct_values(session, Tender.tender_type)
    query_params = {k: v for k, v in request.query_params.items() if k != "page"}
    export_qs = request.url.query

    return templates.TemplateResponse(
        request,
        "tenders.html",
        {
            "active": "tenders",
            "rows": rows,
            "total": total,
            "filter": f,
            "pages": pages,
            "categories": categories,
            "tender_types": tender_types,
            "query_params": query_params,
            "export_qs": export_qs,
        },
    )


@router.get("/tender/{pcc_pk:path}", response_class=HTMLResponse)
def tender_detail(
    request: Request, pcc_pk: str, session: Session = Depends(get_session)
):
    tender = session.exec(select(Tender).where(Tender.pcc_pk == pcc_pk)).first()
    if not tender:
        return templates.TemplateResponse(
            request, "not_found.html", {"active": "tenders"}, status_code=404
        )
    watch = session.exec(
        select(Watchlist).where(Watchlist.tender_pk == pcc_pk)
    ).first()
    try:
        attachments = json.loads(tender.attachments) if tender.attachments else []
    except json.JSONDecodeError:
        attachments = []
    return templates.TemplateResponse(
        request,
        "detail.html",
        {
            "active": "tenders",
            "t": tender,
            "watch": watch,
            "attachments": attachments,
            "statuses": WATCHLIST_STATUSES,
        },
    )


@router.get("/watchlist", response_class=HTMLResponse)
def watchlist_page(request: Request, session: Session = Depends(get_session)):
    items = session.exec(select(Watchlist).order_by(Watchlist.updated_at.desc())).all()
    # 串接對應標案
    enriched = []
    for item in items:
        tender = session.exec(
            select(Tender).where(Tender.pcc_pk == item.tender_pk)
        ).first()
        enriched.append({"item": item, "tender": tender})

    columns = {s: [e for e in enriched if e["item"].status == s] for s in WATCHLIST_STATUSES}
    return templates.TemplateResponse(
        request,
        "watchlist.html",
        {
            "active": "watchlist",
            "columns": columns,
            "statuses": WATCHLIST_STATUSES,
            "total": len(enriched),
        },
    )


@router.get("/subscriptions", response_class=HTMLResponse)
def subscriptions_page(request: Request):
    subs = subs_store.load_subscriptions()
    return templates.TemplateResponse(
        request,
        "subscriptions.html",
        {"active": "subscriptions", "subs": subs},
    )

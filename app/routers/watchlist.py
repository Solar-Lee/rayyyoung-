"""投標追蹤清單 CRUD。"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Form, HTTPException
from fastapi.responses import RedirectResponse
from sqlmodel import Session, select

from app.database import get_session
from app.models import WATCHLIST_STATUSES, Watchlist

router = APIRouter(tags=["watchlist"])


@router.post("/watchlist/add")
def add_to_watchlist(
    tender_pk: str = Form(...),
    status: str = Form("評估中"),
    note: str = Form(""),
    redirect: str = Form("/watchlist"),
    session: Session = Depends(get_session),
):
    if status not in WATCHLIST_STATUSES:
        status = "評估中"
    existing = session.exec(select(Watchlist).where(Watchlist.tender_pk == tender_pk)).first()
    if existing:
        existing.status = status
        if note:
            existing.note = note
        existing.updated_at = datetime.now(timezone.utc)
        session.add(existing)
    else:
        session.add(Watchlist(tender_pk=tender_pk, status=status, note=note))
    session.commit()
    return RedirectResponse(redirect, status_code=303)


@router.post("/watchlist/{item_id}/update")
def update_watchlist(
    item_id: int,
    status: str = Form(...),
    note: str = Form(""),
    session: Session = Depends(get_session),
):
    item = session.get(Watchlist, item_id)
    if not item:
        raise HTTPException(404, "找不到追蹤項目")
    if status in WATCHLIST_STATUSES:
        item.status = status
    item.note = note
    item.updated_at = datetime.now(timezone.utc)
    session.add(item)
    session.commit()
    return RedirectResponse("/watchlist", status_code=303)


@router.post("/watchlist/{item_id}/remove")
def remove_watchlist(item_id: int, session: Session = Depends(get_session)):
    item = session.get(Watchlist, item_id)
    if item:
        session.delete(item)
        session.commit()
    return RedirectResponse("/watchlist", status_code=303)

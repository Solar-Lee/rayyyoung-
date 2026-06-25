"""關鍵字訂閱管理（讀寫 config/subscriptions.yml）。"""
from __future__ import annotations

from fastapi import APIRouter, Form
from fastapi.responses import RedirectResponse

from app import subs_store

router = APIRouter(tags=["subscriptions"])


@router.post("/subscriptions/add")
def add(email: str = Form(...), keywords: str = Form(...)):
    kw_list = [k.strip() for k in keywords.replace("，", ",").split(",") if k.strip()]
    subs_store.add_subscription(email, kw_list)
    return RedirectResponse("/subscriptions", status_code=303)


@router.post("/subscriptions/remove")
def remove(email: str = Form(...), keyword: str = Form(...)):
    subs_store.remove_keyword(email, keyword)
    return RedirectResponse("/subscriptions", status_code=303)


@router.get("/api/subscriptions")
def list_subscriptions():
    return {"subscriptions": subs_store.load_subscriptions()}

"""標案 JSON API：搜尋/篩選/詳情。"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from app.database import get_session
from app.models import Tender
from app.queries import TenderFilter, search_tenders

router = APIRouter(prefix="/api", tags=["tenders"])


def filter_from_query(
    q: Optional[str] = None,
    org: Optional[str] = None,
    category: Optional[str] = None,
    tender_type: Optional[str] = None,
    budget_min: Optional[int] = None,
    budget_max: Optional[int] = None,
    publish_from: Optional[str] = None,
    publish_to: Optional[str] = None,
    deadline_from: Optional[str] = None,
    deadline_to: Optional[str] = None,
    sort: str = "publish_date",
    desc: bool = True,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
) -> TenderFilter:
    return TenderFilter(
        q=q, org=org, category=category, tender_type=tender_type,
        budget_min=budget_min, budget_max=budget_max,
        publish_from=publish_from, publish_to=publish_to,
        deadline_from=deadline_from, deadline_to=deadline_to,
        sort=sort, desc=desc, page=page, page_size=page_size,
    )


@router.get("/tenders")
def list_tenders(
    f: TenderFilter = Depends(filter_from_query),
    session: Session = Depends(get_session),
):
    rows, total = search_tenders(session, f)
    return {
        "total": total,
        "page": f.page,
        "page_size": f.page_size,
        "items": [r.model_dump() for r in rows],
    }


@router.get("/tenders/{pcc_pk:path}")
def get_tender(pcc_pk: str, session: Session = Depends(get_session)):
    tender = session.exec(select(Tender).where(Tender.pcc_pk == pcc_pk)).first()
    if not tender:
        raise HTTPException(status_code=404, detail="找不到該標案")
    return tender.model_dump()

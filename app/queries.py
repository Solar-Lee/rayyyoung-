"""標案搜尋/篩選的共用查詢邏輯，供 API、頁面、匯出共用。"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from sqlmodel import Session, func, or_, select

from app.models import Tender

SORT_FIELDS = {
    "publish_date": Tender.publish_date,
    "deadline": Tender.deadline,
    "budget_amount": Tender.budget_amount,
    "scraped_at": Tender.scraped_at,
}


@dataclass
class TenderFilter:
    q: Optional[str] = None  # 關鍵字（標案名稱/機關/案號）
    org: Optional[str] = None
    category: Optional[str] = None
    tender_type: Optional[str] = None
    budget_min: Optional[int] = None
    budget_max: Optional[int] = None
    publish_from: Optional[str] = None
    publish_to: Optional[str] = None
    deadline_from: Optional[str] = None
    deadline_to: Optional[str] = None
    sort: str = "publish_date"
    desc: bool = True
    page: int = 1
    page_size: int = 20


def _apply(statement, f: TenderFilter):
    if f.q:
        like = f"%{f.q}%"
        statement = statement.where(
            or_(
                Tender.title.like(like),
                Tender.org_name.like(like),
                Tender.job_number.like(like),
            )
        )
    if f.org:
        statement = statement.where(Tender.org_name.like(f"%{f.org}%"))
    if f.category:
        statement = statement.where(Tender.category.like(f"%{f.category}%"))
    if f.tender_type:
        statement = statement.where(Tender.tender_type.like(f"%{f.tender_type}%"))
    if f.budget_min is not None:
        statement = statement.where(Tender.budget_amount >= f.budget_min)
    if f.budget_max is not None:
        statement = statement.where(Tender.budget_amount <= f.budget_max)
    if f.publish_from:
        statement = statement.where(Tender.publish_date >= f.publish_from)
    if f.publish_to:
        statement = statement.where(Tender.publish_date <= f.publish_to)
    if f.deadline_from:
        statement = statement.where(Tender.deadline >= f.deadline_from)
    if f.deadline_to:
        statement = statement.where(Tender.deadline <= f.deadline_to)
    return statement


def search_tenders(session: Session, f: TenderFilter) -> tuple[list[Tender], int]:
    """回傳 (該頁標案, 符合總數)。"""
    base = _apply(select(Tender), f)

    count_stmt = _apply(select(func.count(Tender.id)), f)
    total = session.exec(count_stmt).one()

    sort_col = SORT_FIELDS.get(f.sort, Tender.publish_date)
    base = base.order_by(sort_col.desc() if f.desc else sort_col.asc())

    page = max(1, f.page)
    page_size = max(1, min(200, f.page_size))
    base = base.offset((page - 1) * page_size).limit(page_size)

    rows = session.exec(base).all()
    return rows, total


def all_matching(session: Session, f: TenderFilter, cap: int = 5000) -> list[Tender]:
    """取出所有符合條件（不分頁，供匯出用），上限保護。"""
    base = _apply(select(Tender), f)
    sort_col = SORT_FIELDS.get(f.sort, Tender.publish_date)
    base = base.order_by(sort_col.desc() if f.desc else sort_col.asc()).limit(cap)
    return session.exec(base).all()


def distinct_values(session: Session, column) -> list[str]:
    rows = session.exec(select(column).distinct()).all()
    return sorted({r for r in rows if r})

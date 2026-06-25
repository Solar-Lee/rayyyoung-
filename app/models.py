"""SQLModel 資料表定義。"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Tender(SQLModel, table=True):
    """單一招標標案。以 PCC 主鍵 pcc_pk 去重。"""

    id: Optional[int] = Field(default=None, primary_key=True)
    pcc_pk: str = Field(index=True, unique=True, description="PCC 詳情頁主鍵 / 唯一識別")

    org_name: str = Field(default="", index=True, description="機關名稱")
    org_address: str = Field(default="", description="機關地址")
    contact: str = Field(default="", description="聯絡人/電話")

    job_number: str = Field(default="", index=True, description="標案案號")
    title: str = Field(default="", index=True, description="標案名稱")
    tender_type: str = Field(default="", index=True, description="招標方式")
    award_type: str = Field(default="", description="決標方式")
    procurement_nature: str = Field(default="", index=True, description="採購性質")
    category: str = Field(default="", index=True, description="採購類別/標的分類")
    budget_range: str = Field(default="", description="採購金額級距")
    budget_amount: Optional[int] = Field(default=None, index=True, description="預算金額（元）")

    publish_date: str = Field(default="", index=True, description="公告日期 YYYY-MM-DD")
    deadline: str = Field(default="", index=True, description="截止投標 YYYY-MM-DD HH:MM")
    open_date: str = Field(default="", description="開標時間 YYYY-MM-DD HH:MM")
    location: str = Field(default="", description="履約地點")
    multiple_award: str = Field(default="", description="是否複數決標")

    attachments: str = Field(default="", description="附件清單（JSON 字串）")
    detail_url: str = Field(default="", description="官方詳情頁連結")
    raw: str = Field(default="", description="原始抓取欄位（JSON 字串）")

    scraped_at: datetime = Field(default_factory=_utcnow)


class Subscription(SQLModel, table=True):
    """關鍵字訂閱（亦同步至 config/subscriptions.yml）。"""

    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(index=True)
    keyword: str = Field(index=True)
    active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=_utcnow)


class Watchlist(SQLModel, table=True):
    """投標追蹤清單。"""

    id: Optional[int] = Field(default=None, primary_key=True)
    tender_pk: str = Field(index=True, description="對應 Tender.pcc_pk")
    status: str = Field(default="評估中", index=True, description="評估中/準備投標/已投標/不投標")
    note: str = Field(default="")
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)


WATCHLIST_STATUSES = ["評估中", "準備投標", "已投標", "不投標"]

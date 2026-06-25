"""把 data/raw/*.json 冪等 upsert 進 SQLite。

App 啟動時與每日爬取後皆會呼叫。以 Tender.pcc_pk 去重。
"""
from __future__ import annotations

import json
from pathlib import Path

from sqlmodel import Session, select

from app.config import RAW_DIR
from app.database import engine, init_db
from app.models import Tender

_TENDER_FIELDS = set(Tender.model_fields.keys())


def _clean(record: dict) -> dict:
    """只保留 Tender 已知欄位，去掉多餘 key。"""
    return {k: v for k, v in record.items() if k in _TENDER_FIELDS and k != "id"}


def upsert_records(session: Session, records: list[dict]) -> int:
    """upsert 一批標案，回傳新增/更新筆數。"""
    count = 0
    for raw in records:
        record = _clean(raw)
        pk = record.get("pcc_pk")
        if not pk:
            continue
        existing = session.exec(select(Tender).where(Tender.pcc_pk == pk)).first()
        if existing:
            for key, value in record.items():
                if key == "pcc_pk":
                    continue
                # 不用空值覆蓋既有資料
                if value in (None, "") and getattr(existing, key, None):
                    continue
                setattr(existing, key, value)
            session.add(existing)
        else:
            session.add(Tender(**record))
        count += 1
    session.commit()
    return count


def ingest_file(path: Path) -> int:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    records = data.get("tenders", data) if isinstance(data, dict) else data
    with Session(engine) as session:
        return upsert_records(session, records)


def ingest_all(raw_dir: Path | None = None) -> int:
    """匯入所有 data/raw/*.json。回傳總處理筆數。"""
    init_db()
    raw_dir = raw_dir or RAW_DIR
    total = 0
    for path in sorted(Path(raw_dir).glob("*.json")):
        total += ingest_file(path)
    return total


if __name__ == "__main__":
    n = ingest_all()
    print(f"已匯入 {n} 筆標案至資料庫。")

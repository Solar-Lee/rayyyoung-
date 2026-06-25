"""FastAPI 端點測試（用暫存 DB + 假資料，不連網）。"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.database import engine, init_db
from app.main import app
from app.models import Tender


@pytest.fixture(scope="module", autouse=True)
def seed_db():
    init_db()
    with Session(engine) as s:
        s.add_all(
            [
                Tender(
                    pcc_pk="T1", org_name="臺北市政府", title="資訊系統維運案",
                    job_number="A-1", tender_type="公開招標", category="勞務",
                    budget_amount=5_000_000, publish_date="2026-06-25",
                    deadline="2026-07-10 17:00", detail_url="https://web.pcc.gov.tw/x?pkPmsMain=T1",
                ),
                Tender(
                    pcc_pk="T2", org_name="高雄市政府", title="道路工程改善案",
                    job_number="B-2", tender_type="限制性招標", category="工程",
                    budget_amount=20_000_000, publish_date="2026-06-24",
                    deadline="2026-07-05 17:00",
                ),
            ]
        )
        s.commit()
    yield


# 不用 with，避免觸發 lifespan 重新 ingest data/raw
client = TestClient(app)


def test_health():
    assert client.get("/healthz").json()["status"] == "ok"


def test_list_tenders_all():
    data = client.get("/api/tenders").json()
    assert data["total"] == 2


def test_search_keyword():
    data = client.get("/api/tenders", params={"q": "資訊"}).json()
    assert data["total"] == 1
    assert data["items"][0]["pcc_pk"] == "T1"


def test_filter_budget():
    data = client.get("/api/tenders", params={"budget_min": 10_000_000}).json()
    assert data["total"] == 1
    assert data["items"][0]["pcc_pk"] == "T2"


def test_get_tender_detail_api():
    assert client.get("/api/tenders/T1").json()["title"] == "資訊系統維運案"
    assert client.get("/api/tenders/NOPE").status_code == 404


def test_pages_render():
    assert client.get("/").status_code == 200
    assert client.get("/tenders").status_code == 200
    assert client.get("/tender/T1").status_code == 200
    assert client.get("/watchlist").status_code == 200
    assert client.get("/subscriptions").status_code == 200


def test_watchlist_flow():
    r = client.post(
        "/watchlist/add",
        data={"tender_pk": "T1", "status": "準備投標", "note": "重點案"},
        follow_redirects=False,
    )
    assert r.status_code == 303
    page = client.get("/watchlist")
    assert "重點案" in page.text


def test_export_csv():
    r = client.get("/export.csv")
    assert r.status_code == 200
    assert "標案名稱" in r.text
    assert "資訊系統維運案" in r.text


def test_export_xlsx():
    r = client.get("/export.xlsx")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith(
        "application/vnd.openxmlformats"
    )

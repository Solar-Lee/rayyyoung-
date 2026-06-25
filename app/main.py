"""FastAPI 應用程式進入點。"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config import ROOT_DIR
from app.database import init_db
from app.ingest import ingest_all
from app.routers import export, pages, subscriptions, tenders, watchlist

STATIC_DIR = ROOT_DIR / "app" / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 啟動：建表 + 把 data/raw/*.json 匯入 SQLite
    init_db()
    try:
        n = ingest_all()
        print(f"[startup] 已匯入/更新 {n} 筆標案")
    except Exception as exc:  # 匯入失敗不阻擋啟動
        print(f"[startup] 匯入資料時發生問題：{exc}")
    yield


app = FastAPI(title="台灣政府標案投標工具平台", version="0.1.0", lifespan=lifespan)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

app.include_router(pages.router)
app.include_router(tenders.router)
app.include_router(watchlist.router)
app.include_router(subscriptions.router)
app.include_router(export.router)


@app.get("/healthz", include_in_schema=False)
def healthz():
    return {"status": "ok"}

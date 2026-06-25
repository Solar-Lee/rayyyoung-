"""集中式設定。從環境變數 / .env 讀取，提供合理預設值。"""
from __future__ import annotations

import os
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # python-dotenv 未安裝時不致命
    pass

# 專案根目錄（此檔位於 app/config.py）
ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
CONFIG_DIR = ROOT_DIR / "config"
SUBSCRIPTIONS_FILE = CONFIG_DIR / "subscriptions.yml"

DATA_DIR.mkdir(exist_ok=True)
RAW_DIR.mkdir(parents=True, exist_ok=True)

DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DATA_DIR / 'app.db'}")

# SMTP（Email 通知）
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
NOTIFY_FROM = os.getenv("NOTIFY_FROM", "") or SMTP_USER

# 爬蟲禮貌設定
SCRAPE_MIN_DELAY = float(os.getenv("SCRAPE_MIN_DELAY", "1.5"))
SCRAPE_MAX_DELAY = float(os.getenv("SCRAPE_MAX_DELAY", "3.5"))
SCRAPE_MAX_DETAILS = int(os.getenv("SCRAPE_MAX_DETAILS", "0"))

# 官方政府電子採購網
PCC_BASE = "https://web.pcc.gov.tw"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)

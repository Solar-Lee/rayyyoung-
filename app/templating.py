"""共用 Jinja2 模板環境與過濾器。"""
from __future__ import annotations

from pathlib import Path

from fastapi.templating import Jinja2Templates

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def money(value) -> str:
    """1234567 -> '1,234,567'。"""
    if value in (None, ""):
        return "—"
    try:
        return f"{int(value):,}"
    except (TypeError, ValueError):
        return str(value)


def default_dash(value) -> str:
    return value if value not in (None, "") else "—"


templates.env.filters["money"] = money
templates.env.filters["dash"] = default_dash

"""讀寫 config/subscriptions.yml 的小工具，供平台訂閱管理頁與 notify 共用。

檔案格式：
    subscriptions:
      - email: a@b.com
        keywords: [資訊, 軟體]
        active: true
"""
from __future__ import annotations

from pathlib import Path

import yaml

from app.config import SUBSCRIPTIONS_FILE


def load_subscriptions(path: Path | None = None) -> list[dict]:
    path = path or SUBSCRIPTIONS_FILE
    if not Path(path).exists():
        return []
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    subs = data.get("subscriptions", []) or []
    # 正規化
    out = []
    for s in subs:
        out.append(
            {
                "email": (s.get("email") or "").strip(),
                "keywords": [k.strip() for k in (s.get("keywords") or []) if str(k).strip()],
                "active": bool(s.get("active", True)),
            }
        )
    return [s for s in out if s["email"]]


def save_subscriptions(subs: list[dict], path: Path | None = None) -> None:
    path = path or SUBSCRIPTIONS_FILE
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    payload = {"subscriptions": subs}
    Path(path).write_text(
        yaml.safe_dump(payload, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def add_subscription(email: str, keywords: list[str], path: Path | None = None) -> list[dict]:
    subs = load_subscriptions(path)
    email = email.strip()
    keywords = [k.strip() for k in keywords if k.strip()]
    for s in subs:
        if s["email"] == email:
            # 合併關鍵字
            s["keywords"] = sorted(set(s["keywords"]) | set(keywords))
            s["active"] = True
            save_subscriptions(subs, path)
            return subs
    subs.append({"email": email, "keywords": keywords, "active": True})
    save_subscriptions(subs, path)
    return subs


def remove_keyword(email: str, keyword: str, path: Path | None = None) -> list[dict]:
    subs = load_subscriptions(path)
    for s in subs:
        if s["email"] == email:
            s["keywords"] = [k for k in s["keywords"] if k != keyword]
    subs = [s for s in subs if s["keywords"]]
    save_subscriptions(subs, path)
    return subs

"""測試共用設定：在匯入 app 之前把資料庫指向暫存檔，避免污染正式 DB。"""
import os
import tempfile

# 必須在任何 app.* 匯入前設定
_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp.close()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.name}"
os.environ.setdefault("SMTP_HOST", "")

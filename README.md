# 台灣政府標案每日爬取與投標工具平台

每日自動爬取**政府電子採購網**（[web.pcc.gov.tw](https://web.pcc.gov.tw)）最新招標公告，
彙整成可**搜尋、篩選、追蹤、Email 通知、匯出**的專業投標工具平台。

> 為投標廠商打造：即時掌握新標案、不漏接符合關鍵字的商機、用看板追蹤投標進度。

---

## 功能

- **每日自動爬取**：用 Playwright 真實瀏覽器抓取官方招標公告詳細資訊（繞過反爬蟲）。
- **搜尋與篩選**：依關鍵字、機關、標的分類、招標方式、預算區間、公告/截止日期查詢。
- **儀表板**：今日新公告、即將截止（3 日內）、機關標案數 Top、最新標案總覽。
- **標案詳情頁**：機關、案號、招標/決標方式、預算、截止/開標時間、履約地點、附件、官方連結。
- **關鍵字訂閱 + Email 通知**：設定關鍵字，每日命中新標案時寄送 Email 摘要。
- **追蹤清單**：看板式狀態（評估中／準備投標／已投標／不投標）＋ 註記。
- **匯出**：依目前篩選條件匯出 **CSV / Excel**，供投標作業使用。

## 技術架構

| 層 | 技術 |
|----|------|
| 後端 / API | FastAPI |
| 前端 | Jinja2 伺服器渲染 + Tailwind CSS (CDN) |
| 資料庫 | SQLite（透過 SQLModel） |
| 爬蟲 | Playwright + Chromium |
| 排程 | GitHub Actions（每日 cron） |
| 通知 | SMTP（stdlib `smtplib`） |

## 專案結構

```
├── scraper/        # 爬蟲：pcc_scraper(Playwright) / parser(解析) / run_daily / notify
├── app/            # FastAPI：models / database / queries / ingest / routers / templates
├── config/         # subscriptions.yml 關鍵字訂閱清單
├── data/raw/       # 每日爬取結果（canonical，由 Actions commit）
├── tests/          # parser 與 API 測試
└── .github/workflows/daily-scrape.yml
```

資料流：`run_daily`（Playwright 爬取）→ `data/raw/YYYYMMDD.json` → `ingest`（upsert 進 SQLite）→ FastAPI 平台查詢。
`Tender` 以 PCC 主鍵 `pcc_pk` 去重，可重複爬取而不重複。

## 快速開始（本機）

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium      # 安裝瀏覽器（爬蟲用）

# 啟動平台（首次啟動會把 data/raw/*.json 匯入 SQLite，含示範資料）
uvicorn app.main:app --reload
# 開啟 http://localhost:8000
```

### 執行每日爬取

```bash
python -m scraper.run_daily                  # 抓今日招標公告
python -m scraper.run_daily --date 2026-06-25
python -m scraper.run_daily --days 3         # 今日往前 3 天
python -m scraper.run_daily --no-headless --max-details 5   # 除錯：顯示瀏覽器、限抓 5 筆
```

### 關鍵字訂閱 Email 通知

1. 在平台「關鍵字訂閱」頁，或直接編輯 `config/subscriptions.yml` 設定關鍵字與信箱。
2. 設定 SMTP（複製 `.env.example` 為 `.env` 填入；或在 GitHub Secrets 設定）。
3. 執行：

```bash
python -m scraper.notify --dry-run    # 只印不寄（先驗證命中）
python -m scraper.notify              # 比對今日資料並寄送
```

## 部署：GitHub Actions 每日排程

`.github/workflows/daily-scrape.yml` 每日 **01:00 UTC（台灣 09:00）** 自動：
爬取 → Email 通知 → 把 `data/raw/` 變更 commit 回 repo。亦可在 Actions 頁面手動 `workflow_dispatch`。

在 repo **Settings → Secrets and variables → Actions** 設定 Email 通知用 Secrets：

| Secret | 說明 |
|--------|------|
| `SMTP_HOST` | 例：`smtp.gmail.com` |
| `SMTP_PORT` | 例：`587` |
| `SMTP_USER` | 寄件帳號 |
| `SMTP_PASS` | 應用程式密碼 |
| `NOTIFY_FROM` | 寄件者顯示（選填） |

> 平台 UI 本身可在本機 / 任意主機以 `uvicorn` 執行；資料由 Actions 每日更新後 `git pull` 即同步。

## 測試

```bash
pytest -q          # 14 項：parser 解析 + API 端點 + 匯出 + 追蹤
```

## 維護爬蟲

`scraper/parser.py` 採「欄位名 → 值」容錯對映，官方頁面微調通常不影響解析。
若官方**改版**導致抓不到列表或詳情，請調整 `scraper/pcc_scraper.py` 的查詢端點
（`_SEARCH_URL`）與分頁選擇器（`_go_next_page`）；解析欄位則調整 `parser.py` 的 `_LABEL_MAP`。

## 注意事項與授權

- 本平台資料蒐集自**政府電子採購網**，僅供**非商業**參考用途，實際以官方公告為準。
- 爬蟲內建隨機延遲（`SCRAPE_MIN_DELAY` / `SCRAPE_MAX_DELAY`），請維持禮貌性爬取、勿過量請求。
- `data/raw/sample.json` 為示範資料，實際運行後可刪除。

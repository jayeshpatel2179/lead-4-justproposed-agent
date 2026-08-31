# leads-agent

Telegram bot that takes a Meta Ads Manager **leads Excel export (.xlsx, < 20 MB)**
and **appends the new leads** into one fixed Google Sheet.

- Existing rows are **never edited, reordered, or deleted**.
- Re-sending the same (or an updated) file only adds rows that aren't there yet.
- Dedup key: `Phone` + `Received` timestamp.
- Reads the `Leads` tab of the workbook; writes columns exactly:
  `Priority, Name, Phone, Occasion, Package Budget, City, Timeline, Ready to Talk, Ad Source, Platform, Received`

Destination sheet:
https://docs.google.com/spreadsheets/d/1fwrMFpywqv_y7Ko570tbtXHeo65YfL4XEwsJZxMhtRA/edit

---

## 1. Google service account (one time)

The bot writes to Google Sheets with a **service account**, not your personal login.

1. Go to https://console.cloud.google.com/ → create a project (any name).
2. APIs & Services → **Enable APIs** → enable **Google Sheets API** and **Google Drive API**.
3. APIs & Services → **Credentials** → **Create credentials** → **Service account**.
   Give it a name, click through, Done.
4. Open the service account → **Keys** → **Add key** → **Create new key** → **JSON**.
   A `.json` file downloads. This is your credential.
5. Open that JSON, copy the `client_email` value
   (looks like `leads-agent@your-project.iam.gserviceaccount.com`).
6. Open the Google Sheet → **Share** → paste that email → give it **Editor** → Send.

For local runs: rename the JSON to `service_account.json` and drop it in this folder.

---

## 2. Run locally (Windows PowerShell)

```powershell
cd C:\Agents\leads-agent
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
```

Copy `.env.example` to `.env` (the bot token and sheet ID are already filled in;
`service_account.json` in the folder covers credentials), then:

```powershell
cd C:\Agents\leads-agent; .\venv\Scripts\python.exe -m bot.main 2>&1 | Tee-Object -FilePath bot.log
```

Then in Telegram: open the bot, `/start`, and send the `.xlsx` file.
Send `/whoami` to get your Telegram user ID if you want to lock the bot down
via `ALLOWED_USER_IDS`.

---

## 3. Deploy on Railway

1. Push this folder to a GitHub repo.
2. Railway → **New Project** → **Deploy from GitHub repo** → pick it.
3. Railway auto-detects Python and installs `requirements.txt`.
   Start command is set in `railway.json` / `Procfile`: `python -m bot.main`
   (it's a **worker** — long polling, no web port needed).
4. Project → **Variables** → add:

   | Variable | Value |
   |---|---|
   | `BOT_TOKEN` | `8720609626:AAGnPhsYh-YibivdJ5snXcnfdTaL1WtRQTY` |
   | `SHEET_ID` | `1fwrMFpywqv_y7Ko570tbtXHeo65YfL4XEwsJZxMhtRA` |
   | `GOOGLE_CREDENTIALS_JSON` | *paste the entire service-account JSON as one line* |
   | `ALLOWED_USER_IDS` | *(optional)* your Telegram user ID |

5. Deploy. Check the **Deploy logs** for `leads-agent starting (long polling)`.

Run only one instance at a time (one poller per bot token).

---

## Files

| File | Purpose |
|---|---|
| `bot/config.py` | env vars, column list, dedup config |
| `bot/excel.py` | read the `Leads` tab from the uploaded `.xlsx` |
| `bot/sheets.py` | append-only writer for the Google Sheet |
| `bot/main.py` | Telegram handlers, entry point (`python -m bot.main`) |

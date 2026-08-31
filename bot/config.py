"""Configuration, loaded from environment variables (Railway) or a local .env file."""
from __future__ import annotations

import json
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# --- Telegram -----------------------------------------------------------------
BOT_TOKEN: str = os.getenv(
    "BOT_TOKEN",
    "8720609626:AAGnPhsYh-YibivdJ5snXcnfdTaL1WtRQTY",
).strip()

# Optional allow-list. Comma-separated Telegram numeric user IDs.
# Leave empty to let anyone who has the bot use it.
_allowed = os.getenv("ALLOWED_USER_IDS", "").replace(" ", "")
ALLOWED_USER_IDS: set[int] = {int(x) for x in _allowed.split(",") if x}

# --- Google Sheets -----------------------------------------------------------
# The one fixed destination spreadsheet. Never a new sheet per upload.
SHEET_ID: str = os.getenv(
    "SHEET_ID", "1fwrMFpywqv_y7Ko570tbtXHeo65YfL4XEwsJZxMhtRA"
).strip()

# Which tab inside that spreadsheet to append into. Empty = first tab (gid=0).
WORKSHEET_NAME: str = os.getenv("WORKSHEET_NAME", "").strip()

# Which tab inside the uploaded Excel file to read leads from.
SOURCE_SHEET_NAME: str = os.getenv("SOURCE_SHEET_NAME", "Leads").strip()

# Max Telegram document size we will accept (bytes). Telegram bot API caps ~20MB.
MAX_FILE_BYTES: int = int(os.getenv("MAX_FILE_BYTES", str(20 * 1024 * 1024)))

# Column order that gets written to the Google Sheet (also the expected header).
COLUMNS: list[str] = [
    "Priority",
    "Name",
    "Phone",
    "Occasion",
    "Package Budget",
    "City",
    "Timeline",
    "Ready to Talk",
    "Ad Source",
    "Platform",
    "Received",
]

# Columns used to decide whether a lead is already in the sheet (0-based index
# into COLUMNS). Phone + Received timestamp uniquely identifies one submission.
DEDUP_COLUMN_INDEXES: tuple[int, ...] = (2, 10)


def load_google_credentials_info() -> dict:
    """Return the service-account dict from GOOGLE_CREDENTIALS_JSON or a local file."""
    raw = os.getenv("GOOGLE_CREDENTIALS_JSON", "").strip()
    if raw:
        return json.loads(raw)

    path = os.getenv("GOOGLE_CREDENTIALS_FILE", "service_account.json").strip()
    p = Path(path)
    if p.is_file():
        return json.loads(p.read_text(encoding="utf-8"))

    raise RuntimeError(
        "No Google credentials found. Set GOOGLE_CREDENTIALS_JSON (full JSON string) "
        "or place a service_account.json next to the bot."
    )

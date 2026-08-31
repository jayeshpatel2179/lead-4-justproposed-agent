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

# A lead is "the same lead" when Phone + Received timestamp match. Re-uploading
# an overlapping date range only appends the rows whose (phone, received) pair
# isn't already in the sheet — existing rows are never touched.
PHONE_COLUMN_INDEX: int = 2
RECEIVED_COLUMN_INDEX: int = 10


_CRED_ENV_VARS = (
    "GOOGLE_CREDENTIALS_JSON",
    "GOOGLE_CREDENTIALS_FILE",
    "GOOGLE_APPLICATION_CREDENTIALS_JSON",
    "GOOGLE_APPLICATION_CREDENTIALS",
    "SERVICE_ACCOUNT_JSON",
)


def _coerce_credentials(val: str) -> dict | None:
    """Turn an env var value into a service-account dict, or None if it isn't one."""
    val = val.strip().strip("'").strip('"').strip()
    if not val:
        return None
    # A JSON blob pasted directly into the variable.
    if "{" in val and "}" in val and '"private_key"' in val:
        blob = val[val.index("{") : val.rindex("}") + 1]
        return json.loads(blob)
    # A path to a JSON key file.
    p = Path(val)
    if p.is_file():
        return json.loads(p.read_text(encoding="utf-8"))
    return None


def load_google_credentials_info() -> dict:
    """Return the service-account dict from any known env var or a local file.

    The JSON can be pasted into any of the vars in _CRED_ENV_VARS (people put it
    in the wrong one), or those vars can hold a path to the key file.
    """
    for var in _CRED_ENV_VARS:
        info = _coerce_credentials(os.getenv(var, ""))
        if info:
            return info

    p = Path("service_account.json")
    if p.is_file():
        return json.loads(p.read_text(encoding="utf-8"))

    present = [v for v in _CRED_ENV_VARS if os.getenv(v, "").strip()]
    raise RuntimeError(
        "No Google credentials found. Paste the full service-account JSON into a "
        "Railway variable named GOOGLE_CREDENTIALS_JSON. "
        + (
            f"(These credential vars are set but unusable: {present})"
            if present
            else "(No credential env var is set at all.)"
        )
    )

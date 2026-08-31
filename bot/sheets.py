"""Append-only writer for the one fixed Google Sheet."""
from __future__ import annotations

import gspread
from google.oauth2.service_account import Credentials

from . import config

_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
]


def _client() -> gspread.Client:
    creds = Credentials.from_service_account_info(
        config.load_google_credentials_info(), scopes=_SCOPES
    )
    return gspread.authorize(creds)


def _worksheet(gc: gspread.Client):
    sh = gc.open_by_key(config.SHEET_ID)
    if config.WORKSHEET_NAME:
        try:
            return sh.worksheet(config.WORKSHEET_NAME)
        except gspread.WorksheetNotFound:
            return sh.add_worksheet(
                config.WORKSHEET_NAME, rows=1000, cols=len(config.COLUMNS)
            )
    return sh.sheet1


def _key(row: list[str]) -> tuple[str, ...]:
    return tuple(
        (row[i].strip().lower() if i < len(row) else "")
        for i in config.DEDUP_COLUMN_INDEXES
    )


class AppendResult:
    def __init__(self, added: int, skipped: int, total_after: int, header_written: bool):
        self.added = added
        self.skipped = skipped
        self.total_after = total_after
        self.header_written = header_written


def append_leads(rows: list[list[str]]) -> AppendResult:
    """Append only the leads not already present. Never edits or deletes rows."""
    gc = _client()
    ws = _worksheet(gc)

    existing = ws.get_all_values()

    header_written = False
    if not existing or not any(any(c.strip() for c in r) for r in existing):
        ws.update(range_name="A1", values=[config.COLUMNS])
        existing = [config.COLUMNS]
        header_written = True

    seen = {_key(r) for r in existing[1:]}

    new_rows: list[list[str]] = []
    skipped = 0
    for row in rows:
        k = _key(row)
        if k in seen:
            skipped += 1
            continue
        seen.add(k)
        new_rows.append(row)

    if new_rows:
        ws.append_rows(
            new_rows,
            value_input_option="RAW",
            insert_data_option="INSERT_ROWS",
            table_range="A1",
        )

    total_after = len(existing) - 1 + len(new_rows)
    return AppendResult(len(new_rows), skipped, total_after, header_written)


def service_account_email() -> str:
    return config.load_google_credentials_info().get("client_email", "unknown")

"""Append-only writer for the one fixed Google Sheet."""
from __future__ import annotations

import re

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


def _cell(row: list[str], idx: int) -> str:
    return row[idx].strip() if idx < len(row) and row[idx] is not None else ""


def _norm_phone(value: str) -> str:
    """Digits only, last 10 — so +91 93116 97389 / 919311697389 / 9311697389 match."""
    digits = re.sub(r"\D", "", value or "")
    return digits[-10:] if len(digits) >= 10 else digits


def _norm_received(value: str) -> str:
    """Trim to 'YYYY-MM-DD HH:MM:SS' so formatting noise doesn't break matching."""
    return (value or "").strip()[:19]


def _key(row: list[str]) -> tuple[str, str]:
    return (
        _norm_phone(_cell(row, config.PHONE_COLUMN_INDEX)),
        _norm_received(_cell(row, config.RECEIVED_COLUMN_INDEX)),
    )


class AppendResult:
    def __init__(
        self,
        added: int,
        skipped: int,
        total_after: int,
        header_written: bool,
        added_received: list[str],
        skipped_received: list[str],
    ):
        self.added = added
        self.skipped = skipped
        self.total_after = total_after
        self.header_written = header_written
        self.added_received = added_received
        self.skipped_received = skipped_received


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
    added_received: list[str] = []
    skipped_received: list[str] = []
    for row in rows:
        k = _key(row)
        received = _cell(row, config.RECEIVED_COLUMN_INDEX)
        if k in seen:
            skipped_received.append(received)
            continue
        seen.add(k)
        new_rows.append(row)
        added_received.append(received)

    if new_rows:
        ws.append_rows(
            new_rows,
            value_input_option="RAW",
            insert_data_option="INSERT_ROWS",
            table_range="A1",
        )

    total_after = len(existing) - 1 + len(new_rows)
    return AppendResult(
        len(new_rows),
        len(skipped_received),
        total_after,
        header_written,
        added_received,
        skipped_received,
    )


def service_account_email() -> str:
    return config.load_google_credentials_info().get("client_email", "unknown")

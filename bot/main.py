"""Telegram bot: receive an .xlsx lead export, append new leads to the Google Sheet."""
from __future__ import annotations

import asyncio
import logging

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from . import config
from .excel import ExcelParseError, parse_leads
from .sheets import append_leads

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    level=logging.INFO,
)
log = logging.getLogger("leads-agent")

SHEET_URL = f"https://docs.google.com/spreadsheets/d/{config.SHEET_ID}/edit"


def _date_range(received_values: list[str]) -> str:
    """'2026-08-01 → 2026-08-15' from a list of Received timestamps (or '' if none)."""
    days = sorted({v.strip()[:10] for v in received_values if v and v.strip()})
    if not days:
        return ""
    return days[0] if len(days) == 1 else f"{days[0]} → {days[-1]}"


def _authorised(update: Update) -> bool:
    if not config.ALLOWED_USER_IDS:
        return True
    user = update.effective_user
    return bool(user and user.id in config.ALLOWED_USER_IDS)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Send me the Meta Ads leads Excel file (.xlsx, under 20 MB).\n"
        "I append every new lead into the shared Google Sheet — "
        "existing rows are never changed or deleted.\n\n"
        f"Sheet: {SHEET_URL}"
    )


async def whoami(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    u = update.effective_user
    await update.message.reply_text(f"Your Telegram user ID: {u.id}")


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    if not _authorised(update):
        await message.reply_text("Sorry, you are not authorised to use this bot.")
        return

    doc = message.document
    name = (doc.file_name or "").lower()
    if not name.endswith((".xlsx", ".xlsm")):
        await message.reply_text("Please send an .xlsx file exported from Meta Ads Manager.")
        return
    if doc.file_size and doc.file_size > config.MAX_FILE_BYTES:
        await message.reply_text(
            f"That file is {doc.file_size / 1_048_576:.1f} MB. Limit is 20 MB."
        )
        return

    await context.bot.send_chat_action(message.chat_id, ChatAction.TYPING)
    status = await message.reply_text("Got it — reading the file...")

    try:
        tg_file = await doc.get_file()
        data = bytes(await tg_file.download_as_bytearray())
    except Exception as exc:  # noqa: BLE001
        log.exception("download failed")
        await status.edit_text(f"Could not download the file from Telegram: {exc}")
        return

    try:
        _, rows = parse_leads(data)
    except ExcelParseError as exc:
        await status.edit_text(f"Could not read the leads: {exc}")
        return

    if not rows:
        await status.edit_text("No lead rows found in that file.")
        return

    await status.edit_text(f"Read {len(rows)} rows. Updating the Google Sheet...")

    try:
        result = await asyncio.to_thread(append_leads, rows)
    except Exception as exc:  # noqa: BLE001
        log.exception("sheet append failed")
        await status.edit_text(f"Failed to update the Google Sheet: {exc}")
        return

    lines = []
    if result.added:
        rng = _date_range(result.added_received)
        lines.append(f"✅ Added {result.added} new lead(s){f' ({rng})' if rng else ''}.")
    else:
        lines.append("✅ Added 0 new leads — everything in this file was already in the sheet.")
    if result.skipped:
        rng = _date_range(result.skipped_received)
        lines.append(
            f"⏭️ Skipped {result.skipped} duplicate(s){f' ({rng})' if rng else ''} "
            f"— already in the sheet, not written again."
        )
    lines.append(f"📊 Sheet now has {result.total_after} lead rows.")
    if result.header_written:
        lines.append("(Wrote the header row — the sheet was empty.)")
    lines.append(SHEET_URL)
    await status.edit_text("\n".join(lines))


async def handle_other(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Send the leads Excel file as a document (.xlsx).")


async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    log.exception("unhandled error", exc_info=context.error)


def main() -> None:
    if not config.BOT_TOKEN:
        raise SystemExit("BOT_TOKEN is not set.")

    app = Application.builder().token(config.BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", start))
    app.add_handler(CommandHandler("whoami", whoami))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_other)
    )
    app.add_error_handler(on_error)

    log.info("leads-agent starting (long polling). Target sheet: %s", config.SHEET_ID)
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    main()

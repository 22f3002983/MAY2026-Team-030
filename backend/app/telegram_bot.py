import asyncio
import os
import threading

from telegram import Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters

TELEGRAM_BOT_TOKEN    = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_BOT_USERNAME = os.getenv('TELEGRAM_BOT_USERNAME')

# in-memory conversation state for the /start flow — keyed by Telegram chat_id,
# e.g. {'step': 'awaiting_email', 'role': 'resident', 'email': '...'}. No DB
# table needed, this is purely a short-lived onboarding handshake.
_pending = {}


def _digits_only(text):
    return ''.join(ch for ch in text if ch.isdigit())


# ── outbound sends — non-blocking relative to the Flask request thread ──────

async def _send_one(chat_id, message):
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    async with bot:
        await bot.send_message(chat_id=chat_id, text=message)


async def _send_many(chat_ids, message):
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    async with bot:
        await asyncio.gather(
            *(bot.send_message(chat_id=chat_id, text=message) for chat_id in chat_ids),
            return_exceptions=True,
        )


def send_telegram_message(chat_id, message):
    """Send one Telegram message. Fire-and-forget on a background thread so
    the caller's API response never waits on Telegram's HTTP round trip."""
    if not TELEGRAM_BOT_TOKEN:
        print(' * [telegram] TELEGRAM_BOT_TOKEN not set — skipping send', flush=True)
        return
    if not chat_id:
        return

    def _run():
        try:
            asyncio.run(_send_one(chat_id, message))
        except Exception as exc:
            print(f' * [telegram] failed to send to {chat_id}: {exc}', flush=True)

    threading.Thread(target=_run, daemon=True).start()


def send_telegram_message_bulk(chat_ids, message):
    """Send the same message to many chat ids concurrently, off-thread."""
    chat_ids = [c for c in chat_ids if c]
    if not TELEGRAM_BOT_TOKEN:
        print(' * [telegram] TELEGRAM_BOT_TOKEN not set — skipping bulk send', flush=True)
        return
    if not chat_ids:
        return

    def _run():
        try:
            asyncio.run(_send_many(chat_ids, message))
        except Exception as exc:
            print(f' * [telegram] bulk send failed: {exc}', flush=True)

    threading.Thread(target=_run, daemon=True).start()


# ── inbound — the /start onboarding conversation ────────────────────────────

def start_telegram_bot(flask_app):
    """Start long-polling for the bot in a background thread, once per
    running process. Mirrors the reloader guard in app/scheduler.py so the
    Werkzeug debug reloader's watcher process doesn't start a second poller."""
    if flask_app.debug and os.environ.get('WERKZEUG_RUN_MAIN') != 'true':
        return

    if not TELEGRAM_BOT_TOKEN:
        print(' * [telegram] TELEGRAM_BOT_TOKEN not set — Telegram bot disabled', flush=True)
        return

    async def handle_start(update, context):
        chat_id = update.effective_chat.id
        _pending[chat_id] = {'step': 'awaiting_role'}
        await update.message.reply_text(
            "Welcome to the Niwaas bot!\n\n"
            "Are you a Resident or a Vendor? Reply with 'resident' or 'vendor'."
        )

    async def handle_message(update, context):
        chat_id = update.effective_chat.id
        text = (update.message.text or '').strip()
        state = _pending.get(chat_id)

        if not state:
            await update.message.reply_text('Send /start to begin.')
            return

        step = state['step']

        if step == 'awaiting_role':
            role = text.lower()
            if role not in ('resident', 'vendor'):
                await update.message.reply_text("Please reply with 'resident' or 'vendor'.")
                return
            state['role'] = role
            if role == 'resident':
                state['step'] = 'awaiting_email'
                await update.message.reply_text('Please send your email address.')
            else:
                state['step'] = 'awaiting_vendor_phone'
                await update.message.reply_text('Please send the last 6 digits of your registered phone number.')
            return

        if step == 'awaiting_email':
            state['email'] = text.strip().lower()
            state['step'] = 'awaiting_resident_phone'
            await update.message.reply_text('Thanks. Now send the last 4 digits of your phone number.')
            return

        if step == 'awaiting_resident_phone':
            last4 = _digits_only(text)
            email = state.get('email', '')
            with flask_app.app_context():
                from app.extensions import db
                from app.models.resident import Resident
                from app.models.user import User

                resident = (
                    Resident.query
                    .join(User, Resident.user_id == User.id)
                    .filter(User.email == email, Resident.phone.like(f'%{last4}'))
                    .first()
                )

                if resident:
                    resident.telegram_chat_id = str(chat_id)
                    db.session.commit()
                    if resident.invite_code:
                        await update.message.reply_text(f'Connected! Your invite code is: {resident.invite_code}')
                    else:
                        await update.message.reply_text("Connected! You've already completed onboarding.")
                else:
                    await update.message.reply_text('No resident found with these details. Please check with your secretary.')
            _pending.pop(chat_id, None)
            return

        if step == 'awaiting_vendor_phone':
            last6 = _digits_only(text)
            with flask_app.app_context():
                from app.extensions import db
                from app.models.vendor import Vendor

                vendor = Vendor.query.filter(Vendor.phone.like(f'%{last6}')).first()

                if vendor:
                    vendor.telegram_chat_id = str(chat_id)
                    db.session.commit()
                    await update.message.reply_text("Connected! You'll now receive job assignment notifications here.")
                else:
                    await update.message.reply_text('No vendor found with these details. Please check with your secretary.')
            _pending.pop(chat_id, None)
            return

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler('start', handle_start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    def _run_polling():
        try:
            # stop_signals=None — PTB's default signal handling only works on
            # the main thread; this runs on a background daemon thread.
            application.run_polling(stop_signals=None)
        except Exception as exc:
            print(f' * [telegram] polling loop crashed: {exc}', flush=True)

    threading.Thread(target=_run_polling, daemon=True).start()
    print(' * [telegram] bot polling started', flush=True)

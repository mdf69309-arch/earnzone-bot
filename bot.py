"""
EarnZone Telegram Bot — Firebase REST API version
==================================================
Service Account JSON লাগবে না!
শুধু Bot Token + Firebase Project ID দিলেই হবে।

Install:
  pip install python-telegram-bot==20.7 requests

Run:
  python bot.py
"""

import logging
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ContextTypes
)

# ══════════════════════════════════════════════════════════
#  ⚙️  CONFIG — শুধু এই দুটো পরিবর্তন করো
# ══════════════════════════════════════════════════════════
BOT_TOKEN    = "8656382731:AAFMeYcssvFWYSL9pKM-pda2PY92qzd8U2c"    # @BotFather থেকে নাও
PROJECT_ID   = "self-io-820e5"     # তোমার Firebase Project ID
# ══════════════════════════════════════════════════════════

FIRESTORE_URL = (
    f"https://firestore.googleapis.com/v1/projects/"
    f"{PROJECT_ID}/databases/(default)/documents"
)

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


# ─── Firebase REST helper ──────────────────────────────────
def fs_get(collection: str, document: str) -> dict:
    url = f"{FIRESTORE_URL}/{collection}/{document}"
    try:
        r = requests.get(url, timeout=8)
        if r.status_code == 200:
            fields = r.json().get("fields", {})
            return {k: list(v.values())[0] for k, v in fields.items()}
    except Exception as e:
        logger.warning(f"Firestore read error: {e}")
    return {}


def cfg(key: str, default: str = "") -> str:
    data = fs_get("settings", "botConfig")
    return str(data.get(key, "")).strip() or default


# ─── /start ───────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user    = update.effective_user
    name    = user.first_name or "বন্ধু"

    channel = cfg("channel",     "@earnzone_bd")
    banner  = cfg("bannerImage", "")
    welcome = cfg("welcomeText", "👋 স্বাগতম {name}!\nচ্যানেলে জয়েন করুন তারপর অ্যাপ চালু করুন।")
    welcome = welcome.replace("{name}", name)
    ch_link = f"https://t.me/{channel.lstrip('@')}"

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Join Channel",  url=ch_link)],
        [InlineKeyboardButton("✅ Check Join",    callback_data=f"chk:{channel}")],
    ])

    try:
        if banner:
            await update.message.reply_photo(
                photo=banner, caption=welcome,
                reply_markup=keyboard, parse_mode="HTML",
            )
        else:
            await update.message.reply_text(
                welcome, reply_markup=keyboard, parse_mode="HTML",
            )
    except Exception as e:
        logger.error(f"start error: {e}")
        await update.message.reply_text(welcome, reply_markup=keyboard)


# ─── Check Join callback ───────────────────────────────────
async def check_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query   = update.callback_query
    await query.answer()

    user    = query.from_user
    channel = query.data.split(":", 1)[1] if ":" in query.data else "@earnzone_bd"
    joined  = await is_member(context, user.id, channel)

    if joined:
        await show_howto(query, context)
    else:
        await query.answer(
            "❌ আপনি এখনো চ্যানেলে জয়েন করেননি!\n"
            "প্রথমে Join Channel এ ক্লিক করুন, তারপর আবার Check করুন।",
            show_alert=True,
        )


async def is_member(context, user_id: int, channel: str) -> bool:
    try:
        m = await context.bot.get_chat_member(chat_id=channel, user_id=user_id)
        return m.status in ("member", "administrator", "creator")
    except Exception as e:
        logger.warning(f"Member check failed: {e}")
        return False


# ─── How to Work ──────────────────────────────────────────
async def show_howto(query, context: ContextTypes.DEFAULT_TYPE):
    mini_app = cfg("miniAppUrl",   "https://t.me/selfiotop_bot/selfio")
    youtube  = cfg("youtubeUrl",   "")
    banner2  = cfg("bannerImage2", "") or cfg("bannerImage", "")
    msg      = cfg("howtoText",    "🎉 অভিনন্দন! ভিডিও দেখে অ্যাপ চালু করুন!")

    buttons = []
    if youtube:
        buttons.append([InlineKeyboardButton("▶️ How to Work দেখুন", url=youtube)])
    buttons.append([InlineKeyboardButton("🚀 App চালু করুন", url=mini_app)])
    keyboard = InlineKeyboardMarkup(buttons)

    try:
        if banner2:
            await query.message.reply_photo(
                photo=banner2, caption=msg,
                reply_markup=keyboard, parse_mode="HTML",
            )
        else:
            await query.message.reply_text(
                msg, reply_markup=keyboard, parse_mode="HTML",
            )
    except Exception as e:
        logger.error(f"show_howto error: {e}")
        await query.message.reply_text(msg, reply_markup=keyboard)


# ─── Main ─────────────────────────────────────────────────
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(check_join, pattern=r"^chk:"))
    logger.info("✅ EarnZone Bot চালু হয়েছে!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()

import logging
import os
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

BOT_TOKEN  = os.environ.get("BOT_TOKEN", "8656382731:AAFMeYcssvFWYSL9pKM-pda2PY92qzd8U2c")
PROJECT_ID = os.environ.get("PROJECT_ID", "self-io-820e5")
FIRESTORE_URL = f"https://firestore.googleapis.com/v1/projects/{PROJECT_ID}/databases/(default)/documents"

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Cache: 5 মিনিট পর পর Firebase পড়বে ──
import time
_cache = {}
_cache_time = 0
CACHE_TTL = 300  # 5 minutes

def get_config() -> dict:
    global _cache, _cache_time
    now = time.time()
    if _cache and (now - _cache_time) < CACHE_TTL:
        return _cache
    try:
        url = f"{FIRESTORE_URL}/settings/botConfig"
        r = requests.get(url, timeout=5)
        if r.status_code == 200:
            fields = r.json().get("fields", {})
            _cache = {k: list(v.values())[0] for k, v in fields.items()}
            _cache_time = now
            logger.info("✅ Config loaded from Firebase")
    except Exception as e:
        logger.warning(f"Config load failed: {e}")
    return _cache

def cfg(key: str, default: str = "") -> str:
    return str(get_config().get(key, "")).strip() or default

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user    = update.effective_user
    name    = user.first_name or "বন্ধু"
    channel = cfg("channel",     "@earnzone_bd")
    banner  = cfg("bannerImage", "")
    welcome = cfg("welcomeText", "👋 স্বাগতম {name}!\nচ্যানেলে জয়েন করুন তারপর অ্যাপ চালু করুন।")
    welcome = welcome.replace("{name}", name)
    ch_link = f"https://t.me/{channel.lstrip('@')}"
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Join Channel", url=ch_link)],
        [InlineKeyboardButton("✅ Check Join",   callback_data=f"chk:{channel}")],
    ])
    try:
        if banner:
            await update.message.reply_photo(photo=banner, caption=welcome, reply_markup=keyboard, parse_mode="HTML")
        else:
            await update.message.reply_text(welcome, reply_markup=keyboard, parse_mode="HTML")
    except Exception as e:
        logger.error(f"start error: {e}")
        await update.message.reply_text(welcome, reply_markup=keyboard)

async def check_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query   = update.callback_query
    await query.answer()
    user    = query.from_user
    channel = query.data.split(":", 1)[1] if ":" in query.data else "@earnzone_bd"
    try:
        m = await context.bot.get_chat_member(chat_id=channel, user_id=user.id)
        joined = m.status in ("member", "administrator", "creator")
    except:
        joined = False
    if joined:
        mini_app = cfg("miniAppUrl",   "https://t.me/selfiotop_bot/selfio")
        youtube  = cfg("youtubeUrl",   "")
        banner2  = cfg("bannerImage2", "") or cfg("bannerImage", "")
        msg      = cfg("howtoText",    "🎉 অভিনন্দন! ভিডিও দেখে অ্যাপ চালু করুন!")
        buttons  = []
        if youtube:
            buttons.append([InlineKeyboardButton("▶️ How to Work দেখুন", url=youtube)])
        buttons.append([InlineKeyboardButton("🚀 App চালু করুন", url=mini_app)])
        keyboard = InlineKeyboardMarkup(buttons)
        try:
            if banner2:
                await query.message.reply_photo(photo=banner2, caption=msg, reply_markup=keyboard, parse_mode="HTML")
            else:
                await query.message.reply_text(msg, reply_markup=keyboard, parse_mode="HTML")
        except Exception as e:
            await query.message.reply_text(msg, reply_markup=keyboard)
    else:
        await query.answer(
            "❌ এখনো জয়েন করেননি!\nJoin Channel এ ক্লিক করুন তারপর আবার Check করুন।",
            show_alert=True
        )

def main():
    # বট শুরুতেই config load করে রাখবে
    get_config()
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(check_join, pattern=r"^chk:"))
    logger.info("✅ EarnZone Bot চালু হয়েছে!")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

if __name__ == "__main__":
    main()

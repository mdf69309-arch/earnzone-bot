import logging, os, time, requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import asyncio

BOT_TOKEN       = os.environ.get("BOT_TOKEN",  "8656382731:AAFMeYcssvFWYSL9pKM-pda2PY92qzd8U2c")
NOTIFY_TOKEN    = "8593684106:AAE0twUXgaemszAopWt1XtV1BIeU92mQ2ps"
NOTIFY_CHAT_ID  = "7522853883"
PROJECT_ID      = os.environ.get("PROJECT_ID", "self-io-820e5")
FIRESTORE_URL   = f"https://firestore.googleapis.com/v1/projects/{PROJECT_ID}/databases/(default)/documents"

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Config Cache ───────────────────────────────────────────
_cache={}; _cache_time=0; CACHE_TTL=300

def get_config():
    global _cache,_cache_time
    now=time.time()
    if _cache and (now-_cache_time)<CACHE_TTL: return _cache
    try:
        r=requests.get(f"{FIRESTORE_URL}/settings/botConfig",timeout=5)
        if r.status_code==200:
            fields=r.json().get("fields",{})
            _cache={k:list(v.values())[0] for k,v in fields.items()}
            _cache_time=now
    except Exception as e:
        logger.warning(f"Config load failed: {e}")
    return _cache

def cfg(key,default=""):
    return str(get_config().get(key,"")).strip() or default

# ── /start ─────────────────────────────────────────────────
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
            await update.message.reply_photo(photo=banner,caption=welcome,reply_markup=keyboard,parse_mode="HTML")
        else:
            await update.message.reply_text(welcome,reply_markup=keyboard,parse_mode="HTML")
    except Exception as e:
        logger.error(f"start error: {e}")
        await update.message.reply_text(welcome,reply_markup=keyboard)

# ── Check Join ─────────────────────────────────────────────
async def check_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query   = update.callback_query
    await query.answer()
    user    = query.from_user
    channel = query.data.split(":",1)[1] if ":" in query.data else "@earnzone_bd"
    try:
        m = await context.bot.get_chat_member(chat_id=channel,user_id=user.id)
        joined = m.status in ("member","administrator","creator")
    except:
        joined = False
    if joined:
        mini_app = cfg("miniAppUrl",  "https://t.me/selfiotop_bot/selfio")
        youtube  = cfg("youtubeUrl",  "")
        banner2  = cfg("bannerImage2","") or cfg("bannerImage","")
        msg      = cfg("howtoText",   "🎉 অভিনন্দন! ভিডিও দেখে অ্যাপ চালু করুন!")
        buttons  = []
        if youtube:
            buttons.append([InlineKeyboardButton("▶️ How to Work দেখুন",url=youtube)])
        buttons.append([InlineKeyboardButton("🚀 App চালু করুন",url=mini_app)])
        keyboard = InlineKeyboardMarkup(buttons)
        try:
            if banner2:
                await query.message.reply_photo(photo=banner2,caption=msg,reply_markup=keyboard,parse_mode="HTML")
            else:
                await query.message.reply_text(msg,reply_markup=keyboard,parse_mode="HTML")
        except:
            await query.message.reply_text(msg,reply_markup=keyboard)
    else:
        await query.answer("❌ এখনো জয়েন করেননি!\nJoin Channel এ ক্লিক করুন তারপর আবার Check করুন।",show_alert=True)

# ── Withdraw Notification Checker ─────────────────────────
_notified = set()

async def check_withdraw_loop(app):
    """প্রতি ২০ সেকেন্ডে নতুন pending withdraw চেক করো।"""
    await asyncio.sleep(10)  # শুরুতে একটু অপেক্ষা
    while True:
        try:
            url = f"{FIRESTORE_URL}/withdrawRequests?pageSize=30"
            r   = requests.get(url, timeout=8)
            if r.status_code == 200:
                docs = r.json().get("documents", [])
                for doc in docs:
                    doc_id = doc.get("name","").split("/")[-1]
                    fields = doc.get("fields",{})
                    status = list(fields.get("status",{}).values())[0] if "status" in fields else ""

                    if status != "pending" or doc_id in _notified:
                        continue

                    _notified.add(doc_id)

                    name   = list(fields.get("userName",{}).values())[0] if "userName" in fields else "অজানা"
                    method = list(fields.get("method",  {}).values())[0] if "method"   in fields else "N/A"
                    phone  = list(fields.get("phone",   {}).values())[0] if "phone"    in fields else "N/A"
                    taka   = list(fields.get("taka",    {}).values())[0] if "taka"     in fields else "0"

                    method_name = {"bkash":"💗 bKash","nagad":"🟠 Nagad","rocket":"🚀 Rocket"}.get(method,method)
                    msg = (
                        f"💸 নতুন Withdraw রিকোয়েস্ট!\n\n"
                        f"👤 নাম: {name}\n"
                        f"💳 মেথড: {method_name}\n"
                        f"📱 নাম্বার: {phone}\n"
                        f"💰 পরিমাণ: ৳{taka}\n\n"
                        f"⏳ Admin Panel থেকে অনুমোদন করুন।"
                    )
                    try:
                        await app.bot.send_message(
                            chat_id=NOTIFY_CHAT_ID,
                            text=msg
                        )
                        logger.info(f"✅ Withdraw notify sent: {doc_id}")
                    except Exception as e:
                        logger.warning(f"Notify send failed: {e}")

        except Exception as e:
            logger.warning(f"Withdraw check error: {e}")

        await asyncio.sleep(20)

# ── Main ───────────────────────────────────────────────────
async def post_init(app):
    asyncio.create_task(check_withdraw_loop(app))
    logger.info("✅ Withdraw checker চালু হয়েছে!")

def main():
    get_config()
    app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(check_join, pattern=r"^chk:"))
    logger.info("✅ EarnZone Bot চালু হয়েছে!")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

if __name__ == "__main__":
    main()

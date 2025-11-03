import logging
import os
import sys
import asyncio
from aiohttp import web
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    MessageHandler, 
    filters,
)

# ===============================
# 🔧 CONFIGURATION
# ===============================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
SOURCE_CHANNEL_ID = int(os.getenv("SOURCE_CHANNEL_ID", "0"))
TARGET_CHANNEL_ID = int(os.getenv("TARGET_CHANNEL_ID", "0"))
RENDER_EXTERNAL_URL = "https://quotexpro1.onrender.com"  # your Render URL
WEBHOOK_PATH = "/telegram"
WEBHOOK_URL = f"{RENDER_EXTERNAL_URL}{WEBHOOK_PATH}" if RENDER_EXTERNAL_URL else ""

app = None  # will hold telegram app instance


# ===============================
# 🎯 HANDLE FORWARDED OR CHANNEL MESSAGES
# ===============================
async def handle_forward(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.channel_post or update.message
    if not msg or not msg.text:
        return

    text = msg.text.strip()
    lines = text.splitlines()

    # ===============================
    # 🎯 Detect Trade Signals
    # ===============================
    if any("💳" in line for line in lines) and any("🔥" in line for line in lines):
        try:
            asset = "N/A"
            time = "N/A"
            direction = "N/A"

            for line in lines:
                if "💳" in line:
                    asset = line.replace("💳", "").strip()
                elif "⌛" in line:
                    time = line.replace("⌛", "").strip()
                elif "🔼" in line or "🔽" in line:
                    dir_raw = line.replace("🔼", "").replace("🔽", "").strip().lower()
                    if dir_raw == "call":
                        direction = "🟢 UP 🟢"
                    elif dir_raw == "put":
                        direction = "🔴 DOWN 🔴"

            formatted_signal = (
    f"🚀 <u><b>𝗢𝗻𝗲 𝗠𝗶𝗻𝘂𝘁𝗲 𝗧𝗿𝗮𝗱𝗲 (𝟭 𝗠𝗜𝗡𝗧)</b></u> 🚀\n\n"
    f"🀄 <u>{asset}</u>\n"
    f"⚡️ <u>𝐓𝐈𝐌𝐄 𝐙𝐎𝐍𝐄 𝐔𝐓𝐂 +𝟓:𝟑𝟎</u>\n"
    f"⌚ <u>{time} ENTRY TIME</u>\n"
    f"<u>{direction}</u>\n\n"
    f"💎 𝗣𝗿𝗲𝗺𝗶𝘂𝗺 𝗦𝗶𝗴𝗻𝗮𝗹 💎\n"
    f"━━━━━━━━━━━━━━━\n"
    f"👇 <u><b>OFFICIAL REGISTRATION LINK</b></u>\n"
    f"👉<a href="https://broker-qx.pro/sign-up/?lid=1200739">Join Free VIP REGISTER HERE</a>\n\n"
    f"🎁 <u><b>USE CODE:</b></u> <code>Masterguru</code>\n"
    f"💥 <u><b>GET INSTANT 50% BONUS ON FIRST DEPOSIT!</b></u>\n"
    f"<i>(Valid only via this official link)</i>\n"
    f"━━━━━━━━━━━━━━━"
            )

            await context.bot.send_message(
                chat_id=TARGET_CHANNEL_ID,
                text=formatted_signal,
                parse_mode='HTML'
            )
            return

        except Exception as e:
            logger.warning(f"Signal parsing error: {e}")
            return

    # ===============================
    # 🎯 Detect Result Messages
    # ===============================
    text_upper = text.upper()

    try:
        result_msg = None
        final_caption = None

        # ✅ MTG WIN
        if "WIN ✅¹" in text_upper or "MTG WIN" in text_upper:
            result_msg = "✅ MTG WIN"
            final_caption = "✅ MTG WIN"

        # ✅ Normal WIN
        elif "WIN ✅" in text_upper and "¹" not in text_upper and "²" not in text_upper:
            result_msg = "✅ WIN"
            final_caption = "✅ WIN"

        # 💔 LOSS or WIN ✅² → LOSS
        elif "WIN ✅²" in text_upper or "💔 LOSS" in text_upper or "LOSS" in text_upper:
            result_msg = "💔 LOSS"

            # Custom message for WIN ✅² treated as LOSS
            if "WIN ✅²" in text_upper:
                final_caption = (
    "💔 LOSS\n"
    "<b><u>Relax bro</u></b> 😎\n"
    "<b><u><i>Next trade me plan ke sath recover kar lenge</i></u></b> 💪"
                )

            # Consecutive loss message
            elif "LOSS" in text_upper and ("CONSEC" in text_upper or "2 LOSS" in text_upper):
                final_caption = (
                    f"💔 LOSS\n"
                    f"Don’t panic, <b><u>bounce back stronger</u></b> 💪\n"
                    f"One loss can’t stop a <b><u>future winner</u></b>🔥"
                )

            # Normal loss message
            elif "LOSS" in text_upper or "💔 LOSS" in text_upper:
                final_caption = (
    "💔 LOSS\n"
    "<b><u>Relax bro</u></b> 😎\n"
    "<b><u><i>Next trade me plan ke sath recover kar lenge</i></u></b> 💪"
                )

        # ⚖ DOJI
        elif "DOJI" in text_upper or "⚖" in text_upper:
            result_msg = "⚖ DOJI"
            final_caption = "⚖ DOJI"

        # ✅ Send final message if detected
        if final_caption:
            await context.bot.send_message(
                chat_id=TARGET_CHANNEL_ID,
                text=f"<b>{final_caption}</b>",
                parse_mode="HTML"
            )

    except Exception as e:
        logger.warning(f"Result message parsing error: {e}")
        return

# ===============================
# 🌐 AIOHTTP HANDLERS
# ===============================
async def handle_telegram_webhook(request):
    try:
        data = await request.json()
        update = Update.de_json(data, app.bot)
        await app.process_update(update)
    except Exception as e:
        logger.error(f"Webhook update error: {e}")
    return web.Response(text="OK")


async def handle_health(request):
    return web.Response(text="Bot is alive! 🚀")


# ===============================
# 🔄 KEEP-ALIVE PING (RENDER)
# ===============================
async def periodic_ping(url: str, interval: int = 30):
    import aiohttp
    while True:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    logger.info(f"Keep-alive ping to {url} — Status: {resp.status}")
        except Exception as e:
            logger.warning(f"Keep-alive error: {e}")
        await asyncio.sleep(interval)


# ===============================
# 🚀 START WEB SERVER
# ===============================
async def run_web_server():
    port = int(os.environ.get('PORT', 10000))
    web_app = web.Application()
    web_app.router.add_get("/", handle_health)
    web_app.router.add_post(WEBHOOK_PATH, handle_telegram_webhook)

    runner = web.AppRunner(web_app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info(f"Web server running on port {port}")


# ===============================
# 🧠 MAIN
# ===============================
async def main():
    global app
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Handle channel or forwarded posts
    app.add_handler(MessageHandler(filters.ALL, handle_forward))

    logger.info("Initializing and setting webhook...")
    await app.initialize()
    await app.bot.set_webhook(WEBHOOK_URL)
    await app.start()

    await run_web_server()

    if RENDER_EXTERNAL_URL:
        asyncio.create_task(periodic_ping(RENDER_EXTERNAL_URL))

    stop_event = asyncio.Event()
    await stop_event.wait()

    await app.stop()
    await app.shutdown()


# ===============================
# 🏁 ENTRY POINT
# ===============================
if __name__ == "__main__":
    if sys.platform.startswith("win") and sys.version_info[:2] >= (3, 8):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    asyncio.run(main())










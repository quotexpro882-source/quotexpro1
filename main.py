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

# ✅ Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

# ✅ Environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
SOURCE_CHANNEL_ID = int(os.getenv("SOURCE_CHANNEL_ID"))
TARGET_CHANNEL_ID = int(os.getenv("TARGET_CHANNEL_ID"))
RENDER_EXTERNAL_URL = "https://quotexpro1.onrender.com"  # e.g., https://yourapp.onrender.com
WEBHOOK_PATH = "/telegram"
WEBHOOK_URL = f"{RENDER_EXTERNAL_URL}{WEBHOOK_PATH}" if RENDER_EXTERNAL_URL else ""

app = None  # Will hold the Telegram app instance


async def copy_channel_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.channel_post

    if msg.chat.id != SOURCE_CHANNEL_ID:
        return  # Only accept from source channel

    # ✅ Process text-based messages
    if msg.text:
        text = msg.text.strip()
        lines = text.splitlines()

        # ✅ Check for presence of 💳 and 🔥 to consider it a signal
        if any("💳" in line for line in lines) and any("🔥" in line for line in lines):
            try:
                # Set defaults
                asset = "N/A"
                timeframe = "N/A"
                time = "N/A"
                direction = "N/A"
                trend = "N/A"
                forecast = "N/A"
                payout = "N/A"

                # Extract available data
                for line in lines:
                    if "💳" in line:
                        asset = line.replace("💳", "").strip()
                    elif "🔥" in line:
                        raw_timeframe = line.replace("🔥", "").strip()
                        if raw_timeframe.startswith("M") and raw_timeframe[1:].isdigit():
                            minutes = raw_timeframe[1:]
                            timeframe = f"{minutes} Minute" if minutes == "1" else f"{minutes} Minutes"
                        else:
                            timeframe = raw_timeframe
                    elif "⌛" in line:
                        time = line.replace("⌛", "").strip()
                    elif "🔼" in line or "🔽" in line:
                        dir_raw = line.replace("🔼", "").replace("🔽", "").strip().lower()
                        if dir_raw == "call":
                            direction = "🔼 UP"
                        elif dir_raw == "put":
                            direction = "🔽 DOWN"
                        else:
                            direction = dir_raw.upper()
                    elif "🚦 Tend:" in line:
                        trend = line.replace("🚦 Tend:", "").strip()
                    elif "📈 Forecast:" in line:
                        forecast = line.replace("📈 Forecast:", "").strip()
                    elif "💸 Payout:" in line:
                        payout = line.replace("💸 Payout:", "").strip()

                new_msg = (
                    f"👑 <b>TANIX AI 24/7</b> 👑\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"📌 <b>Asset:</b> {asset}\n"
                    f"⏱️ <b>Timeframe:</b> {timeframe}\n"
                    f"🕒 <b>Entry Time:</b> {time}\n"
                    f"📍 <b>Direction:</b> {direction}\n"
                    f"🚦 <b>Trend:</b> {trend}\n"
                    f"📊 <b>Forecast Accuracy:</b> {forecast}\n"
                    f"💰 <b>Payout Rate:</b> {payout}\n\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"🇮🇳 <i>All times are in UTC+5:30 (India Standard Time)</i>\n\n"
                    f"💲 <b>Follow Proper Money Management.\n\n</b>"
                    f"⏳️ <b>Always Select 1 Minute time frame.</b>"
                )

                await context.bot.send_message(
                    chat_id=TARGET_CHANNEL_ID,
                    text=new_msg,
                    parse_mode='HTML'
                )
                return

            except Exception as e:
                logger.warning(f"Failed to parse flexible signal: {e}")
                return
        # ✅ WIN/LOSS message check
        elif any(kw in text.upper() for kw in ["WIN ✅", "💔 LOSS", "DOJI ⚖", "DOJI"]):
            # 🔄 Convert WIN ✅² → 💔 LOSS
            if "WIN ✅²" in text:
                text = text.replace("WIN ✅²", "💔 LOSS")

            await context.bot.send_message(
                chat_id=TARGET_CHANNEL_ID,
                text=f"<b>{text}</b>",
                parse_mode='HTML'
            )
            return

        else:
            return  # ❌ Not a signal or result, ignore

    # ✅ Check caption-based WIN/LOSS for media
    elif msg.caption and any(kw in msg.caption.upper() for kw in ["WIN ✅", "💔 LOSS", "DOJI ⚖", "DOJI"]):
        caption_text = msg.caption
        # 🔄 Convert WIN ✅² → 💔 LOSS
        if "WIN ✅²" in caption_text:
            caption_text = caption_text.replace("WIN ✅²", "💔 LOSS")

        caption = f"<b>{caption_text}</b>"

        if msg.photo:
            await context.bot.send_photo(
                chat_id=TARGET_CHANNEL_ID,
                photo=msg.photo[-1].file_id,
                caption=caption,
                parse_mode='HTML'
            )
        elif msg.video:
            await context.bot.send_video(
                chat_id=TARGET_CHANNEL_ID,
                video=msg.video.file_id,
                caption=caption,
                parse_mode='HTML'
            )
        elif msg.document:
            await context.bot.send_document(
                chat_id=TARGET_CHANNEL_ID,
                document=msg.document.file_id,
                caption=caption,
                parse_mode='HTML'
            )

    else:
        return  # ❌ Ignore everything else


# ✅ Webhook update receiver
async def handle_telegram_webhook(request):
    try:
        data = await request.json()
        update = Update.de_json(data, app.bot)
        await app.process_update(update)
    except Exception as e:
        logger.error(f"Webhook update error: {e}")
    return web.Response(text="OK")


# ✅ Health check endpoint
async def handle_health(request):
    return web.Response(text="Bot is alive! 🚀")


# ✅ Periodic ping to keep Render alive
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


# ✅ Start aiohttp web server
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


# ✅ Main function
async def main():
    global app
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(MessageHandler(filters.UpdateType.CHANNEL_POST, copy_channel_post))

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


# ✅ Entry point
if __name__ == "__main__":
    if sys.platform.startswith("win") and sys.version_info[:2] >= (3, 8):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    asyncio.run(main())

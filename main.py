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


# ✅ Copy message logic
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

                # Extract available data
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
                        else:
                            direction = dir_raw.upper()

                # ✅ Custom message format
                new_msg = (
                    f"🚀 𝗢𝗻𝗲 𝗠𝗶𝗻𝘂𝘁𝗲 𝗧𝗿𝗮𝗱𝗲 ( 𝟭 𝗠𝗜𝗡𝗧 ) 🚀\n\n"
                    f"🀄 {asset}\n"
                    f"⚡️ 𝐓𝐈𝐌𝐄 𝐙𝐎𝐍𝐄 𝐔𝐓𝐂 +𝟓:𝟑𝟎\n"
                    f"⌚ {time} ENTRY TIME\n"
                    f"{direction}\n\n"
                    f"💎 𝗣𝗿𝗲𝗺𝗶𝘂𝗺 𝗦𝗶𝗴𝗻𝗮𝗹 💎\n"
                    f"━━━━━━━━━━━━━━━\n"
                    f"💎 OFFICIAL REGISTRATION LINK 👇\n"
                    f"👉 https://broker-qx.pro/sign-up/?lid=1200739\n\n"
                    f"🎁 USE CODE: Masterguru\n"
                    f"💥 GET INSTANT 50% BONUS ON FIRST DEPOSIT!\n"
                    f"(Valid only via this official link)\n"
                    f"━━━━━━━━━━━━━━━"
                )

                await context.bot.send_message(
                    chat_id=TARGET_CHANNEL_ID,
                    text=new_msg,
                    parse_mode='HTML'
                )
                return

            except Exception as e:
                logger.warning(f"Failed to parse signal: {e}")
                return

        # ✅ WIN/LOSS message check
        elif any(kw in text.upper() for kw in ["WIN ✅", "💔 LOSS", "DOJI ⚖", "DOJI"]):
            try:
                upper_text = text.upper()

                # 🔁 Special conversion: WIN ✅¹ → ✅ MTG WIN
                if "WIN ✅¹" in text or "WIN ✅¹" in upper_text:
                    result_msg = "✅ MTG WIN"
                elif "WIN ✅" in upper_text and "¹" not in text:
                    result_msg = "✅ WIN"
                elif "LOSS" in upper_text:
                    result_msg = "💔 LOSS"
                elif "MTG WIN" in upper_text:
                    result_msg = "✅ MTG WIN"
                else:
                    result_msg = "DOJI ⚖"

                # 🔄 If consecutive loss
                if "LOSS" in upper_text and ("CONSEC" in upper_text or "2 LOSS" in upper_text):
                    final_msg = (
                        f"💔 LOSS\n"
                        f"Don’t panic, bounce back stronger 💪\n"
                        f"One loss can’t stop a future winner🔥"
                    )
                elif "LOSS" in upper_text:
                    final_msg = (
                        f"{result_msg}\n"
                        f"Relax bro 😎\n"
                        f"Next trade me plan ke sath recover kar lenge 💪"
                    )
                else:
                    final_msg = result_msg

                await context.bot.send_message(
                    chat_id=TARGET_CHANNEL_ID,
                    text=f"<b>{final_msg}</b>",
                    parse_mode='HTML'
                )
                return
            except Exception as e:
                logger.warning(f"Result message error: {e}")
                return

        else:
            return  # ❌ Not a signal or result, ignore

    # ✅ Check caption-based WIN/LOSS for media
    elif msg.caption and any(kw in msg.caption.upper() for kw in ["WIN ✅", "💔 LOSS", "DOJI ⚖", "DOJI", "MTG WIN"]):
        caption_text = msg.caption.upper()

        if "WIN ✅" in caption_text and "MTG" not in caption_text:
            result_msg = "✅ WIN"
        elif "MTG WIN" in caption_text:
            result_msg = "✅ MTG WIN"
        elif "LOSS" in caption_text:
            result_msg = "💔 LOSS"
        else:
            result_msg = "DOJI ⚖"

        # 🔄 If consecutive loss
        if "LOSS" in caption_text and ("CONSEC" in caption_text or "2 LOSS" in caption_text):
            final_caption = (
                f"💔 LOSS\n"
                f"Don’t panic, bounce back stronger 💪\n"
                f"One loss can’t stop a future winner🔥"
            )
        elif "LOSS" in caption_text:
            final_caption = (
                f"{result_msg}\n"
                f"Relax bro 😎\n"
                f"Next trade me plan ke sath recover kar lenge 💪"
            )
        else:
            final_caption = result_msg

        # ✅ Send with appropriate media type
        if msg.photo:
            await context.bot.send_photo(
                chat_id=TARGET_CHANNEL_ID,
                photo=msg.photo[-1].file_id,
                caption=f"<b>{final_caption}</b>",
                parse_mode='HTML'
            )
        elif msg.video:
            await context.bot.send_video(
                chat_id=TARGET_CHANNEL_ID,
                video=msg.video.file_id,
                caption=f"<b>{final_caption}</b>",
                parse_mode='HTML'
            )
        elif msg.document:
            await context.bot.send_document(
                chat_id=TARGET_CHANNEL_ID,
                document=msg.document.file_id,
                caption=f"<b>{final_caption}</b>",
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


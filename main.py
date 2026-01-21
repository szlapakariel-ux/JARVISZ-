import asyncio
import logging
import sys
import os
from aiohttp import web
from aiogram import Bot, Dispatcher
from config import settings
from database.db import init_db
from handlers import common, checkin, emergency, chat

# 1. Dummy Web Server (Render Requirement)
async def health_check(request):
    return web.Response(text="JARVISZ is running!")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"🌍 Web server running on port {port}")

# 2. Main Bot Logic
async def main():
    # Logging Setup
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stdout
    )
    logger = logging.getLogger(__name__)
    
    logger.info("🚀 Starting JARVISZ on Render (Clean Build)...")
    
    await init_db()
    
    # Start Web Server for Render
    await start_web_server()
    
    # Init Bot
    try:
        settings_bot_token = settings.BOT_TOKEN.get_secret_value()
        bot = Bot(token=settings_bot_token)
    except Exception as e:
         logger.error("Failed to load settings or token. Check environment variables.")
         raise e

    dp = Dispatcher()
    
    # Include Routers
    dp.include_router(common.router)
    dp.include_router(checkin.router)
    dp.include_router(emergency.router)
    dp.include_router(chat.router)
    
    logger.info("📡 Polling started...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot stopped!")

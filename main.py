import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from config import settings
from database.db import init_db
from handlers import common, checkin, emergency, chat

async def main():
    # Logging configuration
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stdout
    )
    logger = logging.getLogger(__name__)
    
    logger.info("Starting JARVISZ...")
    
    # Initialize Database
    await init_db()
    logger.info("Database initialized.")

    # Initialize Bot and Dispatcher
    try:
        bot = Bot(token=settings.BOT_TOKEN.get_secret_value())
        dp = Dispatcher()

        # Include routers
        dp.include_router(common.router)
        dp.include_router(checkin.router)
        dp.include_router(emergency.router)
        dp.include_router(chat.router)

        logger.info("Polling started...")
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        logger.info("Please ensure BOT_TOKEN is set in .env")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot stopped!")

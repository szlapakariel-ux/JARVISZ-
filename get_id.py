import asyncio
import os
from aiogram import Bot

# Manually load env for this script since config.py might fail if env is partial
TOKEN = "8589822171:AAF9IqpWi53srl8vWC4_nNBUdHXv6KdYXzk"

async def get_id():
    bot = Bot(token=TOKEN)
    try:
        print("Checking for updates...")
        updates = await bot.get_updates()
        if not updates:
            print("No updates found. Please send /start to your bot again.")
        for update in updates:
            if update.message:
                print(f"User: {update.message.from_user.first_name} | ID: {update.message.from_user.id} | Username: @{update.message.from_user.username}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(get_id())

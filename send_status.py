import asyncio
from aiogram import Bot
from config import settings

async def send_status():
    bot = Bot(token=settings.BOT_TOKEN.get_secret_value())
    user_id = settings.ADMIN_IDS[0]
    
    msg = (
        "🤖 **Reporte de Estado JARVISZ**\n\n"
        "Si viste el mensaje de 'Garmin Detectado' con tu Body Battery, ¡es que la integración fue un éxito! 🚀\n\n"
        "**¿Cómo seguimos hoy?**\n"
        "1. ¿Querés ver temas de Hosting para que yo (el bot) no me apague si cerrás la compu?\n"
        "2. ¿Querés dejarlo así y probarlo unos días?\n"
        "3. ¿Agregamos otra funcionalidad?\n\n"
        "Respondeme por acá (Telegram) o por el chat de desarrollo, como prefieras."
    )
    
    try:
        await bot.send_message(chat_id=user_id, text=msg)
        print("Mensaje enviado.")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(send_status())

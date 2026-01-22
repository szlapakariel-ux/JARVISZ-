import asyncio
from aiogram import Bot
import logging

logger = logging.getLogger(__name__)

class TimerManager:
    """
    Simple in-memory timer manager.
    WARNING: Timers will be lost if the bot restarts (Render free tier spins down).
    For critical alarms, we should use a DB + Polling, but for 'Focus Blocks' this is acceptable MVP.
    """
    
    @staticmethod
    async def set_timer(chat_id: int, duration_minutes: int, label: str, bot: Bot):
        try:
            seconds = duration_minutes * 60
            logger.info(f"Timer set for {chat_id}: {duration_minutes}m - {label}")
            
            # Send confirmation silently (or assume caller did)
            # await bot.send_message(chat_id, f"⏱️ Timer iniciado: {duration_minutes} min para '{label}'.")
            
            await asyncio.sleep(seconds)
            
            # Alarm
            await bot.send_message(chat_id, f"🔔 **TIEMPO CUMPLIDO**\n\nTerminó el bloque de: {label}.\n\n¿Cómo te fue?")
            
        except asyncio.CancelledError:
            logger.info(f"Timer cancelled for {chat_id}")
        except Exception as e:
            logger.error(f"Timer error: {e}")

    @staticmethod
    def parse_timer_tag(text: str):
        """
        Extracts <<TIMER: 15m, Label>>
        Returns: (clean_text, minutes, label)
        """
        import re
        match = re.search(r'<<TIMER:\s*(\d+)[mM]?\s*,\s*(.*?)>>', text)
        if match:
            minutes = int(match.group(1))
            label = match.group(2)
            clean_text = text.replace(match.group(0), "").strip()
            return clean_text, minutes, label
        return text, None, None

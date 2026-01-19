from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

router = Router()

@router.message(Command("sos"))
async def cmd_emergency(message: Message):
    await message.answer("⚠️ Modo Protección Activado. Respira.")

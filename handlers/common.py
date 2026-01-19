from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

router = Router()

@router.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer("Hola Ariel. Soy JARVISZ. Estoy listo para ayudarte.")

@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer("Comandos disponibles:\n/start - Iniciar\n/checkin - Registrar estado")

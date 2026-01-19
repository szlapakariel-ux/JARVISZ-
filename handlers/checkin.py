from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.future import select
from database.db import async_session
from database.models import CheckIn, User

router = Router()

# --- States ---
class MorningCheckInOnly(StatesGroup):
    waiting_for_sleep_hours = State()
    waiting_for_body_battery = State()
    waiting_for_mood = State()
    waiting_for_interoception = State() # 2 words

class EveningCheckInOnly(StatesGroup):
    waiting_for_day_score = State()
    waiting_for_stress_level = State()
    waiting_for_reflection = State()

# --- Keyboards ---
def mood_keyboard():
    buttons = [
        [InlineKeyboardButton(text="😫 1 - Agotado", callback_data="mood_1")],
        [InlineKeyboardButton(text="😕 2 - Bajo", callback_data="mood_2")],
        [InlineKeyboardButton(text="😐 3 - Normal", callback_data="mood_3")],
        [InlineKeyboardButton(text="🙂 4 - Bien", callback_data="mood_4")],
        [InlineKeyboardButton(text="😊 5 - Excelente", callback_data="mood_5")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# --- Handlers ---

@router.message(Command("checkin"))
async def cmd_checkin(message: Message, state: FSMContext):
    """Starts the check-in process manually."""
    # Logic to decide if it's morning or evening could go here.
    # For now, let's force morning flow or ask user.
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="☀️ Mañana", callback_data="start_morning")],
        [InlineKeyboardButton(text="🌙 Noche", callback_data="start_evening")]
    ])
    await message.answer("¿Qué check-in querés hacer?", reply_markup=keyboard)

@router.callback_query(F.data == "start_morning")
async def start_morning_checkin(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("⏳ **Conectando con Garmin...**")
    
    # Try to fetch Garmin data
    from services.garmin import GarminService
    garmin = GarminService()
    metrics = garmin.get_todays_metrics()
    
    if metrics and metrics.get("body_battery") is not None:
        bb = metrics["body_battery"]
        sleep_score = metrics.get("sleep_score")
        
        await state.update_data(body_battery=bb)
        if sleep_score and sleep_score != "N/A":
            await state.update_data(sleep_score=sleep_score)

        # --- GENERAR PANORAMA FÍSICO ---
        # Interpretación cualitativa en lugar de dato crudo
        intro = f"☀️ **Hola Ariel, analicé tu estado físico:**\n\n"
        
        if bb >= 75:
            panorama = "� **Motor al 100%.**\nTu cuerpo recuperó bárbaro. Tenés nafta para encarar las cosas difíciles que venís pateando. Es un día para aprovechar."
        elif bb >= 45:
            panorama = "⚖️ **Motor estable.**\nTenés energía pero no es infinita. Si te organizás, llegás bien a la noche. Ojo con el hiperfoco que te drene rápido."
        else:
            panorama = "�️ **Modo Ahorro de Energía.**\nTu cuerpo está pidiendo tregua. Hoy no es día para héroes. Hacé lo mínimo indispensable y buscá momentos de silencio."

        # Sleep context
        if sleep_score and sleep_score != "N/A" and sleep_score < 50:
            panorama += "\n_(El mal sueño de anoche te va a jugar en contra, paciencia con vos mismo)_"

        msg = f"{intro}{panorama}\n\nPara cerrar la estrategia del día:\n**¿Cómo te sentís de ánimo?**"
        
        # Skip sleep hours question if we have data, logic implies we jump to mood
        await callback.message.edit_text(msg)
        await callback.message.answer("Seleccioná tu mood:", reply_markup=mood_keyboard())
        await state.set_state(MorningCheckInOnly.waiting_for_mood)

    else:
        # Fallback to manual
        await callback.message.edit_text("☀️ **Buenos días Ariel**\n\n(No pude leer Garmin hoy)\n¿Cuántas horas dormiste anoche aprox?")
        await state.set_state(MorningCheckInOnly.waiting_for_sleep_hours)
    
    await callback.answer()

@router.callback_query(F.data == "start_evening")
async def start_evening_checkin(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("🌙 **Buenas noches Ariel**\n\nDel 1 al 10, ¿qué tan pesado se sintió el día hoy?")
    await state.set_state(EveningCheckInOnly.waiting_for_day_score)
    await callback.answer()

@router.message(MorningCheckInOnly.waiting_for_sleep_hours)
async def process_sleep_hours(message: Message, state: FSMContext):
    try:
        hours = float(message.text.replace(',', '.'))
        await state.update_data(sleep_hours=hours)
        
        # Check if we already have Body Battery from Garmin
        data = await state.get_data()
        if "body_battery" in data:
             # Skip asking for BB, jump to mood
             await message.answer("Joyal. ¿Cómo te sentís para arrancar?", reply_markup=mood_keyboard())
             await state.set_state(MorningCheckInOnly.waiting_for_mood)
        else:
             # Manual flow
             await message.answer("Oki. ¿Y cuánto dice el **Body Battery** ahora? (0-100)")
             await state.set_state(MorningCheckInOnly.waiting_for_body_battery)

    except ValueError:
        await message.answer("Ups, pasame solo el número (ej: 7 o 6.5)")

@router.message(MorningCheckInOnly.waiting_for_body_battery)
async def process_body_battery(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Solo números enteros porfa (0-100).")
        return
    
    bb = int(message.text)
    await state.update_data(body_battery=bb)
    
    await message.answer("Bien. ¿Cómo te sentís para arrancar?", reply_markup=mood_keyboard())
    await state.set_state(MorningCheckInOnly.waiting_for_mood)

@router.callback_query(MorningCheckInOnly.waiting_for_mood, F.data.startswith("mood_"))
async def process_mood(callback: CallbackQuery, state: FSMContext):
    mood_score = int(callback.data.split("_")[1])
    await state.update_data(mood_score=mood_score)
    
    await callback.message.edit_text(f"Mood: {mood_score}/5 registrado.")
    await callback.message.answer(
        "🧠 **Ejercicio de Interocepción**\n\n"
        "Definí tu estado actual en **DOS PALABRAS**:\n"
        "1. Una emoción (ej: Ansioso, Calmo, Irritado)\n"
        "2. Una sensación física (ej: Pecho cerrado, Hombros tensos, Ligero)\n\n"
        "Escribilas juntas."
    )
    await state.set_state(MorningCheckInOnly.waiting_for_interoception)
    await callback.answer()

@router.message(MorningCheckInOnly.waiting_for_interoception)
async def process_interoception(message: Message, state: FSMContext):
    text = message.text
    data = await state.get_data()
    
    # Save to DB
    async with async_session() as session:
        user_id = message.from_user.id
        words = text.split()
        emotion = words[0] if len(words) > 0 else "N/A"
        sensation = " ".join(words[1:]) if len(words) > 1 else "N/A"
        
        # Calculate Sleep Score logic handling Garmin or Manual
        if 'sleep_score' in data and data['sleep_score'] != "N/A":
            final_sleep_score = int(data['sleep_score'])
            sleep_notes = f"Garmin Score: {final_sleep_score}"
        elif 'sleep_hours' in data:
            final_sleep_score = int(data['sleep_hours'] * 10)
            sleep_notes = f"Manual Hours: {data['sleep_hours']}"
        else:
            final_sleep_score = 0
            sleep_notes = "No sleep data"

        new_checkin = CheckIn(
            user_id=user_id,
            type="morning",
            sleep_score=final_sleep_score,
            body_battery=data.get('body_battery'),
            mood_score=data.get('mood_score'),
            emotion_word=emotion,
            sensation_word=sensation,
            notes=sleep_notes
        )
        session.add(new_checkin)
        await session.commit()
    
    # Analyze with Groq (Llama 3)
    from services.groq_service import GroqService
    grok = GroqService()
    
    context = {
        "body_battery": data.get('body_battery'),
        "sleep_score": data.get('sleep_score'),
        "mood_score": data.get('mood_score'),
        "time_of_day": "Mañana"
    }
    
    # Show "Thinking..." status
    processing_msg = await message.answer("🤔 Analizando...")
    
    ai_response = await grok.analyze_checkin(context, text)
    
    await processing_msg.delete()
    await message.answer(ai_response)
    await state.clear()

# --- Evening Flows ---

@router.message(EveningCheckInOnly.waiting_for_day_score)
async def process_day_score(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Del 1 al 10, número entero.")
        return
    await state.update_data(day_score=int(message.text))
    await message.answer("¿Cuál fue tu nivel de estrés promedio hoy? (0-100, mirá el reloj si querés)")
    await state.set_state(EveningCheckInOnly.waiting_for_stress_level)

@router.message(EveningCheckInOnly.waiting_for_stress_level)
async def process_stress_level(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Número entero (0-100).")
        return
    await state.update_data(stress_level=int(message.text))
    await message.answer("¿Algo para destacar del día? (Logros, broncas, o un simple 'nada').\nSi escribís 'skip', lo salto.")
    await state.set_state(EveningCheckInOnly.waiting_for_reflection)

@router.message(EveningCheckInOnly.waiting_for_reflection)
async def process_reflection(message: Message, state: FSMContext):
    reflection = message.text
    if reflection.lower() == "skip":
        reflection = ""
    
    data = await state.get_data()
    
    async with async_session() as session:
        user_id = message.from_user.id
        new_checkin = CheckIn(
            user_id=user_id,
            type="evening",
            # Mapping day_score (1-10) to mood_score (1-5) roughly
            mood_score=max(1, min(5, round(data['day_score'] / 2))),
            body_battery=None, # Evening might not ask for BB unless relevant
            notes=f"Day Score: {data['day_score']}/10. Stress: {data['stress_level']}. Reflection: {reflection}"
        )
        session.add(new_checkin)
        await session.commit()

    # Response based on stress
    stress = data['stress_level']
    response = "😴 **Check-in nocturno guardado.**\n\n"
    
    if stress > 60:
        response += "🔴 **Día intenso.**\nEl cortisol está alto. Tratá de hacer una bajada a tierra (respiración o ducha) antes de dormir para recuperar mejor."
    elif stress < 30:
        response += "🟢 **Día tranquilo.**\nBien ahí protegiendo la energía. A descansar."
    else:
        response += "🟡 **Día normal.**\nHasta mañana Ariel."

    await message.answer(response)
    await state.clear()

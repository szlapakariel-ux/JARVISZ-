from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from services.openai_service import OpenAIService
from services.interaction_logger import InteractionLogger
from services.garmin import GarminService
from services.calendar_service import CalendarService
from services.tasks_service import TasksService
from services.chunking_service import ChunkingService
from handlers.response_utils import send_smart_response, continue_smart_response
from aiogram.types import CallbackQuery
from datetime import datetime

router = Router()
ai_service = OpenAIService()
interaction_logger = InteractionLogger()

# --- States for Confirmation Loop ---
class ActionState(StatesGroup):
    waiting_for_confirmation = State()

@router.message(ActionState.waiting_for_confirmation)
async def process_confirmation(message: Message, state: FSMContext):
    text = message.text.lower()
    data = await state.get_data()
    action = data.get('action')
    
    if text in ["si", "sí", "confirmar", "dale", "ok", "yes"]:
        if action == "create_event":
            cal = CalendarService()
            ok = cal.add_event(data['summary'], data['start_time'])
            if ok: await message.answer(f"✅ Agendado: {data['summary']}")
            else: await message.answer("❌ Error al agendar.")
            
        elif action == "delete_event":
            cal = CalendarService()
            ok = cal.delete_event(data['id'])
            if ok: await message.answer(f"🗑️ Evento '{data['summary']}' eliminado.")
            else: await message.answer("❌ Error al eliminar.")

        elif action == "create_task":
            tasks = TasksService()
            ok, msg = tasks.create_task(title=data['summary'], due_date=datetime.fromisoformat(data['start_time']) if data.get('start_time') else None)
            await message.answer(msg)
            
        elif action == "delete_task":
            tasks = TasksService()
            ok = tasks.delete_task(data['id'], data['list_id'])
            if ok: await message.answer(f"🗑️ Tarea '{data['summary']}' eliminada.")
            else: await message.answer("❌ Error al eliminar tarea.")
            
    else:
        await message.answer("🚫 Cancelado.")
    
    await state.clear()

# --- Chat History Memory ---
# Simple in-memory dict: user_id -> list of {"role": "user"|"assistant", "content": "..."}
user_histories = {}

@router.message()
async def chat_handler(message: Message, state: FSMContext):
    user_id = message.from_user.id
    text = message.text
    
    
    # 1. TRAFFIC ROUTER (GPT-4o-mini)
    # Decisions: 'casual', 'management', 'consultant'
    route_result = await ai_service.route_traffic(text)
    destination = route_result.get("destination", "consultant")
    
    print(f"DEBUG: Router Decision: {destination} for '{text}'")

    # --- ROUTE: CASUAL (Cheap) ---
    if destination == "casual":
        response = await ai_service.casual_chat(text)
        await message.answer(response)
        
        # Log Logic (Simplified)
        interaction_logger.log_interaction(text, response, {"route": "casual"}, user_id)
        return

    # --- ROUTE: MANAGEMENT (Calendar/Tasks Actions) ---
    elif destination == "management":
        processing_msg = await message.answer(f"⚙️ **Gestionando...**")
        
        # Extract Strict Data (GPT-4o-mini)
        now = datetime.now().isoformat()
        intent_json_str = await ai_service.extract_management_data(text, now)
        
        # Parse JSON
        try:
            intent = json.loads(intent_json_str)
            action = intent.get('action')
            summary = intent.get('summary')
            
            await processing_msg.delete()
            
            # Action: Create Event
            if action == "create_event":
                await state.update_data(action="create_event", summary=summary, start_time=intent.get('start_time'))
                start_pretty = intent.get('start_time', '').replace('T', ' ')
                await message.answer(f"📅 **Confirmar Agendar:**\n\n📝 {summary}\n🕒 {start_pretty}\n\n(Sí/No)")
                await state.set_state(ActionState.waiting_for_confirmation)
                return

            # Action: Delete Event
            elif action == "delete_event":
                cal = CalendarService()
                event = cal.find_next_event(summary)
                if event:
                    await state.update_data(action="delete_event", id=event['id'], summary=event['summary'])
                    start_raw = event['start'].get('dateTime', event['start'].get('date'))
                    await message.answer(f"🗑️ **Confirmar Borrar Evento:**\n\n📝 {event['summary']}\n🕒 {start_raw}\n\n(Sí/No)")
                    await state.set_state(ActionState.waiting_for_confirmation)
                else:
                    await message.answer(f"⚠️ No encontré ningún evento próximo que coincida con '{summary}'.")
                return

            # Action: Create Task
            elif action == "create_task":
                await state.update_data(action="create_task", summary=summary, start_time=intent.get('start_time'))
                await message.answer(f"📋 **Confirmar Crear Tarea:**\n\n📝 {summary}\n\n(Sí/No)")
                await state.set_state(ActionState.waiting_for_confirmation)
                return
            
            # Action: Read (Summarize with Casual Chat context)
            elif action in ["read_calendar", "read_tasks"]:
                context_str = ""
                if "calendar" in action:
                     cal = CalendarService()
                     events = cal.get_upcoming_events(7)
                     context_str += f"AGENDA: {events}\n"
                if "tasks" in action:
                     tasks = TasksService()
                     t_data = tasks.get_all_tasks()
                     context_str += f"TAREAS: {t_data}\n"
                
                # Use Casual Chat to summarize (Cheap)
                response = await ai_service.casual_chat(f"Contexto: {context_str}. Usuario: {text}")
                await message.answer(response)
                return
                
        except Exception as e:
            print(f"Management Error: {e}")
            await message.answer("⚠️ No pude entender la orden de gestión.")
            return

    # --- ROUTE: BREAKDOWN (Task Chunking) ---
    elif destination == "breakdown":
        msg_wait = await message.answer("🧩 **Desglosando tarea...**")
        chunker = ChunkingService()
        steps = await chunker.breakdown_task(text)
        
        # Format response
        response = "Acá tenés un plan de ataque rápido para no bloquearte:\n\n"
        for step in steps:
            response += f"▫️ {step}\n"
            
        response += "\n¿Arrancamos con el 1? <<BUTTONS: ¡Dale!, Mejor otra cosa>>"
        
        await msg_wait.delete()
        await send_smart_response(message, response, state)
        interaction_logger.log_interaction(text, response, {"route": "breakdown"}, user_id)
        return

    # --- ROUTE: CONSULTANT (Heavy/Assistant) ---
    # This is for Health, Advice, Deep Analysis, Document Search (RAG)
    else:
        # Fetch Context (Only if needed)
        status_parts = []
        garmin_data = None
        calendar_events = None
        tasks_data = None

        msg_wait = await message.answer("🧠 **Conectando con el Especialista...**")

        # Heuristic: Check triggers to avoid API calls if obviously not needed? 
        # Actually, for "Consultant", we assume we need context. But we can be smart.
        # Let's fetch basic context always for the Assistant to be "aware".
        
        # 1. Garmin (Always useful for 'how am I?')
        try:
            garmin = GarminService()
            garmin_data = garmin.get_todays_metrics()
            status_parts.append("Biometría")
        except: pass
        
        # 2. Calendar (Only if mentioned or broad context needed)
        # For simplicity/robustness, we fetch it.
        try:
            cal = CalendarService()
            calendar_events = cal.get_upcoming_events(3) # Reduce to 3 days to save tokens?
            status_parts.append("Agenda")
        except: pass

        # 3. Call Assistant API
        response = await ai_service.chat(
            user_input=text, 
            garmin_data=garmin_data, 
            calendar_events=calendar_events, 
            tasks_data=tasks_data, 
            user_id=user_id
        )
        
        await msg_wait.delete()
        # USE SMART RESPONSE (Consolidacion Rules)
        await send_smart_response(message, response, state)
        
        interaction_logger.log_interaction(text, response, {"route": "consultant"}, user_id)

# --- SMART CALLBACK HANDLERS ---
@router.callback_query(F.data == "smart_page")
async def on_smart_page(callback: CallbackQuery, state: FSMContext):
    await continue_smart_response(callback, state)

@router.callback_query(F.data.startswith("smart_act:"))
async def on_smart_action(callback: CallbackQuery, state: FSMContext):
    action = callback.data.split(":")[1]
    
    # --- HANDLING CONSOLIDATED ACTIONS ---
    # These are standard buttons the LLM might consistently use due to instructions
    
    if action.lower() in ["pausa", "descanso", "frenar"]:
        # Frustration Protocol: Offer breathing or silence
        await callback.message.answer(
            "🛑 **Protocolo de Pausa Activado**\n\n"
            "Soltá el teléfono. Respirá hondo 3 veces.\n"
            "JARVISZ entra en silencio por 5 minutos.\n\n"
            "(Si necesitás volver antes, escribí 'volver')"
        )
        # Here we could set a state to ignore messages or set a timer
        from handlers.timer_utils import TimerManager
        await TimerManager.set_timer(callback.message.chat.id, 5, "Pausa de Emergencia", callback.message.bot)
        
    elif action.lower() in ["micro-tarea", "algo fácil", "microtarea"]:
        # Dopamine Hack: Give trivial task
        tasks = [
            "Tomá un vaso de agua.",
            "Estirá los brazos arriba por 10 segundos.",
            "Tirá un papel a la basura.",
            "Abrí y cerrá los ojos fuerte 3 veces."
        ]
        import random
        t = random.choice(tasks)
        await callback.message.answer(f"✨ **Micro-Misión:**\n\n{t}\n\nSi la hacés, ganás.", reply_markup=None)
        
    elif action.lower() in ["cambiar de tema", "otra cosa"]:
        # Reset context
        await state.clear()
        await callback.message.answer("🔄 **Tema reiniciado.**\n\n¿En qué nos enfocamos ahora?")
        
    else:
        # Generic fallback for other dynamic buttons LLM might invent
        # We treat it as user saying that phrase
        await callback.message.answer(f"👍 **{action}**")
        # Reuse chat logic to process this as a message?
        # Ideally yes, but maybe too deep recursion.
        # For now, just acknowledge.

    await callback.answer()


from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from services.openai_service import OpenAIService
from services.interaction_logger import InteractionLogger
from services.garmin import GarminService
from services.calendar_service import CalendarService
from services.tasks_service import TasksService
import json
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
    text = message.text.lower()
    
    # Initialize history if new
    if user_id not in user_histories:
        user_histories[user_id] = []
    
    # --- 1. INTENT DETECTION (Regex/Keywords heuristic first) ---
    intent_triggers = ["agendar", "borrar", "eliminar", "cancelar", "crear recordatorio"]
    
    if any(w in text for w in intent_triggers) and len(text.split()) > 2 and "?" not in text:
        processing_msg = await message.answer("🧠 **Procesando solicitud...**")
        
        from datetime import datetime
        now = datetime.now().isoformat()
        
        try:
            # Use OpenAI for intent analysis
            json_str = await ai_service.analyze_intent(message.text, now)
            
            # Clean JSON
            json_str = json_str.replace("```json", "").replace("```", "").strip()
            if "{" in json_str: 
                json_str = json_str[json_str.find("{"):json_str.rfind("}")+1]
            
            intent = json.loads(json_str)
            action = intent.get('action')
            summary = intent.get('summary')
            
            await processing_msg.delete()
            
            if action == "create_event":
                await state.update_data(action="create_event", summary=summary, start_time=intent.get('start_time'))
                start_pretty = intent['start_time'].replace('T', ' ')
                await message.answer(f"📅 **Confirmar Agendar:**\n\n📝 {summary}\n🕒 {start_pretty}\n\n(Sí/No)")
                await state.set_state( ActionState.waiting_for_confirmation )
                return

            elif action == "delete_event":
                # Need to find it first
                cal = CalendarService()
                event = cal.find_next_event(summary)
                if event:
                    await state.update_data(action="delete_event", id=event['id'], summary=event['summary'])
                    # Format time
                    start_raw = event['start'].get('dateTime', event['start'].get('date'))
                    await message.answer(f"🗑️ **Confirmar Borrar Evento:**\n\n📝 {event['summary']}\n🕒 {start_raw}\n\n(Sí/No)")
                    await state.set_state(ActionState.waiting_for_confirmation)
                else:
                    await message.answer(f"⚠️ No encontré ningún evento próximo que coincida con '{summary}'.")
                return

            elif action == "create_task":
                await state.update_data(action="create_task", summary=summary, start_time=intent.get('start_time'))
                await message.answer(f"📋 **Confirmar Crear Tarea:**\n\n📝 {summary}\n\n(Sí/No)")
                await state.set_state(ActionState.waiting_for_confirmation)
                return

            elif action == "delete_task":
                tasks = TasksService()
                task, list_id = tasks.find_task(summary)
                if task:
                    await state.update_data(action="delete_task", id=task['id'], list_id=list_id, summary=task['title'])
                    await message.answer(f"🗑️ **Confirmar Borrar Tarea:**\n\n📝 {task['title']}\n\n(Sí/No)")
                    await state.set_state(ActionState.waiting_for_confirmation)
                else:
                    await message.answer(f"⚠️ No encontré ninguna tarea pendiente que coincida con '{summary}'.")
                return
                
        except Exception as e:
            # Fallback
            print(f"DEBUG: Intent Analysis Error: {e}")
            pass

    # --- 2. FALLBACK TO STANDARD CHAT FLOW ---

    # Expanded Keywords
    body_triggers = ["chequeá", "chequea", "cuerpo", "escaner", "realidad", "estrés", "stress", "ansiedad", "abrumado", "scan", "signos"]
    
    calendar_triggers = [
        "agenda", "calendario", "hoy", "mañana", "semana", "mes", 
        "tengo", "reunión", "compromiso", "turno", "cita", "médico", 
        "dentista", "gimnasio", "cumpleaños", "vacaciones", "feriado",
        "lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo",
        "cuándo", "resumen"
    ]
    
    tasks_triggers = ["tareas", "pendientes", "hacer", "to-do", "todo", "lista", "comprar"]
    
    garmin_data = None
    calendar_events = None
    tasks_data = None
    
    status_parts = []
    
    # Check Body
    if any(word in text for word in body_triggers):
        status_parts.append("sensores biométricos")
        try:
            garmin = GarminService()
            garmin_data = garmin.get_todays_metrics()
        except Exception:
            garmin_data = None
            
    # DEBUG LOGS
    print(f"DEBUG: Processing message: '{text}'")
    
    # Check Calendar
    is_direct_calendar_request = False
    if any(word in text for word in calendar_triggers) or "agenda" in text or "semana" in text:
        is_direct_calendar_request = True
        status_parts.append("agenda")
        try:
            cal = CalendarService()
            calendar_events = cal.get_upcoming_events(7) 
        except Exception as e:
            calendar_events = f"Error: {e}"
            
    # Check Tasks
    if any(word in text for word in tasks_triggers):
        status_parts.append("tareas")
        try:
            tasks = TasksService()
            tasks_data = tasks.get_all_tasks()
        except:
            tasks_data = None
            
    # Get User History
    history = user_histories[user_id]

    # UI Feedback
    if status_parts:
        if is_direct_calendar_request and calendar_events and "Error" not in str(calendar_events) and not garmin_data:
             # Fast path for pure calendar requests if no complexity
             # But let's let AI summarize if we have multiple things, or just send if simple.
             pass

        msg = await message.answer(f"🔍 **Revisando {', '.join(status_parts)}...**")
        
        # Call OpenAI
        response = await ai_service.chat(message.text, garmin_data, calendar_events, tasks_data, history)
        
        await msg.delete()
        await message.answer(response)
    else:
        # Normal chat
        response = await ai_service.chat(message.text, None, None, None, history)
        await message.answer(response)
    
    # Update History if we continued
    history.append({"role": "user", "content": message.text})
    history.append({"role": "assistant", "content": response})
    if len(history) > 10:
        history = history[-10:]
    user_histories[user_id] = history
    
    # Log
    interaction_logger.log_interaction(
        user_message=message.text,
        bot_response=response,
        context_data={ "garmin": garmin_data, "calendar": calendar_events, "tasks": tasks_data },
        user_id=message.from_user.id
    )

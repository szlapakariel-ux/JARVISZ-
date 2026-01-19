import logging
from openai import AsyncOpenAI
from config import settings
from datetime import datetime
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

class OpenAIService:
    def __init__(self):
        try:
            self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY.get_secret_value())
            self.model = "gpt-4o"  # Or "gpt-3.5-turbo" if preferred for cost
            logger.info("OpenAI Service initialized.")
        except Exception as e:
            logger.error(f"Failed to init OpenAI: {e}")
            self.client = None

    async def _call_gpt(self, messages: list, temperature: float = 0.7) -> str:
        if not self.client:
            return "Error: OpenAI no inicializado."
            
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"OpenAI API Error: {e}")
            return "Lo siento, tuve un problema conectando con mi cerebro central (OpenAI)."

    async def chat(self, user_input: str, garmin_data: dict = None, calendar_events: str = None, tasks_data: str = None, history: list = None) -> str:
        # 1. Prepare Base Context
        tz_argentina = ZoneInfo("America/Argentina/Buenos_Aires")
        now = datetime.now(tz_argentina)
        dia_semana = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"][now.weekday()]
        fecha = now.strftime("%d/%m/%Y %H:%M")
        
        system_prompt = f"""
        Sos JARVISZ, un asistente personal emocional y práctico para Ariel (50 años, TDAH, Duelo reciente).
        
        CONTEXTO ACTUAL:
        - Fecha/Hora: {dia_semana} {fecha}
        - Ubicación: Argentina (GMT-3)
        
        TU PERSONALIDAD:
        - Empático pero directo (no des vueltas).
        - Usá emojis para dar tono.
        - Si es tarde (noche), sugerí descanso.
        - Si es mañana, sé motivador pero suave.
        - Conocés el contexto de Ariel: necesita ayuda ejecutiva (priorizar) y validación emocional.
        
        """
        
        # 2. Add Tools Context
        if garmin_data:
            system_prompt += f"\n[DATOS BIOMÉTRICOS HOY]:\nBody Battery: {garmin_data.get('body_battery')}\nEstrés: {garmin_data.get('stress_avg')}\nSueño: {garmin_data.get('sleep_score')}\n(Usá esto para validar su nivel de energía real)."
            
        if calendar_events:
            system_prompt += f"\n[AGENDA PRÓXIMA]:\n{calendar_events}\n"
            
        if tasks_data:
            system_prompt += f"\n[TAREAS PENDIENTES]:\n{tasks_data}\n"

        # 3. Construct Messages
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add history (last few messages)
        if history:
            # History is expected to be list of {"role": "user"|"assistant", "content": "..."}
            # We strictly filter to valid roles for OpenAI
            valid_msgs = [m for m in history if m.get("role") in ["user", "assistant"]]
            messages.extend(valid_msgs)
            
        # Add current user input
        messages.append({"role": "user", "content": user_input})
        
        return await self._call_gpt(messages)

    async def analyze_checkin(self, context_data: dict, user_input: str) -> str:
        """
        Analyzes the morning/evening check-in data to provide feedback.
        """
        system_prompt = f"""
        Sos JARVISZ. Ariel acaba de hacer su check-in.
        
        DATOS DE CONTEXTO:
        - Body Battery: {context_data.get('body_battery', 'N/A')}
        - Sueño: {context_data.get('sleep_score', 'N/A')}
        - Mood: {context_data.get('mood_score', 'N/A')}/5
        - Momento: {context_data.get('time_of_day', 'N/A')}
        
        INPUT DE ARIEL (Sobre cómo se siente):
        "{user_input}"
        
        TU OBJETIVO:
        1. Validar lo que siente (empatía).
        2. Relacionarlo con los datos (ej: "Con razón te sentís así, dormiste poco").
        3. Dar un consejo micro-accionable para el momento del día.
        4. MAXIMO 3 oraciones. Corto y al pie.
        """
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input or "No escribí nada extra, basate en los datos."}
        ]
        return await self._call_gpt(messages)

    async def analyze_intent(self, user_input: str, now_iso: str) -> str:
        """
        Specialized method for the intent classification logic used in chat.py
        Returns a JSON string.
        """
        system_prompt = f"""
        Sos el modulo de gestión de JARVISZ. HOY: {now_iso}.
        Tu tarea es clasificar la intención y extraer datos en JSON. STRICT JSON ONLY.
        
        ACCIONES:
        - "create_event": Agendar reunion/turno en calendario.
        - "delete_event": Borrar evento.
        - "create_task": Crear tarea.
        - "delete_task": Borrar tarea.
        - "none": Si no es comando de gestión.
        
        JSON FORMAT:
        {{ "action": "...", "summary": "...", "start_time": "2026-MM-DDTHH:MM:SS" (or null) }}
        """
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input}
        ]
        
        # Use lower temperature for deterministic logic
        return await self._call_gpt(messages, temperature=0.1)

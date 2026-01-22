import logging
import asyncio
from openai import AsyncOpenAI
from config import settings
from datetime import datetime
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

class OpenAIService:
    def __init__(self):
        try:
            self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY.get_secret_value())
            self.assistant_id = settings.OPENAI_ASSISTANT_ID
            self.threads = {} # In-memory: user_id -> thread_id
            logger.info(f"OpenAI Assistant Service initialized. Agent ID: {self.assistant_id}")
        except Exception as e:
            logger.error(f"Failed to init OpenAI: {e}")
            self.client = None

    async def _get_or_create_thread(self, user_id: int) -> str:
        if user_id in self.threads:
            return self.threads[user_id]
        
        try:
            thread = await self.client.beta.threads.create()
            self.threads[user_id] = thread.id
            return thread.id
        except Exception as e:
            logger.error(f"Error creating thread: {e}")
            raise

    async def chat(self, user_input: str, garmin_data: dict = None, calendar_events: str = None, tasks_data: str = None, history: list = None, user_id: int = None) -> str:
        """
        Uses OpenAI Assistants API.
        'history' argument is ignored as Threads manage history now.
        'user_id' is required to map to a Thread.
        """
        if not self.client:
            return "Error: OpenAI no disponible."
        
        if not user_id:
            return "Error: user_id requerido para Assistant API."

        try:
            # 1. Get Thread
            thread_id = await self._get_or_create_thread(user_id)
            
            # 2. Add Message
            await self.client.beta.threads.messages.create(
                thread_id=thread_id,
                role="user",
                content=user_input
            )
            
            # 3. Prepare Dynamic Context (Instructions update)
            tz_argentina = ZoneInfo("America/Argentina/Buenos_Aires")
            now = datetime.now(tz_argentina)
            
            # --- CONSOLIDACIÓN REAL RULES ---
            consolidacion_rules = """
            REGLAS NO NEGOCIABLES ("CONSOLIDACIÓN"):
            1. ESTRUCTURA (4 PASOS):
               - Apertura: Saludo breve + "Soy tu IA...".
               - Intención: ¿Qué necesita? (Usa botones).
               - Acción: Ayuda concreta.
               - Cierre: Resumen + Refuerzo.
            2. FORMATO:
               - Usa MÁXIMO 3 oraciones por párrafo.
               - SIEMPRE ofrece botones para acciones siguientes.
               - SINTAXIS BOTONES: Al final de tu respuesta, agrega: <<BUTTONS: Etiqueta 1, Etiqueta 2>>.
            3. HERRAMIENTAS EJECUTIVAS (MODO TDAH):
               - CEGUERA TEMPORAL: Si el usuario va a hacer algo, OFRECE UN TIMER.
                 SINTAXIS TIMER: <<TIMER: 15, Nombre del bloque>> (donde 15 son minutos).
               - PARÁLISIS: Si la tarea parece grande, OFRECE DESGLOSARLA en pasos pequeños (Chunking).
               - NO preguntes "¿Qué quieres hacer?" en texto si puedes poner botones.
            4. TONO:
               - Si detectas frustración: Valida -> Ofrece Salida (Pausa/Micro-tarea).
            """

            context_str = f"CONTEXTO ACTUAL: {now.strftime('%d/%m/%Y %H:%M')} (Argentina).\n{consolidacion_rules}\n"
            
            if garmin_data:
                context_str += f"[BIOMETRÍA]: BB:{garmin_data.get('body_battery')} Stress:{garmin_data.get('stress_avg')}\n"
            if calendar_events:
                 context_str += f"[AGENDA]: {calendar_events}\n"
            if tasks_data:
                 context_str += f"[TAREAS]: {tasks_data}\n"

            # 4. Run Assistant
            run = await self.client.beta.threads.runs.create(
                thread_id=thread_id,
                assistant_id=self.assistant_id,
                additional_instructions=context_str
            )
            
            # 5. Poll for completion
            while True:
                run_status = await self.client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)
                if run_status.status == 'completed':
                    break
                elif run_status.status in ['failed', 'cancelled', 'expired']:
                    return "Algo salió mal procesando tu mensaje."
                await asyncio.sleep(1) # Wait 1s
            
            # 6. Get Messages
            messages = await self.client.beta.threads.messages.list(
                thread_id=thread_id,
                limit=1
            )
            
            # Return the latest message from assistant
            if messages.data:
                return messages.data[0].content[0].text.value
            return "..."

        except Exception as e:
            logger.error(f"Assistant Chat Error: {e}")
            return f"Hubo un error con el Agente: {e}"

    async def analyze_checkin(self, context_data: dict, user_input: str) -> str:
        """
        Uses standard Chat Completions for fast, specialized analysis 
        (avoiding Thread pollution or Agent personality overrides).
        """
        system_prompt = f"""
        Sos JARVISZ. Ariel acaba de hacer su check-in.
        DATOS:
        - BB: {context_data.get('body_battery', 'N/A')}
        - Sueño: {context_data.get('sleep_score', 'N/A')}
        - Mood: {context_data.get('mood_score', 'N/A')}/5
        
        INPUT: "{user_input}"
        
        OBJETIVO:
        1. Validar emoción.
        2. Relacionar con datos.
        3. Consejo corto.
        Max 3 oraciones.
        """
        try:
             response = await self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_input or "Datos"}
                ]
             )
             return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Checkin Analysis Error: {e}")
            return "Recibido. (Error analizando)"

    async def route_traffic(self, user_input: str) -> dict:
        """
        TRAFFIC CONTROLLER (ROUTER).
        Uses gpt-4o-mini (Cheap) to decide who handles the message.
        Returns JSON: {"destination": "casual"|"management"|"consultant", "confidence": float}
        """
        system_prompt = """
        Sos el Router de JARVISZ. Tu única tarea es clasificar el mensaje del usuario para ahorrar costos.
        
        DESTINOS:
        1. 'casual': Saludos, agradecimientos, chistes, preguntas simples ("Hola", "Gracias", "¿Estás ahí?").
        2. 'management': El usuario quiere AGENDAR, BORRAR o CONSULTAR su calendario/tareas ("Agendar mañana", "Qué tengo hoy", "Borrar tarea").
        3. 'breakdown': El usuario pide ayuda para empezar algo difícil, quiere dividir una tarea o se siente bloqueado ("Ayudame a limpiar", "Dividime esta tarea", "No sé por dónde empezar").
        4. 'consultant': El usuario pide consejos de salud, análisis profundo, preguntas sobre documentos/PDFs o "Chequeo de Realidad".
        
        Responded ONLY with JSON: {"destination": "..."}
        """
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_input}
                ],
                temperature=0.0
            )
            import json
            content = response.choices[0].message.content.replace("```json", "").replace("```", "").strip()
            return json.loads(content)
        except Exception as e:
            logger.error(f"Router Error: {e}")
            return {"destination": "consultant"} # Default to powerful agent if unsure

    async def casual_chat(self, user_input: str) -> str:
        """
        CASUAL SPECIALIST.
        Uses gpt-4o-mini (Cheap) for small talk.
        """
        system_prompt = "Sos JARVISZ, un asistente amable y breve. Respondé con onda pero corto."
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_input}
                ]
            )
            return response.choices[0].message.content
        except Exception as e:
            return "Hola! (Error simple)"

    async def extract_management_data(self, user_input: str, now_iso: str) -> str:
        """
        MANAGEMENT SPECIALIST (JSON Extractor).
        Uses gpt-4o-mini to parse calendar/task intent.
        """
        system_prompt = f"""
        Sos el Especialista de Gestión. HOY: {now_iso}.
        Extraer datos JSON para Calendar/Tasks.
        
        ACCIONES: "create_event", "delete_event", "create_task", "delete_task", "read_calendar", "read_tasks".
        
        JSON: {{ "action": "...", "summary": "...", "start_time": "..." }}
        """
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_input}
                ],
                temperature=0.1
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Intent Error: {e}")
            return "{}"

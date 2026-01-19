import google.generativeai as genai
from config import settings
import logging
from datetime import datetime
from zoneinfo import ZoneInfo
import asyncio
import time

logger = logging.getLogger(__name__)

class GeminiService:
    def __init__(self):
        try:
            genai.configure(api_key=settings.GEMINI_API_KEY.get_secret_value())
            self.model = genai.GenerativeModel('gemini-flash-latest')
            logger.info("Gemini initialized.")
        except Exception as e:
            logger.error(f"Failed to init Gemini: {e}")
            self.model = None
    
    async def _call_with_retry(self, prompt: str, max_retries: int = 3):
        """
        Llama a Gemini con retry automático en caso de rate limiting
        """
        for attempt in range(max_retries):
            try:
                response = await self.model.generate_content_async(prompt)
                return response.text
            except Exception as e:
                error_str = str(e)
                
                # Si es rate limit (429), esperar y reintentar
                if "429" in error_str or "quota" in error_str.lower():
                    if attempt < max_retries - 1:
                        wait_time = (2 ** attempt) * 5  # Exponential backoff: 5s, 10s, 20s
                        logger.warning(f"Rate limit hit. Waiting {wait_time}s before retry {attempt + 1}/{max_retries}")
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        logger.error(f"Max retries reached. Rate limit persists.")
                        return "Estoy teniendo problemas técnicos (demasiadas consultas). Esperá un minuto y volvé a intentar."
                
                # Si es otro error, loguear y devolver mensaje
                logger.error(f"Gemini error: {e}")
                return "No te pude entender, perdón."
        
        return "Error inesperado. Intentá de nuevo."

    async def analyze_checkin(self, context_data: dict, user_input: str) -> str:
        if not self.model:
            return "Lo siento, mi cerebro IA no está disponible hoy. :("
        
        # Obtener fecha y hora actual en Argentina
        tz_argentina = ZoneInfo("America/Argentina/Buenos_Aires")
        now = datetime.now(tz_argentina)
        
        # Formatear información temporal
        dias_semana = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
        dia_semana = dias_semana[now.weekday()]
        fecha_formateada = now.strftime("%d/%m/%Y")
        hora_formateada = now.strftime("%H:%M")
        
        # Determinar momento del día
        hora = now.hour
        if 5 <= hora < 12:
            momento_dia = "mañana"
        elif 12 <= hora < 19:
            momento_dia = "tarde"
        else:
            momento_dia = "noche"
        
        prompt = f"""
        Sos JARVISZ, un asistente personal para Ariel (50 años, TDAH, Duelo reciente).
        Tu objetivo: Ayudarlo a regular energía y emociones.
        
        CONTEXTO TEMPORAL:
        - Fecha: {dia_semana} {fecha_formateada}
        - Hora: {hora_formateada} ({momento_dia})
        
        Datos de Contexto:
        - Body Battery: {context_data.get('body_battery', 'N/A')}
        - Sueño: {context_data.get('sleep_score', 'N/A')}
        - Mood: {context_data.get('mood_score', 'N/A')}
        - Hora: {context_data.get('time_of_day', momento_dia)}
        
        Input del Usuario: "{user_input}"
        
        Instrucciones:
        1. Analizá los datos y lo que dijo Ariel.
        2. Respondé en 2-3 oraciones máximo.
        3. Sé empático pero directo. Usá emojis.
        4. Si la batería está baja, sugerí descanso. Si está alta, sugerí aprovechar el día.
        5. Jamás uses frases trilladas de autoayuda. Hablá como un amigo cercano que conoce el dolor de Ariel.
        6. Considerá el momento del día: si es noche, no sugieras actividades energéticas.
        """
        try:
            return await self._call_with_retry(prompt)
        except Exception as e:
            print(f"DEBUG GEMINI ERROR: {e}")
            logger.error(f"Gemini error details: {e}")
            return f"Tuve un error pensando: {e}"

    async def chat(self, user_input: str, garmin_data: dict = None, calendar_events: str = None, tasks_data: str = None) -> str:
        if not self.model:
            return "Estoy desconectado del cerebro central."
        
        # Obtener fecha y hora actual en Argentina
        tz_argentina = ZoneInfo("America/Argentina/Buenos_Aires")
        now = datetime.now(tz_argentina)
        
        # Formatear información temporal
        dias_semana = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
        dia_semana = dias_semana[now.weekday()]
        fecha_formateada = now.strftime("%d/%m/%Y")
        hora_formateada = now.strftime("%H:%M")
        
        # Determinar momento del día
        hora = now.hour
        if 5 <= hora < 12:
            momento_dia = "mañana"
        elif 12 <= hora < 19:
            momento_dia = "tarde"
        else:
            momento_dia = "noche"
            
        system_instruction = "Respondé corto, empático y como amigo."
        context_str = f"""
        CONTEXTO TEMPORAL (IMPORTANTE):
        - Fecha: {dia_semana} {fecha_formateada}
        - Hora: {hora_formateada} ({momento_dia})
        - Zona horaria: Argentina (GMT-3)
        
        IMPORTANTE: Usá esta información para contextualizar tus respuestas. Por ejemplo:
        - Si es noche/tarde del domingo, NO preguntes "¿Cómo arrancamos hoy?"
        - Si es tarde/noche, NO uses saludos de mañana
        - Si es fin de semana, ajustá tus sugerencias
        - Si es muy tarde, considerá sugerir descanso
        """
        
        # Load Knowledge Base
        try:
             with open("knowledge_base.md", "r", encoding="utf-8") as f:
                 kb_content = f.read()
        except:
             kb_content = "Perfil de Ariel simplificado."

        if garmin_data:
            # Reality Check Mode
            system_instruction += """
            IMPORTANTE: El usuario está pidiendo un 'Chequeo de Realidad'.
            Compará lo que el usuario DICE sentir con los DATOS REALES de su cuerpo.
            - Si el estrés/HR son altos -> Validá que su cuerpo está reaccionando.
            - Si los números son bajos/normales -> Sugerí gentilmente que puede ser algo mental/ansiedad y no físico.
            Usá los datos para fundamentar tu consejo.
            """
            context_str += f"""
            DATOS EN TIEMPO REAL (Garmin):
            - Body Battery: {garmin_data.get('body_battery', 'N/A')} (Reserva de energía)
            - Estrés Promedio: {garmin_data.get('stress_avg', 'N/A')} (0-100)
            - HR Reposo: {garmin_data.get('resting_hr', 'N/A')}
            - Sueño: {garmin_data.get('sleep_score', 'N/A')}
            """
            
        if calendar_events:
            context_str += f"""
            AGENDA DE HOY (Google Calendar):
            {calendar_events}
            (Si la agenda está muy cargada y la Body Battery es baja, sugerí priorizar o cancelar cosas).
            """

        if tasks_data:
            context_str += f"""
            TAREAS PENDIENTES (Google Tasks):
            {tasks_data}
            
            IMPORTANTE sobre las tareas:
            - Si hay tareas vencidas, mencionalo con empatía (sin juzgar)
            - Si pregunta qué tiene que hacer, priorizá según urgencia y energía disponible
            - Si la Body Battery es baja, sugerí posponer tareas no urgentes
            - Ayudá a priorizar: ¿qué es realmente importante HOY?
            """

        prompt = f"""
        CONTEXTO VITAL (ESTO ES LA VERDAD ABSOLUTA DE ARIEL):
        {kb_content}
        ----------------------------------------------------
        
        {context_str}
        
        Usuario: "{user_input}"
        
        {system_instruction}
        """
        try:
            return await self._call_with_retry(prompt)
        except Exception as e:
            logger.error(f"Gemini chat error: {e}")
            return "No te pude entender, perdón."


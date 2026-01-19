import httpx
from config import settings
import logging
from datetime import datetime
from zoneinfo import ZoneInfo
import asyncio
import json

logger = logging.getLogger(__name__)

class GrokService:
    def __init__(self):
        self.api_key = settings.GROK_API_KEY.get_secret_value()
        self.base_url = "https://api.x.ai/v1"
        self.model = "grok-beta"  # Modelo más rápido y económico
        logger.info("Grok initialized.")
    
    async def _call_with_retry(self, messages: list, max_retries: int = 3):
        """
        Llama a Grok con retry automático
        """
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        payload = {
            "messages": messages,
            "model": self.model,
            "stream": False,
            "temperature": 0.7
        }
        
        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(
                        f"{self.base_url}/chat/completions",
                        headers=headers,
                        json=payload
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        return data['choices'][0]['message']['content']
                    elif response.status_code == 429:
                        # Rate limit
                        if attempt < max_retries - 1:
                            wait_time = (2 ** attempt) * 5
                            logger.warning(f"Rate limit hit. Waiting {wait_time}s before retry {attempt + 1}/{max_retries}")
                            await asyncio.sleep(wait_time)
                            continue
                        else:
                            return "Estoy teniendo problemas técnicos (demasiadas consultas). Esperá un minuto y volvé a intentar."
                    else:
                        logger.error(f"Grok API error: {response.status_code} - {response.text}")
                        return "No te pude entender, perdón."
                        
            except Exception as e:
                logger.error(f"Grok error: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2)
                    continue
                return "No te pude entender, perdón."
        
        return "Error inesperado. Intentá de nuevo."
    
    async def analyze_checkin(self, context_data: dict, user_input: str) -> str:
        # Obtener fecha y hora actual
        tz_argentina = ZoneInfo("America/Argentina/Buenos_Aires")
        now = datetime.now(tz_argentina)
        
        dias_semana = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
        dia_semana = dias_semana[now.weekday()]
        fecha_formateada = now.strftime("%d/%m/%Y")
        hora_formateada = now.strftime("%H:%M")
        
        hora = now.hour
        if 5 <= hora < 12:
            momento_dia = "mañana"
        elif 12 <= hora < 19:
            momento_dia = "tarde"
        else:
            momento_dia = "noche"
        
        system_message = f"""Sos JARVISZ, un asistente personal para Ariel (50 años, TDAH, Duelo reciente).
Tu objetivo: Ayudarlo a regular energía y emociones.

CONTEXTO TEMPORAL:
- Fecha: {dia_semana} {fecha_formateada}
- Hora: {hora_formateada} ({momento_dia})

Datos de Contexto:
- Body Battery: {context_data.get('body_battery', 'N/A')}
- Sueño: {context_data.get('sleep_score', 'N/A')}
- Mood: {context_data.get('mood_score', 'N/A')}

Instrucciones:
1. Analizá los datos y lo que dijo Ariel.
2. Respondé en 2-3 oraciones máximo.
3. Sé empático pero directo. Usá emojis.
4. Si la batería está baja, sugerí descanso. Si está alta, sugerí aprovechar el día.
5. Jamás uses frases trilladas de autoayuda. Hablá como un amigo cercano que conoce el dolor de Ariel.
6. Considerá el momento del día: si es noche, no sugieras actividades energéticas."""

        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_input}
        ]
        
        return await self._call_with_retry(messages)
    
    async def chat(self, user_input: str, garmin_data: dict = None, calendar_events: str = None, tasks_data: str = None) -> str:
        # Obtener fecha y hora
        tz_argentina = ZoneInfo("America/Argentina/Buenos_Aires")
        now = datetime.now(tz_argentina)
        
        dias_semana = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
        dia_semana = dias_semana[now.weekday()]
        fecha_formateada = now.strftime("%d/%m/%Y")
        hora_formateada = now.strftime("%H:%M")
        
        hora = now.hour
        if 5 <= hora < 12:
            momento_dia = "mañana"
        elif 12 <= hora < 19:
            momento_dia = "tarde"
        else:
            momento_dia = "noche"
        
        # Load Knowledge Base
        try:
            with open("knowledge_base.md", "r", encoding="utf-8") as f:
                kb_content = f.read()
        except:
            kb_content = "Perfil de Ariel simplificado."
        
        context_parts = [f"""CONTEXTO TEMPORAL (IMPORTANTE):
- Fecha: {dia_semana} {fecha_formateada}
- Hora: {hora_formateada} ({momento_dia})
- Zona horaria: Argentina (GMT-3)

IMPORTANTE: Usá esta información para contextualizar tus respuestas."""]
        
        if garmin_data:
            context_parts.append(f"""DATOS EN TIEMPO REAL (Garmin):
- Body Battery: {garmin_data.get('body_battery', 'N/A')}
- Estrés Promedio: {garmin_data.get('stress_avg', 'N/A')}
- HR Reposo: {garmin_data.get('resting_hr', 'N/A')}
- Sueño: {garmin_data.get('sleep_score', 'N/A')}""")
        
        if calendar_events:
            context_parts.append(f"""AGENDA DE HOY (Google Calendar):
{calendar_events}""")
        
        if tasks_data:
            context_parts.append(f"""TAREAS PENDIENTES (Google Tasks):
{tasks_data}""")
        
        system_message = f"""CONTEXTO VITAL (ESTO ES LA VERDAD ABSOLUTA DE ARIEL):
{kb_content}

{chr(10).join(context_parts)}

Respondé corto, empático y como amigo."""

        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_input}
        ]
        
        return await self._call_with_retry(messages)

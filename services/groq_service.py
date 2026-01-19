from config import settings
import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from groq import AsyncGroq
import json

logger = logging.getLogger(__name__)

class GroqService:
    def __init__(self):
        try:
            self.client = AsyncGroq(
                api_key=settings.GROQ_API_KEY.get_secret_value()
            )
            # Usamos Llama 3 para un buen balance de velocidad y calidad
            self.model = "llama-3.3-70b-versatile" 
            logger.info("Groq initialized (Llama 3).")
        except Exception as e:
            logger.error(f"Failed to init Groq: {e}")
            self.client = None
    
    async def _call_with_retry(self, messages: list, max_retries: int = 3):
        if not self.client:
            return "Error: Cerebro IA no disponible."

        for attempt in range(max_retries):
            try:
                chat_completion = await self.client.chat.completions.create(
                    messages=messages,
                    model=self.model,
                    temperature=0.7,
                    max_tokens=1024,
                )
                return chat_completion.choices[0].message.content
            except Exception as e:
                logger.error(f"Groq error: {e}")
                if "429" in str(e): # Rate limit
                     if attempt < max_retries - 1:
                        import asyncio
                        await asyncio.sleep(2 ** attempt)
                        continue
                return "Tuve un problema técnico pensando. Intentá de nuevo."
        return "Error inesperado."
    
    async def analyze_checkin(self, context_data: dict, user_input: str) -> str:
        tz_argentina = ZoneInfo("America/Argentina/Buenos_Aires")
        now = datetime.now(tz_argentina)
        
        system_message = f"""Sos JARVISZ, asistente personal para Ariel (50 años, TDAH, Duelo).
        
INFO ACTUAL: {now.strftime("%A %d/%m %H:%M")}
DATOS: {json.dumps(context_data, ensure_ascii=False)}

INSTRUCCIÓN: Analizá el estado de Ariel. Sé empático, breve (2 oraciones) y da un consejo accionable basado en su energía (Body Battery/Sueño)."""

        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_input}
        ]
        
        return await self._call_with_retry(messages)
    
    async def chat(self, user_input: str, garmin_data: dict = None, calendar_events: str = None, tasks_data: str = None, history: list = None) -> str:
        tz_argentina = ZoneInfo("America/Argentina/Buenos_Aires")
        now = datetime.now(tz_argentina)
        
        # --- SAFEGUARD: TRUNCATE INPUTS ---
        # Prevent huge context from crashing Groq
        if calendar_events and len(calendar_events) > 2000:
            calendar_events = calendar_events[:2000] + "... [TRUNCADO POR SEGURIDAD]"
            
        context_str = f"FECHA ACTUAL: {now.strftime('%A %d/%m/%Y %H:%M')}\n"
        
        if garmin_data: context_str += f"SALUD: {garmin_data}\n"
        if calendar_events: context_str += f"AGENDA (Próx 7 días): {calendar_events}\n"
        if tasks_data: context_str += f"TAREAS: {tasks_data}\n"
        
        try:
            with open("knowledge_base.md", "r", encoding="utf-8") as f:
                kb = f.read()
        except: kb = "Usuario: Ariel."

        system_message = f"""Sos JARVISZ, el asistente inteligente de Ariel (50 años).

--- TUS REGLAS DE ORO ---
1. **INFORMACIÓN:** Los datos que ves abajo (AGENDA, TAREAS, CONOCIMIENTO) son la **ÚNICA VERDAD**. No inventes nada.
   - Si dice "Lunes 19", ES Lunes 19. No calcules días. Confía en el texto.
2. **AGENDA:** 
   - Si no ves eventos en la lista, decí "No veo nada agendado". No digas "No tengo acceso". Tienes acceso total.
   - Si te piden "resumen", agrúpalo narrativamente (ej: "Semana tranki, solo rutina laboral, salvo el viernes que tenés médico").
3. **PERSONALIDAD:**
   - Sé directo, usa lenguaje natural argentino ("agendaste", "tenés").
   - NO pidas disculpas todo el tiempo ("Lo siento"). Si no sabés, decí "Che, no encuentro eso".
   - Al hablar de personas (Malena, Patricia, Lautaro), asume que son importantes para Ariel.

--- CONOCIMIENTO BASE ---
{kb}
        
--- CONTEXTO EN TIEMPO REAL ---
{context_str}

Instrucción Final: Responde la consulta de Ariel basándote EXCLUSIVAMENTE en lo de arriba.
"""
        messages = [{"role": "system", "content": system_message}]
        
        # Append history if exists
        if history:
            messages.extend(history)
            
        messages.append({"role": "user", "content": user_input})
        
        return await self._call_with_retry(messages)

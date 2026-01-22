from services.openai_service import OpenAIService
from config import settings
import json
import logging

logger = logging.getLogger(__name__)

class ChunkingService:
    def __init__(self):
        # reuse logic from openai service manually or just import openai client
        # to keep it clean, let's use a fresh client or pass one.
        # Ideally, we should add this method to OpenAIService or just use it here.
        # For Separation of Concerns, let's make this standalone but using the same key.
        from openai import AsyncOpenAI
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY.get_secret_value())

    async def breakdown_task(self, task_description: str) -> list[str]:
        """
        Takes a task (e.g. "Clean the house") and returns exactly 5 micro-steps.
        Returns: List of strings.
        """
        system_prompt = """
        Sos un experto en TDAH y Funciones Ejecutivas.
        Tu tarea: Desglosar una tarea intimidante en 5 MICRO-PASOS ridículamente fáciles.
        
        REGLAS:
        1. Exactamente 5 pasos.
        2. Cada paso debe tener una duración estimada (minutos).
        3. El primer paso debe ser "estúpido" de tan fácil (ej: "Ponerse las zapatillas").
        4. Output JSON: ["1. Paso (2m)", "2. Paso (5m)", ...]
        
        NO uses markdown, solo array JSON puro.
        """
        
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Tarea: {task_description}"}
                ],
                temperature=0.3
            )
            content = response.choices[0].message.content.replace("```json", "").replace("```", "").strip()
            return json.loads(content)
        except Exception as e:
            logger.error(f"Chunking error: {e}")
            return [
                "1. Respirar hondo (1m)",
                "2. Escribir qué querías hacer (1m)",
                "3. Tomar agua (1m)",
                "4. Mirar el primer paso real (1m)",
                "5. Empezar (sin presión) (5m)"
            ]

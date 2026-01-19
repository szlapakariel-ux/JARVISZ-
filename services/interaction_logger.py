import json
import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path

logger = logging.getLogger(__name__)

class InteractionLogger:
    """
    Registra todas las interacciones con JARVISZ para análisis posterior
    """
    
    def __init__(self, log_dir="interaction_logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
    def log_interaction(
        self, 
        user_message: str, 
        bot_response: str,
        context_data: dict = None,
        user_id: int = None
    ):
        """
        Registra una interacción completa
        """
        try:
            # Obtener timestamp en Argentina
            tz_argentina = ZoneInfo("America/Argentina/Buenos_Aires")
            now = datetime.now(tz_argentina)
            
            # Crear estructura de datos
            interaction = {
                "timestamp": now.isoformat(),
                "date": now.strftime("%Y-%m-%d"),
                "time": now.strftime("%H:%M:%S"),
                "day_of_week": now.strftime("%A"),
                "user_id": user_id,
                "user_message": user_message,
                "bot_response": bot_response,
                "context": context_data or {},
                "metadata": {
                    "message_length": len(user_message),
                    "response_length": len(bot_response),
                    "has_garmin_data": bool(context_data and context_data.get("garmin")),
                    "has_calendar_data": bool(context_data and context_data.get("calendar")),
                    "has_tasks_data": bool(context_data and context_data.get("tasks")),
                },
                # Campos para revisión posterior
                "review": {
                    "reviewed": False,
                    "category": None,  # emotional, energy, family, task_with_load, task_simple, other
                    "rating": None,
                    "notes": "",
                    "suggested_changes": []
                }
            }
            
            # Guardar en archivo diario
            log_file = self.log_dir / f"interactions_{now.strftime('%Y-%m-%d')}.jsonl"
            
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(interaction, ensure_ascii=False) + "\n")
            
            logger.info(f"Interaction logged: {log_file}")
            
        except Exception as e:
            logger.error(f"Error logging interaction: {e}")
    
    def get_all_unreviewed(self):
        """
        Obtiene todas las interacciones no revisadas de todos los archivos
        """
        all_unreviewed = []
        
        # Buscar todos los archivos de log
        log_files = sorted(self.log_dir.glob("interactions_*.jsonl"))
        
        for log_file in log_files:
            with open(log_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        interaction = json.loads(line)
                        if not interaction["review"]["reviewed"]:
                            all_unreviewed.append(interaction)
        
        return all_unreviewed
    
    def update_review(self, timestamp: str, rating: str, notes: str = "", suggested_changes: list = None, category: str = None):
        """
        Actualiza la revisión de una interacción específica
        """
        # Extraer fecha del timestamp
        dt = datetime.fromisoformat(timestamp)
        date_str = dt.strftime("%Y-%m-%d")
        
        log_file = self.log_dir / f"interactions_{date_str}.jsonl"
        
        if not log_file.exists():
            logger.error(f"Log file not found: {log_file}")
            return False
        
        # Leer todas las interacciones
        interactions = []
        with open(log_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    interactions.append(json.loads(line))
        
        # Actualizar la interacción específica
        updated = False
        for interaction in interactions:
            if interaction["timestamp"] == timestamp:
                interaction["review"] = {
                    "reviewed": True,
                    "category": category,
                    "rating": rating,
                    "notes": notes,
                    "suggested_changes": suggested_changes or []
                }
                updated = True
                break
        
        if not updated:
            logger.error(f"Interaction not found: {timestamp}")
            return False
        
        # Reescribir el archivo
        with open(log_file, "w", encoding="utf-8") as f:
            for interaction in interactions:
                f.write(json.dumps(interaction, ensure_ascii=False) + "\n")
        
        logger.info(f"Review updated for {timestamp}")
        return True

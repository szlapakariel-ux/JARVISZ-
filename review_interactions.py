"""
Script interactivo para revisar las interacciones con JARVISZ
Categoriza mensajes y evalúa respuestas con checkpoint
"""
import json
from pathlib import Path
from services.interaction_logger import InteractionLogger
from datetime import datetime

class ReviewCheckpoint:
    """Maneja el checkpoint de revisión"""
    
    def __init__(self, checkpoint_file="review_checkpoint.json"):
        self.checkpoint_file = Path(checkpoint_file)
        self.last_reviewed = self.load()
    
    def load(self):
        """Carga el último timestamp revisado"""
        if self.checkpoint_file.exists():
            with open(self.checkpoint_file, "r") as f:
                data = json.load(f)
                return data.get("last_reviewed_timestamp")
        return None
    
    def save(self, timestamp):
        """Guarda el último timestamp revisado"""
        with open(self.checkpoint_file, "w") as f:
            json.dump({
                "last_reviewed_timestamp": timestamp,
                "last_review_date": datetime.now().isoformat()
            }, f, indent=2)

def format_interaction(interaction, index):
    """Formatea una interacción para mostrar"""
    print(f"\n{'='*80}")
    print(f"📝 Interacción #{index + 1}")
    print(f"📅 {interaction['date']} {interaction['time']} ({interaction['day_of_week']})")
    print(f"{'='*80}")
    
    print(f"\n👤 TU MENSAJE:")
    print(f"   {interaction['user_message']}")
    
    print(f"\n🤖 RESPUESTA DE JARVISZ:")
    print(f"   {interaction['bot_response']}")
    
    # Mostrar contexto usado
    context_used = []
    if interaction['metadata']['has_garmin_data']:
        context_used.append("⌚ Garmin")
    if interaction['metadata']['has_calendar_data']:
        context_used.append("📅 Calendar")
    if interaction['metadata']['has_tasks_data']:
        context_used.append("✅ Tasks")
    
    if context_used:
        print(f"\n📊 Datos usados: {', '.join(context_used)}")
    
    print(f"\n{'='*80}")

def categorize_message():
    """Categoriza el mensaje del usuario"""
    print("\n🏷️  ¿Qué tipo de mensaje es TUYO?")
    print("  1 - 🧠 Emocional (cómo te sentís, estado de ánimo)")
    print("  2 - ⚡ Energía (cansancio, estrés, Body Battery)")
    print("  3 - 👨‍👩‍👧 Familia (comunicación con Vani/Male)")
    print("  4 - 📋 Tarea con carga (tiene peso emocional/energético)")
    print("  5 - 📝 Tarea simple (recordatorio sin carga)")
    print("  6 - ❓ Otra")
    print("  s - ⏭️  Saltar")
    print("  q - 🚪 Salir")
    
    choice = input("\nTu elección: ").strip().lower()
    
    if choice == 'q':
        return None, True
    if choice == 's':
        return None, False
    
    category_map = {
        '1': 'emotional',
        '2': 'energy',
        '3': 'family',
        '4': 'task_with_load',
        '5': 'task_simple',
        '6': 'other'
    }
    
    return category_map.get(choice), False

def evaluate_response(category):
    """Evalúa la respuesta de JARVISZ"""
    print("\n📊 ¿Cómo fue la respuesta de JARVISZ para este tipo de mensaje?")
    print("  1 - ✅ Buena (apropiada y útil)")
    print("  2 - ⚠️  Mejorar (funcionó pero podría ser mejor)")
    print("  3 - ❌ Mala (no fue apropiada)")
    
    choice = input("\nTu elección: ").strip()
    
    rating_map = {
        '1': 'good',
        '2': 'needs_improvement',
        '3': 'bad'
    }
    
    rating = rating_map.get(choice)
    
    if not rating:
        print("❌ Opción inválida")
        return None
    
    # Pedir notas
    notes = input("\n💬 Notas (opcional, Enter para saltar): ").strip()
    
    # Pedir cambios sugeridos
    suggested_changes = []
    if rating in ['needs_improvement', 'bad']:
        print("\n📝 ¿Qué debería cambiar? (Enter para terminar)")
        while True:
            change = input("  - ").strip()
            if not change:
                break
            suggested_changes.append(change)
    
    return {
        'category': category,
        'rating': rating,
        'notes': notes,
        'suggested_changes': suggested_changes
    }

def main():
    print("🔍 JARVISZ - Revisor de Interacciones")
    print("="*80)
    
    logger = InteractionLogger()
    checkpoint = ReviewCheckpoint()
    
    # Obtener todas las interacciones no revisadas
    unreviewed = logger.get_all_unreviewed()
    
    if not unreviewed:
        print("\n✅ ¡No hay interacciones pendientes de revisar!")
        print("Todas las conversaciones están revisadas.")
        return
    
    print(f"\n📊 Tienes {len(unreviewed)} interacciones sin revisar")
    print(f"Última revisión: {checkpoint.last_reviewed or 'Nunca'}")
    print("\nPresiona Enter para comenzar...")
    input()
    
    reviewed_count = 0
    
    for i, interaction in enumerate(unreviewed):
        format_interaction(interaction, i)
        
        # Paso 1: Categorizar el mensaje
        category, should_quit = categorize_message()
        
        if should_quit:
            print("\n👋 Saliendo...")
            break
        
        if not category:
            continue  # Skip
        
        # Paso 2: Evaluar la respuesta
        review_data = evaluate_response(category)
        
        if review_data:
            # Guardar la revisión
            success = logger.update_review(
                interaction['timestamp'],
                review_data['rating'],
                review_data['notes'],
                review_data['suggested_changes'],
                review_data['category']
            )
            
            if success:
                checkpoint.save(interaction['timestamp'])
                reviewed_count += 1
                print(f"\n✅ Revisión guardada ({reviewed_count}/{len(unreviewed)})")
    
    # Resumen final
    print(f"\n{'='*80}")
    print(f"📊 RESUMEN")
    print(f"{'='*80}")
    print(f"Revisadas en esta sesión: {reviewed_count}")
    print(f"Pendientes: {len(unreviewed) - reviewed_count}")
    print(f"\n✅ Progreso guardado. La próxima vez continuarás desde aquí.")

if __name__ == '__main__':
    main()

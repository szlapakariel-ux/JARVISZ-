# 📊 Sistema de Revisión de Interacciones

## ¿Qué hace?

Este sistema registra **automáticamente** todas tus conversaciones con JARVISZ para que puedas revisarlas después y mejorar el bot basándote en uso real.

---

## 🔄 Flujo de trabajo

### 1. **Uso normal** (automático)
Simplemente usás JARVISZ como siempre. Cada conversación se guarda automáticamente en `interaction_logs/`.

### 2. **Revisión** (cuando tengas tiempo)
Corrés el script de revisión:

```bash
python review_interactions.py
```

El script te muestra:
- Tus mensajes
- Respuestas de JARVISZ
- Qué datos usó (Garmin, Calendar, Tasks)

Y te pregunta:
- ✅ ¿Funcionó bien?
- ⚠️ ¿Podría mejorar?
- ❌ ¿No funcionó?

### 3. **Checkpoint automático**
El sistema guarda tu progreso. Si lo dejás a la mitad, la próxima vez continúa desde donde quedaste.

---

## 📝 Ejemplo de uso

```
Lunes 10:00 - Conversación 1 con JARVISZ
Lunes 15:00 - Conversación 2 con JARVISZ
Lunes 20:00 - Revisás las 2 conversaciones
              ✅ Checkpoint guardado

Martes 08:00 - Conversación 3 con JARVISZ
Martes 12:00 - Conversación 4 con JARVISZ
Martes 22:00 - Revisás solo las 2 nuevas (3 y 4)
              ✅ Checkpoint actualizado
```

---

## 🎯 Qué revisar

Cuando veas una conversación, preguntate:

**✅ Buena:**
- La respuesta fue útil
- El tono fue apropiado
- Usó los datos correctos

**⚠️ Mejorar:**
- Funcionó pero podría ser mejor
- Faltó mencionar algo
- Sobró información

**❌ Mala:**
- No entendió lo que pediste
- Respuesta inapropiada
- Usó datos incorrectos

---

## 📁 Archivos generados

- `interaction_logs/` - Carpeta con todas las conversaciones
  - `interactions_2026-01-18.jsonl` - Conversaciones del 18/01
  - `interactions_2026-01-19.jsonl` - Conversaciones del 19/01
  - etc.

- `review_checkpoint.json` - Guarda tu progreso de revisión

---

## 💡 Tips

1. **No necesitás revisar todo de una vez** - Hacelo de a poco cuando tengas tiempo
2. **Sé específico en las notas** - Ayuda a saber qué cambiar
3. **Revisá regularmente** - Así no se acumula mucho
4. **Usá los patrones** - Si algo se repite, es importante

---

## 🔧 Comandos útiles

**Revisar interacciones:**
```bash
python review_interactions.py
```

**Ver estadísticas** (próximamente):
```bash
python review_interactions.py --stats
```

---

## 🎯 Objetivo

El objetivo es que JARVISZ mejore continuamente basándose en **tu uso real**, no en suposiciones.

Cada revisión ayuda a:
- Ajustar el tono de las respuestas
- Mejorar qué datos usar y cuándo
- Identificar patrones que se repiten
- Actualizar el knowledge_base.md

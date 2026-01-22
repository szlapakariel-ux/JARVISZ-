# Anexo Técnico: Reglas de "Consolidación Real" para la Implementación

**Referencia:** Archivo `consolidacion_real_conceptos.md`
**Prioridad:** Crítica (Estas reglas definen la aceptación del producto).

El sistema no solo debe ser modular; debe comportarse siguiendo estrictamente las siguientes **Reglas de Oro** derivadas del análisis de mejores prácticas para TDAH y salud mental. Estas reglas afectan principalmente a los módulos **`La Voz` (Frontend/Telegram)** y **`La Consciencia` (Lógica LLM)**.

## 1. Reglas de Interfaz y Mensajería (Módulo `La Voz`)
*El objetivo es reducir la carga cognitiva y evitar el "muro de texto" que provoca abandono.*

*   **La Regla del 3x3:**
    *   **Máximo 3 burbujas** de mensajes consecutivos por parte del bot. Si hay más contenido, el bot debe pausar y esperar interacción (botón "Seguir" o "¿Más info?").
    *   **Máximo 3 líneas** de texto por burbuja en pantallas móviles estándar. El contenido debe ser "escaneable".
*   **Interacción Forzada:**
    *   Se prohíben las preguntas abiertas cuando sea posible usar **Botones (Inline Keyboards)**. Esto reduce la fricción de tener que escribir.
    *   Si se presenta una lista (ej. pasos de una tarea), no debe superar los **5-7 ítems**.

## 2. Estructura de la Conversación (Módulo `La Consciencia`)
*El flujo no puede ser libre; debe seguir una estructura predecible para dar seguridad al usuario.*

El *System Prompt* o la lógica de orquestación debe forzar esta estructura de 4 pasos en cada interacción de ayuda:
1.  **Apertura/Contexto:** Saludo breve + Identificación transparente como IA ("Soy tu asistente IA...").
2.  **Captura de Intención:** Uso de botones para saber qué necesita el usuario rápidamente.
3.  **Acción/Desglose:** El núcleo de la ayuda (ver punto 4 abajo).
4.  **Cierre:** Resumen breve + Refuerzo positivo inmediato.

## 3. Protocolos de "Ceguera Temporal" y Desglose (Módulo `La Consciencia`)
*Funcionalidades críticas para el manejo de funciones ejecutivas.*

*   **Mitigación de Ceguera Temporal:**
    *   Siempre que se plantee una tarea, el bot debe mostrar: Tiempo estimado vs. Tiempo transcurrido o Próximo evento.
    *   Uso de **timers visuales** o avisos de texto ("Te aviso 5 min antes de terminar el bloque").
*   **Desglose de Tareas (Chunking):**
    *   El bot debe **ofrecer** (no forzar) desglosar tareas complejas.
    *   Límite duro: Máximo **5 pasos** de **5-10 minutos** cada uno.
    *   Mostrar progreso visual (ej: "Paso 2/5 completado ✅").

## 4. Protocolo de Bloqueo y Frustración (Módulo `El Sistema Nervioso`)
*Gestión de errores emocionales, no técnicos.*

Si el análisis de sentimiento (en `La Consciencia`) detecta frustración o bloqueo en el usuario:
1.  **Validar primero:** "Es normal sentirse así", "Es difícil, no pasa nada". (Prohibido decir "deberías" o juzgar).
2.  **Ofrecer Salida:** Presentar menú con 3 opciones claras:
    *   ⏸️ Pausa/Descanso.
    *   micro-tarea (algo muy fácil para ganar dopamina).
    *   Cambiar de tema.
3.  **Nunca presionar:** El bot debe degradarse a un rol de soporte pasivo si el usuario lo pide.

## 5. Privacidad y Métricas (Módulo `La Memoria`)
*Reglas estrictas sobre qué se guarda y qué no.*

*   **Lista Negra de Datos (NO GUARDAR):** Contenido exacto de conversaciones privadas, nombres de medicamentos específicos, datos de terceros mencionados en el chat.
*   **Anonimización:** Los patrones se guardan agregados, no vinculados a la identidad real si no es necesario para la sesión activa.
*   **Métricas de Éxito (KPIs):** No medir "tiempo en app". Medir:
    1.  **Adherencia:** (Días con check-in / Días totales).
    2.  **Racha:** Días consecutivos activos (visualizar para gamificación leve).
    3.  **Tasa de Bloqueo:** Cuántas veces se activó el protocolo de frustración.

---

**Nota final:**
> *"La arquitectura modular es el esqueleto, pero estas reglas de consolidación son el alma del proyecto. Una violación de la regla del '3x3' o un tono de respuesta juicioso se considerará un **bug crítico**, igual que si fallara la base de datos."*

# ADR 0011 — Escalado con `necesita-pedro`

- **Estado:** Aceptada
- **Fecha:** 2026-11-24
- **Tipo:** proceso
- **Decidido por:** Pedro
- **Reversibilidad:** reversible
- **Origen:** punto 15 del diseño del método

## Contexto

En modo automático, el agente tiene que saber cuándo parar y cómo preguntar sin que Pedro esté delante.

## Decisión

- El agente para ante una decisión difícil de revertir y de impacto alto, un plan rechazado dos veces, una tercera ronda de revisión, dos fallos seguidos de la misma tarea o algo que contradice la especificación.
- Pregunta con un comentario estructurado en el issue (contexto, pregunta, opciones, recomendación y qué bloquea), pensado para responder desde el móvil.
- Pedro responde en el issue y quita la etiqueta; eso relanza la tarea y la decisión queda como «decidido por Pedro».
- Mientras tanto, el orquestador sigue con lo que no depende de la tarea bloqueada.
- Las paradas predichas por `/validar-spec` se preguntan todas antes de arrancar el hito.

## Alternativas consideradas

- Decidir por paso del tiempo cuando Pedro no responde: descartado; como mucho, un recordatorio a las 24 h.

## Consecuencias

- Los fallos de infraestructura los reintenta el repaso programado y solo escalan si se repiten.

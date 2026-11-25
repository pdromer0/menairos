# ADR 0009 — Orquestador determinista y entornos de ejecución por modo

- **Estado:** Aceptada
- **Fecha:** 2026-11-24
- **Tipo:** arquitectura
- **Decidido por:** Pedro
- **Reversibilidad:** reversible
- **Origen:** punto 13 (ampliado el 2026-11-25) del diseño del método

## Contexto

El modo automático necesita elegir la siguiente tarea, lanzar sesiones y despertarse solo, sin gastar tokens en decidir lo que un script puede decidir.

## Decisión

- **El estado vive en GitHub** (issues, etiquetas, «blocked by» y PRs); no hay base de datos aparte.
- **Un script determinista elige la siguiente tarea**, sin tokens, respetando dependencias, paralelismo y si la tarea necesita el portátil.
- Tres mecanismos para despertar al orquestador: eventos, un repaso programado (cada 3 h por defecto) y un interruptor de pausa (`MENAIROS_PAUSA`).
- **Entornos por modo**: sesiones en la nube de Claude Code para manual y didáctico, GitHub Actions para automático y local (WSL2) solo para las tareas `donde: local`. Son entornos por defecto, no una restricción.
- Paralelismo 1 en el piloto; con más, solo tareas sin dependencias entre sí y de `area` distinta.

## Alternativas consideradas

- Tareas programadas de Claude Code como entorno del modo automático: alternativa configurable, no por defecto mientras estén en vista previa.
- Codex en CI con la acción oficial: exige una API key facturada aparte; Codex trabaja como revisor desde su integración con GitHub o desde WSL2.

## Consecuencias

- Todo GitHub por REST (ADR 0016), y la rama siempre la del issue.

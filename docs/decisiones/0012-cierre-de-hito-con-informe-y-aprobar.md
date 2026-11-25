# ADR 0012 — Cierre de hito con informe y `--aprobar`

- **Estado:** Aceptada
- **Fecha:** 2026-11-24
- **Tipo:** proceso
- **Decidido por:** Pedro
- **Reversibilidad:** reversible
- **Origen:** punto 16 del diseño del método

## Contexto

Al acabar un hito hay que revisar decisiones, comprobar el producto y encauzar las correcciones sin un cierre manual largo.

## Decisión

- Un informe del hito, casi entero con scripts: decisiones marcadas con su veredicto, validación funcional (✅ el agente, 👁 Pedro), métricas, desviaciones y pendientes, resumen de aprendizaje y disparadores de los módulos.
- Los fallos funcionales abren un mini-hito de corrección (N.1); lo no bloqueante entra en la especificación del hito siguiente; las lecciones del método, como issues en el repo de Menairos.
- **Cierre en un solo comando**, `/cerrar-hito N --aprobar`: comprueba que el informe está completo, crea issues y ADRs, aplica los ajustes de autonomía, fusiona el PR de cierre, etiqueta y publica la Release.

## Alternativas consideradas

- No constan alternativas discutidas en la especificación para esta decisión.

## Consecuencias

- El informe propone cambios de autonomía con datos; decide Pedro.

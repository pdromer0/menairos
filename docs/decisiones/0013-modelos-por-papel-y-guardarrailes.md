# ADR 0013 — Modelos por papel y guardarraíles por falta de progreso

- **Estado:** Aceptada
- **Fecha:** 2026-11-24
- **Tipo:** proceso
- **Decidido por:** Pedro
- **Reversibilidad:** reversible
- **Origen:** punto 17 del diseño del método

## Contexto

Con el método v2, la mayor parte del consumo de cuota venía de sesiones largas y de repetir trabajo. Con Max, lo que se arriesga es agotar la cuota, no una factura.

## Decisión

- Primero lo determinista (scripts sin tokens); sesiones cortas y nuevas por tarea; `AGENTS.md` corto; revisores con lo justo; una sola N3.
- **Modelos por papel**, configurables: Opus para `/crear-spec`, los revisores y las críticas; Sonnet para el plan y la implementación normales y para el informe; Codex para `/validar-spec` y la segunda opinión.
- **Guardarraíles que frenan el consumo sin progreso**, no el consumo en sí: topes duros generosos siempre activos, hook anti-bucle y guardarraíles suaves por sesión, tarea, día e hito, con un reintento con otro enfoque antes de escalar.
- En el primer hito automático, los suaves funcionan en modo observación para calibrarlos con datos.

## Alternativas consideradas

- Limitar el consumo en sí (topes bajos): descartado, porque corta trabajo legítimo y va contra la autonomía.

## Consecuencias

- Todos los umbrales viven en `menairos.toml`; el consumo se mide por sesión y se agrega en el informe del hito.

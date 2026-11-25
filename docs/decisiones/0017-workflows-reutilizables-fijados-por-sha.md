# ADR 0017 — Workflows reutilizables fijados por SHA

- **Estado:** Aceptada
- **Fecha:** 2026-11-25
- **Tipo:** arquitectura
- **Decidido por:** Pedro
- **Reversibilidad:** reversible
- **Origen:** `diseno.md` 2.4

## Contexto

Los workflows del modo automático cambiarán a menudo al principio, y copiar YAML a cada proyecto impide que las mejoras lleguen.

## Decisión

- Los workflows viven en el repo de Menairos como *reusable workflows*; cada proyecto solo tiene ficheros finos que los llaman, **fijados por SHA**.

## Alternativas consideradas

- Copiar el YAML a cada proyecto: descartado, porque las mejoras no llegarían sin copiarlas a mano.

## Consecuencias

- Una mejora del orquestador llega con `/actualizar-menairos`.
- Todos los workflows comprueban primero `MENAIROS_PAUSA` y el autor del evento.

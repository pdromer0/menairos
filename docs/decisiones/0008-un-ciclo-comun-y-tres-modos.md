# ADR 0008 — Un ciclo común y tres modos

- **Estado:** Aceptada
- **Fecha:** 2026-11-24
- **Tipo:** proceso
- **Decidido por:** Pedro
- **Reversibilidad:** reversible
- **Origen:** punto 12 del diseño del método

## Contexto

Se quieren tres formas de trabajar (manual, didáctica y automática) sin mantener tres procesos distintos.

## Decisión

- **Un ciclo común**: arranque → plan de 8 apartados → aprobación del plan → implementación (commit por paso con N1, N2 por turno) → revisión propia → una sola N3 → documentación (anexo y fichero de decisiones) → PR → revisión y ajustes → fusión → sincronizar.
- **Los modos solo cambian quién pasa cada puerta y cuánto se explica**: en manual, Pedro; en didáctico, Pedro con conceptos explicados antes; en automático, el orquestador, los revisores y la política.
- Modo por proyecto en `menairos.toml`, que se puede cambiar por hito o por tarea con una etiqueta (`modo:manual`).
- Una sesión nueva por tarea, también en automático.

## Alternativas consideradas

- No constan alternativas discutidas en la especificación para esta decisión.

## Consecuencias

- En automático, el plan y el veredicto del revisor se publican como comentarios del issue; al segundo rechazo, `necesita-pedro`.

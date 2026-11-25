# ADR 0014 — Seguridad en repos públicos

- **Estado:** Aceptada
- **Fecha:** 2026-11-24
- **Tipo:** seguridad
- **Decidido por:** Pedro
- **Reversibilidad:** reversible
- **Origen:** punto 18 del diseño del método

## Contexto

Un agente que actúa sobre repos públicos puede recibir instrucciones de cualquiera (issues, comentarios, PRs de forks) y maneja secretos.

## Decisión

- El agente solo hace caso a Pedro y a su App: workflows disparados solo por ellos, issues solo suyos y comentarios filtrados antes de llegar al modelo.
- Nunca un agente sobre PRs de forks: nada de `pull_request_target`, y los PR de fuera necesitan la aprobación de Pedro para lanzar workflows.
- Secretos solo en los jobs del agente; la N3 del CI corre sin secretos.
- El agente no puede tocar sus propias reglas: rutas protegidas, la App fuera de las excepciones del ruleset y prohibidos el push forzado, el push a `main` y los borrados por la API.
- Cadena de suministro: dependencias nuevas por Pedro, ficheros de bloqueo, Dependabot y acciones fijadas por SHA. Nada personal en el repo y gitleaks en pre-commit.
- App con permisos mínimos, sin administración.

## Alternativas consideradas

- No constan alternativas discutidas en la especificación para esta decisión.

## Consecuencias

- Queda por evaluar en el hito 0 una lista de destinos de red permitidos para el job del agente.

# ADR 0010 — Fusión automática por tres checks y política

- **Estado:** Aceptada
- **Fecha:** 2026-11-24
- **Tipo:** proceso
- **Decidido por:** Pedro
- **Reversibilidad:** reversible
- **Origen:** punto 14 del diseño del método

## Contexto

En el método v2, Pedro revisa y fusiona cada PR; en modo automático hace falta una puerta que no dependa de él salvo en lo que importa.

## Decisión

- Tres checks obligatorios en el ruleset de `main` y auto-merge por *squash*: `ci` (la N3, sin tokens), `revision` (un agente con contexto limpio) y `politica` (un script).
- `politica` deja el PR esperando a Pedro en las tareas críticas, en las rutas protegidas (`.github/workflows/`, `.claude/`, `AGENTS.md`, `menairos.toml`…) y con dependencias nuevas; Pedro lo desbloquea con `aprobado-pedro` o fusionando.
- Como máximo dos rondas de revisión; a la tercera, `necesita-pedro`.
- Identidad propia: una GitHub App, `menairos-agente`.
- Revisor bloqueante Claude; Codex como segunda opinión en las críticas.

## Alternativas consideradas

- Abrir los PR con el `GITHUB_TOKEN` de Actions: descartado, porque esos PR no disparan otros workflows (el CI no arrancaría).
- Codex como revisor bloqueante: pendiente de verificar en el hito 0.

## Consecuencias

- El historial distingue lo que hizo el agente de lo que hizo Pedro.

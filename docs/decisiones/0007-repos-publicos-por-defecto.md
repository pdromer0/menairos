# ADR 0007 — Repos públicos por defecto

- **Estado:** Aceptada
- **Fecha:** 2026-11-24
- **Tipo:** seguridad
- **Decidido por:** Pedro
- **Reversibilidad:** reversible
- **Origen:** punto 11 del diseño del método

## Contexto

Con GitHub Free, los rulesets solo se aplican en repos públicos, y el modo automático necesita el ruleset como puerta.

## Decisión

- Campo `proyecto.visibilidad` en `menairos.toml`, con **público por defecto** y nada personal en el repo.
- Un proyecto privado en modo automático requiere GitHub Pro; en modo manual, un repo privado sin reglas sirve porque la puerta es Pedro.

## Alternativas consideradas

- Repos privados por defecto: exigirían GitHub Pro para el modo automático.

## Consecuencias

- Las reglas de seguridad de repos públicos (ADR 0014) son obligatorias.
- El valor por defecto se puede cambiar por proyecto; hacer público un repo, en cambio, expone su historia: por eso nada personal desde el primer commit.

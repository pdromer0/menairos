# ADR 0016 — GitHub siempre por REST con `gh api`

- **Estado:** Aceptada
- **Fecha:** 2026-11-25
- **Tipo:** arquitectura
- **Decidido por:** Pedro
- **Reversibilidad:** reversible
- **Origen:** `diseno.md` 2.2

## Contexto

Las sesiones en la nube daban 403 con GraphQL, y cada entorno ya tiene su propia autenticación de GitHub.

## Decisión

- Todo lo de GitHub, por REST y a través de `gh api`, con un envoltorio fino que en los tests se sustituye por un doble con tope.

## Alternativas consideradas

- GraphQL: descartado por el 403 en las sesiones en la nube.

## Consecuencias

- Se reutiliza la autenticación de cada entorno (local, nube y Actions con el token de la App).
- Las órdenes de `gh` que usan GraphQL (por ejemplo, `gh pr edit`) no se usan desde la CLI.

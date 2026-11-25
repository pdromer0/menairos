# ADR 0019 — Estado de los módulos en `menairos.toml`

- **Estado:** Aceptada
- **Fecha:** 2026-11-25
- **Tipo:** arquitectura
- **Decidido por:** Pedro
- **Reversibilidad:** reversible
- **Origen:** `diseno.md` 3.1

## Contexto

Las piezas del modo automático entran como módulos con disparador y estado (inactivo, piloto, activo, retirado), y los scripts necesitan leer ese estado.

## Decisión

- El estado de los módulos vive en `menairos.toml` (`[modulos]`), legible por los scripts.

## Alternativas consideradas

- Mantener el estado en una tabla de un documento: queda solo como vista humana, que genera la CLI en `docs/proceso/modulos.md`.

## Consecuencias

- `/cerrar-hito` puede proponer activar o retirar módulos con datos.

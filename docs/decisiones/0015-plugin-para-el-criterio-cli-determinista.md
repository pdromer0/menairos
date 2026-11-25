# ADR 0015 — Plugin para el criterio, CLI determinista para lo demás

- **Estado:** Aceptada
- **Fecha:** 2026-11-25
- **Tipo:** arquitectura
- **Decidido por:** Pedro
- **Reversibilidad:** difícil de revertir
- **Origen:** `diseno.md` 2.1–2.2

## Contexto

Cada token que un modelo gasta en reconstruir algo calculable es cuota perdida y una fuente de errores.

## Decisión

- Lo que requiere criterio lo hace un modelo siguiendo un prompt del plugin; todo lo demás lo hace la **CLI `menairos`**, determinista y con tests.
- La CLI es un paquete Python en el mismo repo, con la misma versión que el plugin, instalado fijado a la versión del proyecto.
- Salidas en JSON para el modelo y en markdown para Pedro.

## Alternativas consideradas

- No constan alternativas discutidas en la especificación para esta decisión.

## Consecuencias

- Los prompts del plugin son cortos y delegan en la CLI todo lo calculable.

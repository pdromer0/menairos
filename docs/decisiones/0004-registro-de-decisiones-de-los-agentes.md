# ADR 0004 — Registro de decisiones de los agentes con matriz reversibilidad × impacto

- **Estado:** Aceptada
- **Fecha:** 2026-11-24
- **Tipo:** proceso
- **Decidido por:** Pedro
- **Reversibilidad:** reversible
- **Origen:** punto 9 del diseño del método

## Contexto

Las decisiones que toman los agentes quedaban repartidas por PRs y anexos, sin un sitio donde revisarlas juntas, y sin una frontera clara entre decidir solo y preguntar.

## Decisión

- Se registra todo lo que el plan interpreta, las dependencias nuevas, los cambios de interfaz o de esquema, las desviaciones, los criterios sin cumplir, los umbrales elegidos por el agente y las dudas que el modo manual habría preguntado.
- Frontera entre registrar y parar: una matriz de reversibilidad × impacto. Reversible y de impacto bajo: decide y registra. Difícil de revertir o de impacto alto: decide, registra y la decisión queda **marcada**. Difícil de revertir y de impacto alto: **para** con `necesita-pedro`.
- Un fichero por tarea, en el mismo PR (`docs/specs/hito-N/decisiones/T-xx.yaml`).
- `/cerrar-hito` agrega los ficheros y Pedro revisa solo las marcadas: *aceptada*, *corregir* o *elevar a ADR*.
- El porcentaje de decisiones aceptadas mide la confianza para ampliar o recortar la autonomía.

## Alternativas consideradas

- No constan alternativas discutidas en la especificación para esta decisión.

## Consecuencias

- La marca se calcula, no se escribe (H0.1), y difícil + alto + decidido por el agente es un error de validación.
- Los umbrales concretos viven en `menairos.toml`.

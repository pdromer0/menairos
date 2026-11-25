# Decisiones (ADRs)

Cada ADR recoge una decisión de fondo: su contexto, la decisión, las alternativas que constan y
sus consecuencias. Los metadatos van como líneas de lista; `menairos spec validar` lee la línea
`- **Tipo:** …` (comprobación E12: debe haber al menos un ADR de tipo `stack`).

Los ADRs 0001 a 0020 se escribieron al crear el repo (T-03), a partir de las decisiones de fondo
del diseño del método (sus «puntos», que los documentos siguen citando) y de las decisiones
aceptadas en `diseno.md`. Todas las tomó Pedro el 2026-11-24 o el 2026-11-25. La reversibilidad la
propuso el chat al redactarlos y la revisó Pedro en el PR.

| ADR | Decisión | Origen | Tipo | Reversibilidad |
| --- | --- | --- | --- | --- |
| [0001](0001-menairos-v3-del-metodo.md) | Menairos es la v3 del método | 19 | proceso | reversible |
| [0002](0002-repo-propio-plugin-y-menairos-toml.md) | Repo propio, plugin de Claude Code y `menairos.toml` | 7 | arquitectura | difícil de revertir |
| [0003](0003-formato-de-la-especificacion.md) | Formato de la especificación: documentos y tareas en YAML | 8 | proceso | difícil de revertir |
| [0004](0004-registro-de-decisiones-de-los-agentes.md) | Registro de decisiones de los agentes con matriz reversibilidad × impacto | 9 | proceso | reversible |
| [0005](0005-validacion-en-dos-capas.md) | Validación en dos capas y publicación con OK de Pedro | 10 | proceso | reversible |
| [0006](0006-plantillas-por-stack-con-contrato-comun.md) | Plantillas por stack con contrato común | 11 | arquitectura | difícil de revertir |
| [0007](0007-repos-publicos-por-defecto.md) | Repos públicos por defecto | 11 | seguridad | reversible |
| [0008](0008-un-ciclo-comun-y-tres-modos.md) | Un ciclo común y tres modos | 12 | proceso | reversible |
| [0009](0009-orquestador-determinista-y-entornos.md) | Orquestador determinista y entornos de ejecución por modo | 13 (ampliado el 2026-11-25) | arquitectura | reversible |
| [0010](0010-fusion-automatica-por-checks-y-politica.md) | Fusión automática por tres checks y política | 14 | proceso | reversible |
| [0011](0011-escalado-con-necesita-pedro.md) | Escalado con `necesita-pedro` | 15 | proceso | reversible |
| [0012](0012-cierre-de-hito-con-informe-y-aprobar.md) | Cierre de hito con informe y `--aprobar` | 16 | proceso | reversible |
| [0013](0013-modelos-por-papel-y-guardarrailes.md) | Modelos por papel y guardarraíles por falta de progreso | 17 | proceso | reversible |
| [0014](0014-seguridad-en-repos-publicos.md) | Seguridad en repos públicos | 18 | seguridad | reversible |
| [0015](0015-plugin-para-el-criterio-cli-determinista.md) | Plugin para el criterio, CLI determinista para lo demás | `diseno.md` 2.1–2.2 | arquitectura | difícil de revertir |
| [0016](0016-github-por-rest-con-gh-api.md) | GitHub siempre por REST con `gh api` | `diseno.md` 2.2 | arquitectura | reversible |
| [0017](0017-workflows-reutilizables-fijados-por-sha.md) | Workflows reutilizables fijados por SHA | `diseno.md` 2.4 | arquitectura | reversible |
| [0018](0018-esquemas-json-como-contrato.md) | Esquemas JSON como contrato versionado | `diseno.md` 2.5 | arquitectura | difícil de revertir |
| [0019](0019-estado-de-los-modulos-en-menairos-toml.md) | Estado de los módulos en `menairos.toml` | `diseno.md` 3.1 | arquitectura | reversible |
| [0020](0020-stack-python-3-14-con-uv.md) | Stack de Menairos: Python 3.14 con uv | `diseno.md` 5 | stack | difícil de revertir |

## Del punto del diseño al ADR

| Punto | ADR |
| --- | --- |
| 1–6 (contexto: propósito, quién decide, modos, suscripciones, entorno, GitHub) | Sin ADR: son el punto de partida, recogido en `producto.md` |
| 7 | 0002 |
| 8 | 0003 |
| 9 | 0004 |
| 10 | 0005 |
| 11 | 0006 y 0007 |
| 12 | 0008 |
| 13 | 0009 |
| 14 | 0010 |
| 15 | 0011 |
| 16 | 0012 |
| 17 | 0013 |
| 18 | 0014 |
| 19 | 0001 |
| 20 (piloto) | Sin ADR: la secuencia y los criterios del piloto están en `hitos.md` |

## Formato de un ADR nuevo

```markdown
# ADR NNNN — Título

- **Estado:** Propuesta | Aceptada | Sustituida por NNNN
- **Fecha:** AAAA-MM-DD
- **Tipo:** proceso | arquitectura | seguridad | stack
- **Decidido por:** Pedro | agente (validado por Pedro)
- **Reversibilidad:** reversible | difícil de revertir
- **Origen:** de dónde sale la decisión

## Contexto
## Decisión
## Alternativas consideradas
## Consecuencias
```

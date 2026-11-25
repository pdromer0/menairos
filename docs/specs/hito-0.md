# Hito 0 — Núcleo en modo manual

> **Estado:** borrador v1 (2026-11-25), en redacción por tramos.
> - **H0.0 y H0.1:** aceptados por Pedro (2026-11-25), incluidas la verificación temprana del
>   plugin, el repo como fuente de verdad, la marca calculada de las decisiones y los formatos
>   fijos de `abiertas.md` y de los ADRs.
> - **H0.2:** aceptado por Pedro (2026-11-25): plantillas sin Jinja, manifiesto `plantilla.toml`,
>   la CLI no instala nada en el sistema, nunca sobrescribe en un repo existente, `menairos.toml`
>   lo crea `/crear-spec` y las comprobaciones remotas se verifican por la API.
> - **H0.3:** aceptado por Pedro (2026-11-25): especificación en git desde el primer minuto, orden
>   crear → validar → preparar → publicar, primer hito especificado = 1, estado de las fases en
>   `.menairos/estado-spec.toml`, fase 0 del modo MVP con gitleaks, revisor Codex con
>   `codex exec` y formato fijo del informe de revisión (E15).
> - **H0.4:** aceptado por Pedro (2026-11-25): prioridad del modo (comando > tarea > hito >
>   proyecto), lo aprobado en el plan como `decidido_por: pedro`, hooks en Python, anti-bucle
>   también en manual y `/sincronizar` como comando aparte.
> - **H0.5:** aceptado por Pedro (2026-11-25): veredictos en el propio informe, cada ✅ con su
>   orden, `cierre --aprobar` protegido con una regla `ask`, la App `menairos-agente` creada ya en
>   el H0, y el H0 cerrado con su propio `/cerrar-hito` (`v3.0.0`) y el H1 especificado con
>   `/crear-spec --siguiente`.
> - **El H0 se mantiene completo** (decisión de Pedro, 2026-11-25): no se recorta para adelantar el
>   H1.
>
> Objetivo, criterios de salida y demo funcional: `../hitos.md`. Diseño: `../diseno.md`.

## 0. Cómo se trabaja en este hito

- **Hasta que exista `/implementar` (H0.4)**, cada tarea sigue el flujo del método v2: issue →
  plan con los 8 apartados aprobado por Pedro → rama → commits con N1 → N2 al final de cada turno
  → revisión propia → una sola N3 → PR → Pedro revisa y fusiona.
- **Desde H0.4**, las tareas que quedan se hacen con `/implementar` de Menairos (modo manual): es
  su primera prueba real.
- Cada tarea escribe su entrada en el **Anexo** (§7) en el mismo PR, con el formato del método v2: qué
  se hizo, decisiones del diff, medidas, versiones incorrectas, revisión y pendiente.
- **Por tarea, con el chat** (decisiones de Pedro, 2026-11-25): el chat explica cada tarea y se
  discuten todos sus puntos al principio; el plan se valida en el chat solo en las tareas críticas
  o complicadas; Claude Code, en WSL2 y con un encargo del chat, implementa la tarea entera hasta
  dejar el PR abierto; el chat revisa el PR y Pedro fusiona. Los cambios de especificación se
  discuten en el chat y entran en el PR de la tarea que los necesita; el seguimiento del hito vive
  en el documento de seguimiento del Project.
- **T-01 a T-08 no tienen issue** (decisión de Pedro, 2026-11-25): se trabajan con encargos del
  chat y su entrada del anexo va en el PR (las de T-01 y T-02 se escribieron en el Project y entran
  en el repo con T-03). **T-08 publica con `menairos spec publicar` los issues del hito 0 en
  `pdromer0/menairos`**, su primera prueba real sobre el propio Menairos; los de las tareas ya
  hechas (T-01 a T-08) los cierra Pedro con un enlace a su PR, porque `spec publicar` nunca cierra
  nada. Desde T-09, cada tarea sale de su issue.

---

## 1. H0.0 — Arranque

### 1.1 Qué se construye

El repo `pdromer0/menairos`, con su protección, su CI y los documentos de este Project dentro, más
una **verificación temprana del plugin**: comprobar cuanto antes el mayor riesgo técnico del
diseño (que el plugin se instale solo en la nube).

### 1.2 Repo y protección

| Ajuste | Valor | Cómo |
| --- | --- | --- |
| Visibilidad | Público, sin nada personal | `gh repo create` |
| Ruleset «Proteger main» | PR obligatorio; check `ci` obligatorio; rama al día; sin push forzado ni borrado; solo Pedro (su usuario, `actor_type: User`) en la lista de excepciones, **y solo a través de un PR** (modo de excepción `pull_request`): un push directo a `main` se rechaza también para él | API (`POST /repos/{o}/{r}/rulesets`) |
| Escaneo de secretos y protección de push | Activados | API, comprobado después |
| Alertas de Dependabot | Activadas (sin actualizaciones automáticas) | API |
| Informe privado de vulnerabilidades | Activado, con `SECURITY.md` | API |
| PR de forks | Aprobación obligatoria para lanzar workflows, para cualquier persona externa | API (`PUT /repos/{o}/{r}/actions/permissions/fork-pr-contributor-approval`, `all_external_contributors`) |
| Fusión | Solo *squash*; borrar la rama al fusionar; auto-merge permitido | API |
| CodeQL | Configuración por defecto | API (`PATCH /repos/{o}/{r}/code-scanning/default-setup`, lenguajes `python` y `actions`), **en T-02** |

Lo que se ajusta en la web se comprueba después por la API (lección de un proyecto anterior: «lo que se ajusta en
la web se comprueba por la API, no se da por puesto»).

Ajustes al preparar T-01 (2026-11-25, propuestos por el chat; confirmados por Pedro el 2026-11-25):

- **Primero el commit inicial, después el ruleset**: el repo se crea con un primer commit
  (`README.md` y `SECURITY.md`) y el ruleset se activa después; si no, `main` nacería bloqueada.
- **El check `ci` aún no existe en T-01**: lo crea T-02, y su job debe llamarse exactamente `ci`,
  sin matriz (una matriz cambia el nombre del check), para que coincida con el ruleset. El PR de
  T-02 trae el workflow, así que el check corre en ese mismo PR. En el paso 4 de T-01 se comprueba
  por la API que el ruleset guarda `ci`; si no lo admite, el check se añade al ruleset en T-02,
  después de su primera ejecución. **T-03 depende de T-02**, porque su PR necesita el check `ci`.
- **CodeQL pasa a T-02**: su configuración por defecto necesita código en un lenguaje que analizar,
  y en T-01 el repo solo tiene documentos. Se activa por la API, con los lenguajes `python` y
  `actions`.
- **La excepción de Pedro es solo por PR**: así la comprobación deliberada del push directo a
  `main` (1.7) falla también con su usuario, y Pedro conserva la salida de emergencia de fusionar
  un PR saltándose las reglas. La excepción es por usuario, no por rol, con el identificador
  sacado de `gh api user --jq .id`; plan B, si la API no admite el actor `User`: el rol de
  administrador, con su identificador leído por la API.
- **La aprobación de los PR de forks, por la API** (encontrado en el paso 5 de T-01): la ruta
  existe a nivel de repo, así que deja de ser un paso manual de Pedro. Valor: el más estricto,
  `all_external_contributors`.

### 1.3 Estructura inicial

```
menairos/
├── .claude-plugin/
│   ├── plugin.json            manifiesto del plugin (versión = la del paquete)
│   └── marketplace.json       marketplace de un solo plugin
├── skills/
│   └── menairos-hola/         skill mínima para la verificación temprana (1.6); se retira en H0.5
├── src/menairos/
│   ├── __init__.py            __version__
│   └── cli.py                 punto de entrada `menairos` (argparse, sin dependencias)
├── tests/
├── scripts/                   n1.sh y n3.sh (la N2, con su sello, llega con el hook Stop en T-20)
├── esquemas/                  (H0.1)
├── plantillas/                (H0.2)
├── docs/
│   ├── producto.md, diseno.md, hitos.md, abiertas.md
│   ├── specs/hito-0.md, specs/hito-0.tareas.yaml
│   ├── decisiones/            ADRs (1.5) e índice README.md (punto del diseño → ADR)
│   └── proceso/lecciones.md   reglas aprendidas, reutilizables entre tareas
├── .claude/settings.json      permisos del método v2 (fusión y push forzado denegados)
├── .github/
│   ├── workflows/ci.yml       N3: ruff, pyright, pytest; sin secretos; acciones fijadas por SHA
│   ├── ISSUE_TEMPLATE/        tarea, bug, idea
│   └── pull_request_template.md
├── AGENTS.md, CLAUDE.md
├── menairos.toml              la configuración del propio repo
├── pyproject.toml, uv.lock, .pre-commit-config.yaml, .python-version
└── README.md, SECURITY.md
```

- **Stack** (ADR 0020): Python 3.14 con uv; ruff, pyright en modo estándar, pytest con
  pytest-timeout, pre-commit con gitleaks. Las versiones se verifican con herramientas en el
  momento, no de memoria.
- **`AGENTS.md`**, corto: modo de trabajo de §0, comandos, convenciones de idiomas (documentación,
  commits y tests en español; código en inglés), reglas de git. El detalle, enlazado.
- **`menairos.toml` del propio repo:** `version = "3.0.0-dev"`, modo `manual`, entornos por
  defecto `nube` (manual y didáctico) y `actions` (automático), módulos `revisor_plan = "activo"` y
  el resto `inactivo`. El entorno de `menairos.toml` es el **de por defecto, no una restricción**
  (decisión de Pedro, 2026-11-25): Pedro puede trabajar en local o en la nube en los modos manual y
  didáctico; solo `donde: local` en una tarea obliga a hacerla en local.
- **Reparto por tareas** (al preparar T-02, aceptado por Pedro el 2026-11-25): T-02 crea el
  paquete, los tests, `scripts/`, la configuración del stack, el CI, las plantillas de issue y de
  PR, `AGENTS.md`, `CLAUDE.md`, `.claude/settings.json` y `menairos.toml`; `docs/` llega con T-03;
  `.claude-plugin/` y `skills/menairos-hola/`, con T-04; `esquemas/`, con T-05; `plantillas/`, con
  T-09 y T-10.
- **Niveles de comprobación hasta T-10** (aceptado por Pedro el 2026-11-25): `scripts/n1.sh
  [rutas…]` (ruff, pyright y los tests de las rutas dadas) y `scripts/n3.sh` (formato comprobado,
  lint, tipos y todos los tests), los dos con salida 0 o 1 y diciendo qué ejecutaron; el CI llama
  a `scripts/n3.sh`, como hará el workflow de la plantilla `base`. La N2 llega con el hook `Stop`
  (T-20).

### 1.4 Documentos del Project al repo

Se copian `producto.md`, `diseno.md`, `hitos.md`, `specs/hito-0.md`, `specs/hito-0.tareas.yaml` y
`abiertas.md` a `docs/`, citando los proyectos del método v2 de forma genérica, sin sus nombres
(decisión de Pedro, 2026-11-25). Desde ese momento **el repo es la fuente de verdad**: el Project se queda
con su documento de seguimiento y los demás documentos se marcan como archivados (lección
del método v2: «el repositorio es la fuente de verdad de la documentación»).

### 1.5 ADRs iniciales

Formato del método v2 (Estado, Fecha, Contexto, Decisión, Alternativas consideradas, Consecuencias)
más tres campos: **Tipo** (por ejemplo `stack`, `proceso`, `arquitectura`; lo usa la comprobación
E12), **Decidido por** (Pedro o agente) y **Reversibilidad** (reversible o difícil de revertir).
Todos con fecha 2026-11-24 o 2026-11-25 y decididos por Pedro. Los metadatos van como líneas de
lista (`- **Tipo:** …`), que es lo que lee E12. `docs/decisiones/README.md` es el índice: cada
punto del diseño del método con su ADR, y el tipo y la reversibilidad de cada uno.

| ADR | Decisión | Origen |
| --- | --- | --- |
| 0001 | Menairos es la v3 del método | Punto 19 |
| 0002 | Repo propio, plugin de Claude Code y `menairos.toml` | Punto 7 |
| 0003 | Formato de la especificación: documentos y tareas en YAML | Punto 8 |
| 0004 | Registro de decisiones de los agentes con matriz reversibilidad × impacto | Punto 9 |
| 0005 | Validación en dos capas y publicación con OK de Pedro | Punto 10 |
| 0006 | Plantillas por stack con contrato común | Punto 11 |
| 0007 | Repos públicos por defecto | Punto 11 |
| 0008 | Un ciclo común y tres modos | Punto 12 |
| 0009 | Orquestador determinista y entornos de ejecución por modo | Punto 13 |
| 0010 | Fusión automática por tres checks y política | Punto 14 |
| 0011 | Escalado con `necesita-pedro` | Punto 15 |
| 0012 | Cierre de hito con informe y `--aprobar` | Punto 16 |
| 0013 | Modelos por papel y guardarraíles por falta de progreso | Punto 17 |
| 0014 | Seguridad en repos públicos | Punto 18 |
| 0015 | Plugin para el criterio, CLI determinista para lo demás | `diseno.md` 2.1–2.2 |
| 0016 | GitHub siempre por REST con `gh api` | `diseno.md` 2.2 |
| 0017 | Workflows reutilizables fijados por SHA | `diseno.md` 2.4 |
| 0018 | Esquemas JSON como contrato versionado | `diseno.md` 2.5 |
| 0019 | Estado de los módulos en `menairos.toml` | `diseno.md` 3.1 |
| 0020 | Stack de Menairos: Python 3.14 con uv (tipo `stack`) | `diseno.md` 5 |

### 1.6 Verificación temprana del plugin (V-plugin)

El riesgo más alto del diseño se comprueba en el primer tramo, no en el último:

1. Una skill mínima, `menairos-hola`, que solo responde con la versión del plugin.
2. Un repo de prueba público (`pdromer0/menairos-prueba`) con un `.claude/settings.json` que
   declara el marketplace de Menairos y habilita el plugin.
3. Se comprueba que la skill aparece y responde:
   - en local, en una sesión nueva de Claude Code abierta en el repo de prueba;
   - en una sesión en la nube de Claude Code sobre el repo de prueba.
4. El resultado va al anexo y a `abiertas.md`. Si en la nube no se instala solo, se aplica el
   plan B de `diseno.md` 2.1 (copiar el plugin a `.claude/` del proyecto) y se anota como
   decisión.

La comprobación en `claude-code-action` se deja para H0.5, cuando haya un workflow mínimo.

### 1.7 Comprobaciones deliberadas

Como en un proyecto anterior, antes del primer push de código (T-02) se provoca a propósito cada fallo y se deshace:

| Fallo provocado | Debe saltar | Con el mensaje de |
| --- | --- | --- |
| Un fichero mal formateado | pre-commit (ruff format) | ruff |
| Un error de tipos | pre-commit (pyright) | pyright |
| Una clave falsa con formato real, inventada en el momento | pre-commit (gitleaks) | gitleaks |
| Un test que falla | CI (`ci`) | pytest |
| Un push directo a `main` | GitHub | `GH013` (ruleset) |

Cada comprobación vale solo si el fallo cae dentro de lo que la herramienta revisa (lección de
un proyecto anterior: «un hook en verde no dice qué revisó»).

### 1.8 Hecho cuando

- El repo existe con la estructura de 1.3, el CI en verde y la protección de 1.2 comprobada por la
  API.
- Los documentos están en `docs/` y los 20 ADRs en `docs/decisiones/`.
- Las cinco comprobaciones deliberadas de 1.7 se hicieron y están anotadas en el anexo.
- La verificación V-plugin tiene resultado (en local y en la nube), anotado en el anexo y en
  `abiertas.md`.

---

## 2. H0.1 — Contratos

### 2.1 Qué se construye

Los tres esquemas JSON que definen el contrato de Menairos y las dos primeras órdenes de la CLI:
`menairos spec validar` (la capa 1 de `/validar-spec`) y `menairos spec publicar`.

### 2.2 Esquemas

JSON Schema (versión 2020-12) en `esquemas/`, con `"additionalProperties": false` en todos los
objetos: **una clave desconocida es un error**, para atrapar las erratas (`modelo` por `modelos`).
Los valores por defecto se declaran en el esquema (`default`) y los aplica la CLI.

#### `menairos.schema.json` (para `menairos.toml`)

| Clave | Tipo | Obligatoria | Por defecto | Regla |
| --- | --- | --- | --- | --- |
| `menairos.version` | texto | Sí | — | Versión semántica (`3.0.0`, `3.1.0-dev`) |
| `proyecto.nombre` | texto | Sí | — | No vacío |
| `proyecto.repo` | texto | Sí | — | `dueño/repo` |
| `proyecto.visibilidad` | `publico` \| `privado` | No | `publico` | |
| `proyecto.idioma_docs`, `idioma_codigo` | texto | No | `es`, `en` | Código de idioma de 2 letras |
| `stack.plantillas` | lista de textos | Sí | — | Al menos una; debe incluir `base` |
| `modo.defecto` | `manual` \| `didactico` \| `automatico` | No | `manual` | |
| `modo.resumen_aprendizaje` | booleano | No | `true` | |
| `entornos.*` | ver `diseno.md` 3.1 | No | `nube`, `nube`, `actions` | |
| `modelos.*`, `revisores.*` | ver `diseno.md` 3.1 | No | Los del punto 17 | `opus` \| `sonnet` \| `haiku` \| `codex` según el papel |
| `autonomia.*`, `escalado.*`, `guardarrailes.*` | ver `diseno.md` 3.1 | No | Los de `diseno.md` 3.1 | Enteros ≥ 1; porcentajes 1–100 |
| `modulos.*` | `inactivo` \| `piloto` \| `activo` \| `retirado` | No | `inactivo` | |

Coherencias que el esquema no puede expresar y comprueba la CLI:

- `modo.defecto = "automatico"` con `proyecto.visibilidad = "privado"` → aviso (requiere GitHub
  Pro).
- `revisores.pr = "codex"` → aviso mientras la verificación del hito 0 no confirme que Codex
  puede ser check bloqueante.

#### `tareas.schema.json` (para `hito-N.tareas.yaml`)

| Clave | Tipo | Obligatoria | Regla |
| --- | --- | --- | --- |
| `hito` | entero | Sí | ≥ 0 |
| `titulo` | texto | Sí | No vacío |
| `tareas` | lista | Sí | Al menos una |
| `tareas[].id` | texto | Sí | `T-` y 2 o 3 dígitos (`T-01`, `T-104`) |
| `tareas[].titulo` | texto | Sí | No vacío |
| `tareas[].rama` | texto | Sí | Prefijo `feat/`, `fix/`, `docs/`, `refactor/`, `test/`, `chore/` o `ci/` y después `[a-z0-9._-]+` |
| `tareas[].depende_de` | lista de ids | No (`[]`) | |
| `tareas[].area` | texto | No (`general`) | Minúsculas y guiones |
| `tareas[].critica` | booleano | No (`false`) | |
| `tareas[].motivo_critica` | texto | Si `critica` es `true` | |
| `tareas[].donde` | `cualquiera` \| `local` | No (`cualquiera`) | |
| `tareas[].quien` | `claude` \| `codex` | No (`claude`) | |
| `tareas[].modo` | `null` \| modo | No (`null`) | `null` = el del hito |
| `tareas[].especificacion` | lista de textos | Sí | Al menos una; `fichero.md#ancla` |
| `tareas[].criterios_aceptacion` | lista de textos | Sí | Al menos uno, no vacíos |

#### `decisiones.schema.json` (para `decisiones/T-xx.yaml`)

| Clave | Tipo | Obligatoria | Regla |
| --- | --- | --- | --- |
| `tarea` | texto | Sí | El id de la tarea |
| `decisiones` | lista | Sí | Puede estar vacía |
| `decisiones[].id` | texto | Sí | `T-xx-Dn` de la misma tarea |
| `decisiones[].decision`, `motivo` | texto | Sí | No vacíos |
| `decisiones[].alternativas` | lista de textos | Sí | Al menos una |
| `decisiones[].reversibilidad` | `reversible` \| `dificil` | Sí | |
| `decisiones[].impacto` | `bajo` \| `alto` | Sí | |
| `decisiones[].decidido_por` | `agente` \| `pedro` | Sí | |
| `decisiones[].por_que_no_escalo` | texto | Si `decidido_por` es `agente` | |
| `decisiones[].agente`, `revisor` | texto | No | |
| `decisiones[].revision` | `pendiente` \| `aceptada` \| `corregir` \| `elevar-a-adr` | No (`pendiente`) | |

Coherencias de la CLI sobre las decisiones:

- **La marca se calcula, no se escribe:** una decisión está marcada si es `dificil` o de impacto
  `alto`. Así el agente no puede «olvidarse» de marcarla.
- **`dificil` + `alto` + `decidido_por: agente` es un error**: según la matriz del punto 9, el
  agente tenía que haber parado.

### 2.3 `menairos spec validar`

```
menairos spec validar [--hito N] [--json] [--raiz RUTA]
```

- Sin `--hito`, valida el hito con el número más alto que tenga `docs/specs/hito-N.tareas.yaml`.
- Lee `menairos.toml`, `docs/specs/hito-N.md`, `docs/specs/hito-N.tareas.yaml`,
  `docs/abiertas.md` y `docs/decisiones/`.
- **Salida:** con `--json`, `{"ok": bool, "errores": [...], "avisos": [...]}`, donde cada
  elemento lleva `codigo`, `mensaje`, `fichero` y `ruta` (por ejemplo, `tareas[3].depende_de[0]`);
  sin `--json`, una lista legible por Pedro.
- **Código de salida:** `0` sin errores (aunque haya avisos), `1` con errores, `2` error de uso
  (fichero que no existe, argumentos mal).

| Código | Comprobación |
| --- | --- |
| E01 | `menairos.toml` no cumple su esquema |
| E02 | `hito-N.tareas.yaml` no cumple su esquema |
| E03 | Id de tarea repetido |
| E04 | Rama repetida entre tareas |
| E05 | Dependencia a un id que no existe |
| E06 | Una tarea depende de sí misma |
| E07 | Ciclo de dependencias (el mensaje da el ciclo: `T-02 → T-04 → T-02`) |
| E08 | Enlace de `especificacion` a un fichero que no existe |
| E09 | Enlace a un ancla que no existe en el fichero |
| E10 | El hito no tiene sección «Validación funcional» con al menos una comprobación ✅ o 👁, o una ✅ no lleva su orden (6.2) |
| E11 | `abiertas.md` tiene puntos sin justificación |
| E12 | No hay ningún ADR de tipo `stack` |
| E13 | Una plantilla de `stack.plantillas` no existe en la versión de Menairos instalada |
| A01 | `motivo_critica` presente en una tarea no crítica |
| A02 | Tarea sin `area` explícita (con paralelismo > 1 en `menairos.toml`) |
| A03 | Las coherencias de `menairos.toml` de 2.2 |

H0.3 añade E14 y E15 (4.5).

**Anclas (E09).** Se calculan como GitHub: minúsculas; se quitan los signos de puntuación salvo
guiones; los espacios pasan a guiones; las letras con acento se conservan (`## Modelo de datos` →
`#modelo-de-datos`; `## Validación funcional` → `#validación-funcional`); los encabezados
repetidos llevan sufijo `-1`, `-2`.

**Formato de `abiertas.md` (E11).** Cada punto abierto es un encabezado `###` y debe llevar una
línea `**Justificación:**` no vacía. Un fichero sin puntos es válido.

**ADR de tipo `stack` (E12).** Los ADRs llevan una línea `- **Tipo:** …`; basta con que uno sea
`stack`.

**Casos límite** que deben tener test:

- YAML vacío; lista `tareas` vacía; claves con valor `null`;
- YAML con anclas y alias (`&`, `*`): se aceptan, pero un alias que crea un bucle es error de
  esquema;
- ficheros con BOM o con finales de línea CRLF;
- ids con distinto relleno (`T-1` frente a `T-01`): `T-1` no cumple el patrón;
- un ciclo largo (más de 50 tareas) y varios ciclos a la vez: se informan todos, cada uno una vez;
- anclas con acentos, con signos (`¿Qué?`), con código (`` `menairos.toml` ``) y repetidas;
- un enlace sin ancla (`hito-1.md`): vale y apunta al fichero entero;
- enteros enormes en `hito` y en los umbrales;
- el primer y el último elemento de cada lista.

### 2.4 `menairos spec publicar`

```
menairos spec publicar [--hito N] [--seco] [--json] [--raiz RUTA]
```

- **Precondición:** `spec validar` sin errores. Si los hay, no publica nada y sale con `1`.
- **Siempre por `gh api`** (ADR 0016), con un envoltorio fino que en los tests se sustituye por un
  doble con tope.
- **`--seco`** muestra lo que haría sin escribir nada en GitHub. `/validar-spec` lo enseña a Pedro
  antes de pedir el OK.

Lo que hace, en este orden:

1. **Etiquetas** de `diseno.md` 3.4 y una `area:*` por cada área del YAML: crea las que falten;
   no toca las que existen.
2. **Milestone** «Hito N — título»: lo crea si no existe (búsqueda por título exacto).
3. **Issues**, uno por tarea:
   - título `T-01 · título de la tarea`;
   - cuerpo desde la plantilla de issue: resumen, enlaces a las secciones de la especificación,
     criterios de aceptación, rama, dependencias, si necesita el portátil y quién la hace;
   - etiquetas `tipo:tarea`, `critica` si lo es, `area:*` y `modo:*` si la tarea fija modo;
   - una marca oculta en el cuerpo, `<!-- menairos:tarea=T-01 hito=0 -->`, que es lo que usa la
     idempotencia (no el título, que Pedro puede cambiar).
4. **Dependencias nativas «blocked by»**, una por cada `depende_de`, después de crear todos los
   issues.

**Idempotencia.** Una segunda ejecución sin cambios no hace ninguna escritura. Con cambios en el
YAML:

| Situación | Qué hace |
| --- | --- |
| Tarea nueva | Crea su issue y sus dependencias |
| Tarea cambiada, issue abierto | Actualiza el cuerpo y las etiquetas, y lo informa |
| Tarea cambiada, issue cerrado | No toca nada; lo informa como aviso |
| Tarea borrada del YAML | No cierra ni borra el issue; lo informa como aviso |
| Dependencia nueva o quitada | Añade o quita la relación «blocked by» |

**Nunca borra ni cierra nada** (las reglas del método v2: nada de `DELETE` por la API).

**Salida:** con `--json`, `{"creados": [...], "actualizados": [...], "sin_cambios": [...],
"avisos": [...]}`; sin `--json`, un resumen legible.

**Casos límite** que deben tener test (con el doble de GitHub):

- repo sin ninguna etiqueta ni milestone;
- un issue con la marca oculta, pero editado a mano por Pedro (título cambiado): se reconoce por
  la marca;
- dos issues con la misma marca (un error de antes): para y lo informa, sin escribir;
- fallo de la API a mitad de la publicación: la siguiente ejecución completa lo que faltaba sin
  duplicar;
- paginación: más de 100 issues o etiquetas en el repo;
- una dependencia a una tarea cuyo issue está cerrado: se crea igual.

**Por verificar en esta tarea:** la ruta REST para añadir y quitar dependencias «blocked by»
(el método v2 solo la leía: `GET /repos/{o}/{r}/issues/{n}/dependencies/blocked_by`). Se comprueba en la
documentación de GitHub y contra el repo de prueba antes de implementarla.

### 2.5 Hecho cuando

- Los tres esquemas están en `esquemas/`, con un ejemplo válido y uno inválido por regla en
  `tests/data/`.
- `menairos spec validar` detecta los 13 errores y los 3 avisos de 2.3, cada uno con su test, y los
  casos límite tienen test.
- `menairos spec publicar` es idempotente contra el doble de GitHub y tiene test cada caso de la
  tabla de idempotencia y cada caso límite.
- Una publicación real contra `pdromer0/menairos-prueba` con un YAML de ejemplo, ejecutada dos
  veces: la segunda no escribe nada. Anotado en el anexo.

---

## 3. H0.2 — Plantillas y entorno

### 3.1 Qué se construye

- Las **plantillas de documentos** que usan `/crear-spec`, `/implementar` y `/cerrar-hito`.
- Las **plantillas de stack** `base` y `python-uv`, que cumplen el contrato común.
- **`menairos entorno`**, con sus cuatro capas y su modo `--comprobar`.
- El comando **`/preparar-entorno`** del plugin, una capa fina sobre la CLI.

### 3.2 Plantillas de documentos

En `plantillas/docs/`. Los encabezados son **fijos**: los usan las anclas de las tareas y las
comprobaciones de `spec validar`, así que cambiar uno es un cambio de contrato.

| Plantilla | Secciones fijas |
| --- | --- |
| `producto.md` | Visión · Problema · Usuarios · Casos de uso · Alcance · Restricciones · Criterios de éxito |
| `diseno.md` | Arquitectura · Componentes · Datos · Stack · Entornos · Coste · Riesgos |
| `hitos.md` | Vista general · un `##` por hito con Objetivo, Contenido, Criterios de salida y Demo funcional |
| `hito-N.md` | Objetivo · una sección por bloque de trabajo · Validación funcional · Anexo |
| `hito-N.tareas.yaml` | El esqueleto del esquema, con una tarea de ejemplo comentada |
| `abiertas.md` | Explicación del formato (`###` + `**Justificación:**`) y ningún punto |
| `adr.md` | Estado · Fecha · Tipo · Decidido por · Reversibilidad · Contexto · Decisión · Alternativas consideradas · Consecuencias |
| `decisiones-tarea.yaml` | `tarea` y `decisiones: []` |
| `anexo-tarea.md` | Qué se hizo · Decisiones del diff · Medidas · Versiones incorrectas · Revisión · Pendiente |
| `revision-hito-N.md` | Bloqueantes · Mejoras · Preguntas para Pedro · Predicción de paradas (4.3) |
| `inventario-mvp.md` | Estructura · Stack detectado · Funcionalidades · Datos · Calidad · Riesgos (4.2) |
| `pull_request_template.md` | Resumen · Closes #N · Decisiones · Comprobaciones · Revisión propia · Pendiente · Métricas |
| Plantillas de issue | Tarea, bug e idea |

**Sustitución de valores sin dependencias:** los huecos se escriben `{{clave}}`
(`{{proyecto.nombre}}`, `{{hito.numero}}`) y los rellena la CLI con los valores de
`menairos.toml`. No hay lógica dentro de las plantillas (nada de Jinja): si queda un hueco sin
rellenar o se pide una clave que no existe, es un error.

### 3.3 Plantillas de stack y contrato común

Cada plantilla de stack es una carpeta en `plantillas/stacks/` con un **manifiesto
`plantilla.toml`**:

```toml
[plantilla]
nombre = "python-uv"
version = "1.0.0"
requiere = ["base"]

[herramientas]                   # lo que comprueba la capa local
uv = ">=0.9"
python = "3.14"

[ordenes]                        # el contrato común: /implementar solo usa estas
formato = "uv run ruff format ."
formato_fichero = "uv run ruff format {fichero}"   # para el hook PostToolUse (5.5)
extensiones_formato = [".py"]
lint = "uv run ruff check ."
tipos = "uv run pyright"
tests_area = "uv run pytest {rutas}"
n1 = "scripts/n1.sh"
n2 = "scripts/n2.sh"
n3 = "scripts/n3.sh"

[ficheros]
fusionables = [".pre-commit-config.yaml", ".gitignore", "AGENTS.md"]

[[comprobaciones]]               # las deliberadas (3.6)
nombre = "formato"
provoca = "fichero Python mal formateado"
salta = "pre-commit"
mensaje = "ruff format"
```

- **Las versiones del manifiesto** se fijan al crear la plantilla, comprobadas con herramientas
  en ese momento.
- **Composición:** la CLI aplica las plantillas en el orden de `requiere` y después el de
  `stack.plantillas`. Si dos plantillas traen el mismo fichero y no es fusionable, es un error.
  Los fusionables se combinan por secciones: los hooks de pre-commit se suman, las líneas de
  `.gitignore` se unen, y cada plantilla aporta su sección a `AGENTS.md`.

**`base`** (todo proyecto la lleva): `.gitignore`; pre-commit con gitleaks y las comprobaciones
de higiene (fin de fichero, espacios finales, YAML y TOML válidos); plantillas de issue y de PR;
`SECURITY.md`; el workflow `ci` fino, que llama a la orden `n3` del contrato; `AGENTS.md` y
`CLAUDE.md` base; `.claude/settings.json` según el modo, con las prohibiciones del método v2 (fusión,
push forzado, push a `main`, `DELETE` por la API) y el marketplace y el plugin de Menairos.

**`python-uv`:** `pyproject.toml` (Python 3.14; ruff; pyright en modo estándar; pytest con
`timeout = 60` y la marca `slow`); `src/{{paquete}}/__init__.py`; `tests/test_humo.py`;
`.python-version`; hooks locales de ruff y pyright con `uv run --frozen`; y los scripts del
contrato:

| Script | Qué hace | Cuándo |
| --- | --- | --- |
| `scripts/n1.sh [rutas…]` | ruff, pyright y los tests de las rutas dadas | Antes de cada commit |
| `scripts/n2.sh` | La rápida con sello: solo si cambió algo desde el último verde (sello en `.cache/menairos/`) | Al final de cada turno (hook `Stop`) |
| `scripts/n3.sh` | Formato comprobado, lint, tipos y todos los tests | Antes del push y en el CI |

Los tres salen con `0` en verde y `1` en rojo, y dicen qué ejecutaron (lección de un proyecto anterior: un verde
sin decir qué revisó no vale).

### 3.4 `menairos entorno`

```
menairos entorno [local|repo|github|nube] [--comprobar] [--json] [--raiz RUTA]
```

Sin capa, recorre las cuatro en orden. Cada paso **comprueba, actúa si hace falta y vuelve a
comprobar**; repetir la orden no cambia nada si ya está todo puesto. Cada paso termina en uno de
cuatro estados: `ok` (ya estaba), `hecho` (lo ha hecho ahora), `manual` (le toca a Pedro, con
instrucciones) o `error`.

| Capa | Qué comprueba y hace |
| --- | --- |
| **local** | Herramientas del manifiesto y sus versiones (`git`, `gh` con sesión, `uv`, `claude`; `codex` y `docker` si hacen falta); el repo bajo `~/proyectos/` y nunca en `/mnt/c`; `.wslconfig` con memoria y swap (solo aviso); `pre-commit install` |
| **repo** | Aplica las plantillas; `uv sync`; primer commit en `main` si el repo es nuevo |
| **github** | Crea el repo con la visibilidad de `menairos.toml` (con `--source --push`); ruleset de `main` (solo en público o con GitHub Pro; si no, aviso); escaneo de secretos y protección de push; Dependabot; informe privado de vulnerabilidades; fusión solo por *squash*; borrar la rama al fusionar; auto-merge permitido; etiquetas (las mismas de `spec publicar`) |
| **nube** | Genera `scripts/entorno-nube.sh` (instala la CLI de Menairos fijada a la versión, `uv sync`, comprueba `gh`, amplía el tiempo máximo de los comandos para la N3) y las instrucciones para pegarlo en el entorno de la nube de Claude Code y de Codex |

Decisiones de comportamiento:

- **La CLI no instala herramientas del sistema** (uv, gh, Docker…): las comprueba y, si faltan o
  son viejas, da la orden exacta para instalarlas como paso `manual`. Solo actúa dentro del
  proyecto y en GitHub.
- **En un repo que ya existe (modo MVP), nunca sobrescribe:** aplica lo que falta y lista los
  conflictos (un `pyproject.toml` que ya existe, un CI distinto) para que los resuelva
  `/preparar-entorno` con Pedro.
- **`menairos.toml` lo crea `/crear-spec`**, porque es donde se decide el stack.
  `/preparar-entorno` lo necesita y para si no existe.

**Pasos manuales de Pedro**, al final y en una lista: crear la GitHub App `menairos-agente` e
instalarla (en H0 solo se deja preparado; se usa en H1); CodeQL; la aprobación de los PR de forks;
y pegar el script de entorno en la nube. Objetivo: **15 minutos como mucho**, medido en el
anexo.

**`--comprobar`** no escribe nada: verifica por la API todo lo que se puede verificar (también lo
que Pedro hizo en la web) y marca como `manual` lo que no tiene API (el entorno de la nube), con
lo que hay que mirar.

### 3.5 `/preparar-entorno`

El comando del plugin, una capa fina sobre la CLI:

1. Lee `menairos.toml`; si no existe, para y pide `/crear-spec`.
2. Ejecuta `menairos entorno --json` y lo explica en pocas líneas.
3. **Pide permiso antes de las escrituras en GitHub** (crear el repo, cambiar ajustes) en los
   modos manual y didáctico.
4. Si hay conflictos con ficheros que ya existen, los resuelve con Pedro, uno a uno.
5. Lanza las comprobaciones deliberadas (3.6).
6. Enseña la lista de pasos manuales y, cuando Pedro dice que están hechos, ejecuta
   `menairos entorno --comprobar` hasta tenerlo en verde.
7. Si la especificación del hito está aprobada y sin publicar (4.3), ofrece publicarla ahora,
   con el `--seco` delante y el OK de Pedro.

En modo didáctico, explica antes qué es cada pieza (ruleset, pre-commit, gitleaks…).

### 3.6 Comprobaciones deliberadas automáticas

```
menairos entorno comprobaciones [--json]
```

- Las comprobaciones **locales** del manifiesto (formato, tipos, clave falsa, test que falla) se
  ejecutan en un **worktree temporal**: provoca el fallo, lanza el hook o la N3, comprueba que
  falla **con el mensaje esperado** y lo deshace. El árbol de trabajo nunca se toca.
- Las **remotas** (que el CI exige el check y que el ruleset rechaza el push a `main`) no se
  provocan: se verifican leyendo por la API la configuración del ruleset y del check obligatorio.
- La clave falsa se inventa en cada ejecución con el formato de un proveedor real y nunca se
  escribe fuera del worktree temporal.

### 3.7 Casos límite

Deben tener test (los de GitHub, con el doble con tope):

- carpeta vacía, carpeta con ficheros sueltos y repo con historia;
- el repo existe en GitHub pero no en local, y al revés;
- una plantilla que no existe; dos plantillas que traen el mismo fichero no fusionable;
- un hueco `{{…}}` sin rellenar, y una clave que no existe en `menairos.toml`;
- `gh` sin sesión iniciada; una herramienta por debajo de la versión del manifiesto;
- repo en `/mnt/c/…`;
- repo privado sin GitHub Pro (el ruleset devuelve error): aviso, no fallo;
- un fallo a mitad de la capa github: la siguiente ejecución completa lo que faltaba;
- `--comprobar` repetido dos veces seguidas: mismo resultado, ninguna escritura.

### 3.8 Hecho cuando

- `base` y `python-uv` existen con su manifiesto, y un proyecto generado con ellas en una carpeta
  temporal pasa su propia N3 (test marcado `slow`).
- Las comprobaciones deliberadas automáticas fallan donde deben, con su mensaje, y el árbol queda
  intacto.
- `menairos entorno` sobre `pdromer0/menairos-prueba` termina con `--comprobar` en verde.
- Los pasos manuales de Pedro se cronometran y caben en 15 minutos. Anotado en el anexo.
- Los casos límite de 3.7 tienen test.

---

## 4. H0.3 — Especificar

### 4.1 Qué se construye

- **`/crear-spec`**, en sus tres variantes: lluvia de ideas, MVP y `--siguiente`.
- El subagente **`inventario-mvp`**.
- **`/validar-spec`**, con su revisor configurable (subagente `revisor-spec` de Claude o Codex).
- Las órdenes de la CLI que los apoyan: `menairos spec nuevo`, `menairos spec estado` y las
  comprobaciones nuevas E14 y E15 de `spec validar`.

### 4.2 `/crear-spec`

```
/crear-spec [--mvp RUTA_O_REPO] [--siguiente]
```

**Dónde vive la especificación desde el primer minuto:** en una carpeta de git local
(`~/proyectos/<nombre>`), que `menairos spec nuevo` crea con `git init`, el esqueleto de
documentos de las plantillas y un `menairos.toml` de borrador. Así la especificación está
versionada desde el principio. El repo de GitHub lo crea después `/preparar-entorno`.

**El orden completo de un proyecto nuevo:**

```
/crear-spec  →  /validar-spec (OK de Pedro)  →  /preparar-entorno  →  publicación de los issues
```

La publicación necesita el repo en GitHub: si ya existe, la hace `/validar-spec`; si no,
`/validar-spec` deja la especificación **aprobada** y `/preparar-entorno` la publica al terminar
(3.5, paso 7).

**Las fases.** Cada fase hace preguntas cerradas (opciones para elegir, como mucho unas pocas por
turno), escribe su parte de los documentos al cerrarse y hace un commit:

| Fase | Qué se decide | Dónde se escribe |
| --- | --- | --- |
| 1. Visión y problema | Para qué y para quién | `producto.md` §Visión, §Problema |
| 2. Usuarios y casos de uso | Quién lo usa y qué hace (CU-xx) | `producto.md` §Usuarios, §Casos de uso |
| 3. Alcance y restricciones | Qué entra, qué no, límites, criterios de éxito | `producto.md` §Alcance, §Restricciones, §Criterios de éxito |
| 4. Stack y coste | Dos o tres opciones con sus pros y contras; decide Pedro | `diseno.md` §Stack, §Coste; ADR de tipo `stack`; `menairos.toml` [stack] |
| 5. Arquitectura y datos | Componentes, datos, riesgos | `diseno.md` §Arquitectura, §Componentes, §Datos, §Riesgos |
| 6. Entornos y modo | Dónde corre, visibilidad, modo de trabajo | `diseno.md` §Entornos; `menairos.toml` |
| 7. Hitos | Hoja de ruta con objetivos y demo funcional de cada hito | `hitos.md` |
| 8. Primer hito y tareas | La especificación detallada y las tareas | `hito-1.md`, `hito-1.tareas.yaml` |

- **Si el stack no tiene plantilla** (fase 4), avisa en ese momento de que el hito 0 incluirá
  crearla (punto 11) y lo anota en `abiertas.md`.
- **El primer hito especificado es el 1:** en un proyecto, el hito 0 es la preparación del
  entorno, que hace `/preparar-entorno` sin tareas. La excepción es un stack sin plantilla, donde
  el hito 0 sí tiene tareas (crear la plantilla).
- **Reanudar:** el progreso se guarda en `.menairos/estado-spec.toml`, versionado: fase actual,
  fases cerradas y un resumen de cada decisión. Tras un `/clear` o en otra sesión,
  `menairos spec estado` dice dónde se quedó y la conversación sigue desde los ficheros, no desde
  el historial.
- **Volver atrás:** si Pedro cambia una decisión de una fase cerrada, esa fase se reabre y las
  posteriores que dependen de ella se marcan «a revisar» (por ejemplo, cambiar el stack reabre la
  fase 5).
- **Tokens:** la conversación la lleva Opus (punto 17); las lecturas grandes (un MVP, documentos
  largos) las hace un subagente que devuelve un resumen.

**Modo MVP** (`--mvp RUTA_O_REPO`):

0. **Fase 0, antes de nada:** ¿se evoluciona el repo del MVP o se empieza uno nuevo? Y, si el
   resultado va a ser público, **gitleaks sobre toda la historia del MVP** antes de tocar nada:
   una demo hecha deprisa puede tener claves en commits antiguos.
1. El subagente `inventario-mvp` (Sonnet, solo lectura) recorre el MVP y escribe
   `docs/inventario-mvp.md`: estructura, stack detectado, funcionalidades, datos, calidad (tests,
   CI) y riesgos. Cada elemento lleva un hueco de decisión: **mantener**, **cambiar** o
   **descartar**.
2. Las fases 1 a 8 son las mismas, pero cada una empieza por lo que hay en el inventario.
3. Al terminar, ningún elemento del inventario puede quedar sin decidir (E14).

**`--siguiente`** (especificar el hito N+1):

- Entrada: `hitos.md`, el informe de cierre del hito anterior (decisiones «corregir», lecciones,
  desviaciones, pendientes) y `abiertas.md`.
- Solo recorre las fases 7 y 8; reabre la 4, la 5 o la 6 si el cierre pide cambiar el stack, la
  arquitectura o los entornos.

### 4.3 `/validar-spec`

```
/validar-spec [--hito N]
```

1. **Capa 1:** `menairos spec validar`. Si hay errores, los enseña y para; el agente autor puede
   corregirlos con Pedro antes de repetir.
2. **Capa 2, según `revisores.spec` de `menairos.toml`:**
   - `claude`: el subagente `revisor-spec` (Opus, solo lectura, contexto limpio);
   - `codex`: `codex exec` en modo no interactivo y de solo lectura, con el prompt del revisor en
     un fichero y la salida a otro. *Por verificar en la tarea:* las opciones exactas de
     `codex exec` para solo lectura y salida a fichero. Si Codex no está disponible (sin sesión,
     sin cuota), lo dice y ofrece usar Claude.
3. **El revisor recibe solo los documentos** (`producto.md`, `diseno.md`, `hitos.md`, el hito y
   sus tareas, `abiertas.md`), nunca la conversación de `/crear-spec`, y revisa lo del punto 10:
   coherencia entre documentos, ambigüedad, criterios comprobables, cobertura de los casos de uso,
   tamaño de las tareas, etiqueta `critica` y predicción de paradas.
4. **Informe con formato fijo**, en `docs/specs/revision-hito-N.md`:
   - secciones **Bloqueantes**, **Mejoras**, **Preguntas para Pedro** y **Predicción de paradas**;
   - cada hallazgo con id (`R-01`), el documento y la sección a los que se refiere, el cambio que
     propone y un estado (`abierto`, `resuelto`, `descartado` con motivo).
5. **El autor aplica** los cambios que Pedro acepte; las preguntas se le hacen a Pedro; las
   **paradas predichas** se convierten en preguntas adelantadas (punto 15) y sus respuestas
   quedan como decisiones de Pedro en el hito.
6. **Segunda ronda** si quedaron bloqueantes. Si después de la segunda sigue habiendo, se vuelve
   a `/crear-spec` (punto 10).
7. **Publicación:** `menairos spec publicar --seco`, que Pedro ve, y con su OK la publicación de
   verdad. Si el repo aún no existe, la especificación queda aprobada y la publica
   `/preparar-entorno`.

### 4.4 Lo que aporta la CLI

| Orden | Qué hace |
| --- | --- |
| `menairos spec nuevo NOMBRE [--mvp RUTA]` | Crea la carpeta, `git init`, el esqueleto de documentos y el borrador de `menairos.toml` y de `.menairos/estado-spec.toml` |
| `menairos spec estado [--json]` | Fase actual, fases cerradas, fases «a revisar», y si el hito está aprobado o publicado |
| `menairos spec fase cerrar N` / `reabrir N` | Actualiza `.menairos/estado-spec.toml` y marca las fases posteriores que dependen de ella |

### 4.5 Comprobaciones nuevas de `spec validar`

| Código | Comprobación |
| --- | --- |
| E14 | Un elemento de `inventario-mvp.md` sin decisión (solo en modo MVP) |
| E15 | `revision-hito-N.md` con bloqueantes en estado `abierto`: no se puede publicar |
| A04 | Fases marcadas «a revisar» en `.menairos/estado-spec.toml` |

### 4.6 Casos límite

- La sesión se corta a mitad de una fase: se retoma desde la última fase cerrada, sin perder las
  anteriores.
- Pedro cambia el stack cuando ya está en la fase 8: se reabren las fases 4 y 5, y la 8 queda «a
  revisar».
- Un stack sin plantilla: aviso en la fase 4, y `abiertas.md` y el hito 0 lo recogen.
- Un MVP grande: el inventario se hace por carpetas y el subagente devuelve un resumen por carpeta.
- Un MVP sin tests, sin CI o con claves en la historia: lo recoge el inventario como riesgo; las
  claves bloquean hacerlo público hasta limpiarlas.
- Codex sin sesión o sin cuota: se dice y se ofrece Claude.
- El revisor devuelve un informe que no cumple el formato: se le pide una vez que lo rehaga; si
  vuelve a fallar, se informa a Pedro.
- Dos hallazgos contradictorios: van los dos a «Preguntas para Pedro».
- Un hito que, tras la revisión, se queda sin tareas: E02 (el esquema exige al menos una).

### 4.7 Hecho cuando

- En el repo de prueba, `/crear-spec` con una idea pequeña recorre las ocho fases y deja los
  documentos con el formato de las plantillas; un `/clear` a mitad se retoma bien (demo, punto 1).
- `/validar-spec` detecta un ciclo de dependencias sembrado a propósito (demo, punto 2) y, con el
  revisor de Claude y con el de Codex, devuelve un informe con el formato de 4.3 (demo, punto 3).
- La publicación funciona en los dos caminos: con el repo ya creado y desde `/preparar-entorno`.
- El modo MVP funciona sobre un MVP de ejemplo pequeño (en los datos de test), con el inventario
  completo y E14 detectando un elemento sin decidir.
- `--siguiente` funciona con un informe de cierre de ejemplo.
- E14, E15 y A04 tienen test, y los casos límite de 4.6 tienen test donde son deterministas.

---

## 5. H0.4 — Implementar

### 5.1 Qué se construye

- **`/implementar`** en los modos manual y didáctico: el ciclo de `tarea.md` del método v2,
  generalizado y apoyado en la CLI.
- **`/sincronizar`**, el paso después de la fusión (el `/sincronizar` del método v2).
- Las órdenes **`menairos contexto`**, **`menairos decisiones validar`** y
  **`menairos sincronizar`**.
- Los subagentes **`revisor-plan`** y **`mutante`**, traídos del método v2.
- Los **hooks** del plugin: `SessionStart`, `Stop`, `PostToolUse` y el anti-bucle.

### 5.2 `/implementar`

```
/implementar N [notas efímeras] [--modo manual|didactico]
```

N es el número del issue. Las notas duraderas van como comentario del issue, como en el método v2.

**Fase 1 — en modo plan (solo lectura):**

1. **`menairos contexto N --json`** (5.3) reúne todo lo que la tarea necesita. Si el issue está
   cerrado, es un PR, tiene dependencias abiertas o es `donde: local` y la sesión está en la
   nube, **para y lo dice**.
2. **El modo efectivo**, de más a menos prioridad: `--modo` del comando, la etiqueta `modo:*` de
   la tarea, el modo del hito y `modo.defecto` de `menairos.toml` **[propuesta]**.
3. **Plan con los 8 apartados** de `tarea.md` (contexto; lo que el plan interpreta; diferencias
   con las notas; valores a mano con su cálculo ejecutado; casos límite; versiones incorrectas;
   comprobaciones; cuándo parar). Encabezado: rama, modo, si es crítica y el esfuerzo de
   `/code-review` (alto en las críticas, medio en el resto).
4. **En modo didáctico**, antes del plan: una sección **Conceptos** que explica lo nuevo de la
   tarea; el plan añade **«Qué vas a aprender»**; y Pedro pregunta hasta entenderlo antes de
   aprobar.
5. **Si la tarea es crítica**, el subagente `revisor-plan` revisa el plan con contexto limpio y su
   informe va al principio (como en el método v2).
6. Pedro aprueba el plan.

**Fase 2 — implementación:**

1. La rama del issue (nunca la `claude/*` que propone la nube) y la etiqueta `en-curso`, por REST.
2. Un commit por paso lógico con la orden `n1` del contrato; la `n2`, en el hook `Stop`.
3. El **fichero de decisiones** de la tarea, `docs/specs/hito-N/decisiones/T-xx.yaml`, que se
   valida con `menairos decisiones validar T-xx` (5.4).

**Fase 3 — antes del push** (como en el método v2): `/code-review` con el esfuerzo del plan;
clasificación de todos los hallazgos antes de tocar nada; correcciones con N1; **una sola N3**
(orden `n3` del contrato); entrada del anexo; descripción del PR con la plantilla y `Closes #N`;
push y PR por REST; hora de aprobación del plan y de apertura del PR en las métricas.

**Fase 4 — ajustes de la revisión:** las mismas reglas que antes del push, con la sección
«Ajustes de la revisión» del PR y el anexo al día.

### 5.3 `menairos contexto`

```
menairos contexto N [--json] [--raiz RUTA]
```

Reúne en una sola salida lo que necesita la sesión, para que el modelo no lo reconstruya con diez
llamadas:

| Campo | Qué es |
| --- | --- |
| `issue` | Número, título, estado, etiquetas, cuerpo; error si es un PR |
| `tarea` | La entrada del YAML (por la marca oculta): criterios, crítica, `donde`, `quien`, `modo`, rama |
| `dependencias` | Las «blocked by» nativas con su estado; las abiertas bloquean |
| `comentarios` | **Solo los de Pedro y los de la App** (punto 18); cuenta los ignorados de otros usuarios |
| `especificacion` | El texto de las secciones enlazadas, extraído por sus anclas |
| `modo` | El modo efectivo y de dónde sale |
| `entorno` | Si la sesión es local o en la nube, y si choca con `donde` |
| `desfase` | Aviso si el cuerpo del issue ya no coincide con el YAML |

Si las secciones enlazadas pasan de un tamaño razonable, avisa y da los rangos para leerlas por
partes (la lección del método v2 de leer las especificaciones grandes por secciones).

### 5.4 El fichero de decisiones en los modos manual y didáctico

- **Lo que el plan interpreta** y Pedro aprueba al aprobar el plan se registra con
  `decidido_por: pedro` **[propuesta]**: quien lo decidió de verdad fue Pedro, aunque lo propusiera
  el agente.
- **Lo que el agente decide durante la implementación** y no estaba en el plan se registra con
  `decidido_por: agente`.
- Con esto, el registro ya funciona en el H0 y el H1 solo añade el modo automático encima.

### 5.5 Hooks

Todos se implementan como **`menairos hook <nombre>`, en Python** **[propuesta]**, no en bash con
`jq` (en el método v2, sin `jq` los hooks fallaban; así no hay esa dependencia y tienen tests).

| Hook | Qué hace |
| --- | --- |
| `SessionStart` | Mete en el contexto la rama, la última etiqueta, el hito en curso, la tarea `en-curso` y `git status -sb`. Solo git local |
| `Stop` | Ejecuta la orden `n2` (la rápida con sello); no hace nada en modo plan; avisa de que empieza, para que la espera no parezca un cuelgue |
| `PostToolUse` (Edit, Write) | Formatea el fichero editado con `formato_fichero`, si su extensión está en `extensiones_formato` del manifiesto |
| Anti-bucle (`PostToolUse` + `PreToolUse` de Bash) | `PostToolUse` anota cada comando con su código de salida y una huella del árbol de trabajo; `PreToolUse` bloquea un comando si ya falló **3 veces seguidas sin que cambiara ningún fichero** entre medias (punto 17) |

- **El anti-bucle también está activo en manual** **[propuesta]**: es barato y protege igual. En
  manual, su mensaje le dice al agente que pare y pregunte a Pedro; en automático (H1), que escale.
- La huella del árbol se calcula con `git status --porcelain` y `git diff` de lo no confirmado, y
  se guarda en `.cache/menairos/`.

### 5.6 `/sincronizar`

```
/sincronizar [PR]
```

Separado de `/implementar` **[propuesta]**, como en el método v2 (se lanza tras la fusión y después de
`/clear`), apoyado en `menairos sincronizar`: comprueba por REST que el PR está fusionado (`merged`
es `true`; nunca da un PR por fusionado sin esa comprobación); actualiza `main` con
`git pull --ff-only`; borra la rama local solo si todos sus commits entraron; quita la etiqueta
`en-curso`; `uv sync` (o la orden equivalente del stack) si cambiaron las dependencias; y enseña la
siguiente tarea desbloqueada del hito.

### 5.7 Subagentes

- **`revisor-plan`** (Opus, solo lectura): el del método v2. Lee el issue, las notas y la
  especificación, recalcula los valores a mano con código independiente y devuelve «Lo que el plan
  interpreta», «Diferencias con las notas» y «Valores que no cuadran». Activo por defecto.
- **`mutante`** (Sonnet, en un worktree aislado): aplica una versión incorrecta, ejecuta los tests
  predichos, la deshace y devuelve «predicción frente a observado». Módulo **inactivo por
  defecto**, con el disparador del método v2 (más de 2 versiones incorrectas por tarea, o el árbol se
  ensucia).

### 5.8 Codex como implementador

Cuando una tarea es `quien: codex` (solo en modo manual), Codex no tiene el plugin: sigue el ciclo
desde `AGENTS.md`, que lo describe sin depender de Claude Code, y puede usar las mismas órdenes de
la CLI (`menairos contexto`, `decisiones validar`, `n1`–`n3`). Pide permiso para el push, como en
el método v2.

### 5.9 Casos límite

- El issue está cerrado, es un PR o tiene dependencias abiertas: para y lo dice.
- Un issue creado a mano, sin la marca oculta: funciona solo con el cuerpo del issue, con un aviso.
- El YAML cambió después de publicar: `desfase` lo avisa.
- La rama ya existe y va por detrás de `main`: lo dice antes de seguir.
- `donde: local` en una sesión en la nube: para y lo dice.
- La N3 falla dos veces: para y lo dice (como en el método v2).
- Comentarios de otros usuarios en el issue: no llegan al modelo; se dice cuántos se ignoraron.
- La sesión no está en modo plan al empezar: lo pide antes de presentar el plan.
- El anti-bucle: un comando que falla 3 veces **con** ediciones entre medias no se bloquea; sin
  ediciones, sí.

### 5.10 Hecho cuando

- Una tarea en modo manual **en una sesión en la nube** de punta a punta: plan de 8 apartados, PR
  con anexo y fichero de decisiones (demo, punto 5).
- Otra tarea **en local y en modo didáctico**, con los conceptos explicados antes (demo, punto 6).
- **Las tareas que quedan del H0 (H0.5) se hacen con `/implementar`.**
- `menairos contexto` tiene test del filtro de comentarios, de las dependencias abiertas, del
  `desfase` y del choque con `donde`.
- El anti-bucle tiene test con secuencias falsas: bloquea sin cambios en el árbol y no bloquea con
  cambios.
- `menairos sincronizar` tiene test con el doble de GitHub, incluido el PR que no está fusionado.

---

## 6. H0.5 — Cierre y prueba

### 6.1 Qué se construye

- **`/cerrar-hito` básico**, con `menairos informe` y `menairos cierre --aprobar`, sin las partes
  del modo automático (consumo, guardarraíles, ajuste de autonomía, resumen de aprendizaje), que
  llegan en el H1.
- **La prueba de punta a punta** en `pdromer0/menairos-prueba`: la demo funcional del hito.
- **Las verificaciones pendientes** que alimentan el diseño del H1.
- **El cierre del propio H0** con el propio Menairos y la versión `v3.0.0`.

### 6.2 El informe del hito

```
menairos informe N [--json] [--raiz RUTA]
```

Genera `docs/specs/hito-N/informe.md`, que va en el PR «Cierre del hito N». En el H0 tiene cinco
secciones:

| Sección | De dónde sale |
| --- | --- |
| **Decisiones marcadas** | Los ficheros de decisiones del hito; solo las marcadas (difíciles de revertir o de impacto alto). Cada una con una línea `Veredicto: pendiente` que Pedro cambia |
| **Validación funcional** | La sección del mismo nombre de `hito-N.md`, como lista de casillas |
| **Métricas** | Por REST: tareas, PR, tiempo de cada PR (de abierto a fusionado), hora de aprobación del plan (de la sección de métricas del PR), rondas de revisión; y la duración de las N3 que recoja el anexo |
| **Desviaciones y pendientes** | Las secciones «Pendiente» y las desviaciones de las entradas del anexo |
| **Disparadores del método** | La comprobación de los disparadores de los módulos (lo que hacía `disparadores.sh` del método v2), pasada a la CLI |

**Cómo marca Pedro** **[propuesta]**: directamente en el informe, que es lo que está leyendo.

- En las decisiones, cambia `Veredicto: pendiente` por `aceptada`, `corregir` o `elevar-a-adr`.
- En la validación funcional, marca `[x]` lo que funciona o escribe `[!] fallo: …` con lo que ha
  visto.
- `--aprobar` vuelca después los veredictos a los ficheros de decisiones (campo `revision`), de
  forma que los YAML siguen siendo la fuente.

**Las comprobaciones ✅ llevan su orden** **[propuesta]**: en la validación funcional de
`hito-N.md`, cada comprobación ✅ termina con la orden que la comprueba
(`- ✅ La capa 1 detecta un ciclo — \`menairos spec validar --raiz tests/data/ciclo\``). El agente
las ejecuta antes de abrir el PR de cierre y deja marcadas las que pasan. E10 lo comprueba: una ✅
sin orden es un error. Las 👁 son solo de Pedro.

### 6.3 `menairos cierre N --aprobar`

El cierre en un solo comando (punto 16), en su versión del H0:

1. Comprueba que el informe está completo: ningún `Veredicto: pendiente` y ninguna casilla 👁 sin
   marcar. Si falta algo, para y dice qué.
2. Vuelca los veredictos a los ficheros de decisiones.
3. Crea un issue por cada decisión `corregir`, en el milestone del hito siguiente (o en
   «Backlog» si aún no existe). Con la marca oculta, como en `spec publicar`: repetir la orden no
   los duplica.
4. Si hay fallos funcionales (`[!]`), crea el milestone del **mini-hito de corrección** (N.1) con
   un issue por fallo. En el H0 se trabaja en modo manual; en el H1 arrancará solo.
5. Escribe un ADR por cada decisión `elevar-a-adr`, con «Decidido por: agente, validado por
   Pedro».
6. Fusiona el PR de cierre, crea la etiqueta `vX.Y.Z` y publica la Release.
7. Abre en el repo de Menairos los issues de lecciones sobre el método (para Menairos mismo, en su
   propio repo).
8. Termina diciendo qué sigue: el mini-hito de corrección o `/crear-spec --siguiente`.

**Protección** **[propuesta]**: como este comando fusiona, el `.claude/settings.json` de las
plantillas lo deja con una regla `ask` (`menairos cierre * --aprobar`). Un agente nunca puede
lanzarlo sin que Pedro lo confirme en ese momento, aunque las demás fusiones sigan denegadas.

**Etiqueta y Release:** si el token de la sesión no puede crearlas (con el método v2, la nube daba 403),
el comando lo dice y deja la orden exacta para lanzarla en local.

### 6.4 La prueba de punta a punta

En `pdromer0/menairos-prueba`, con una idea pequeña inventada para la prueba, se recorre la demo
funcional del hito (`../hitos.md`) de principio a fin: `/crear-spec` → `/validar-spec` con un ciclo
sembrado → publicación → `/preparar-entorno` → una tarea con `/implementar` en la nube → otra en
local y en modo didáctico → `/cerrar-hito` con `--aprobar`.

Se cronometran tus pasos (especificación, aprobaciones, pasos manuales, revisión del cierre) para
compararlos después con un hito manual del método v2 y con el piloto.

### 6.5 Verificaciones pendientes

Cada una se prueba con lo mínimo, sin construir todavía el modo automático, y su resultado va al
anexo, a `abiertas.md` y a la especificación del H1:

| Verificación | Cómo se prueba |
| --- | --- |
| `/implementar` en una sesión en la nube | Ya cubierta por la demo, punto 5 |
| El plugin en `claude-code-action` | Un workflow mínimo en el repo de prueba que lanza `claude-code-action` con el token OAuth de Max y pide la skill `menairos-hola` |
| Sesiones largas con el token OAuth de Max | El mismo workflow con una tarea sintética de 20 a 30 minutos; se mira que no corte el token ni el tiempo del job |
| El consumo de cada sesión | Lo que devuelve ese workflow: si trae el uso de tokens, se documenta de dónde se lee |
| Codex como check bloqueante | Un PR de prueba con `@codex review` y un workflow que intenta convertir su revisión en un check; se documenta si es viable |
| Etiqueta y Release con el token de una App | Con la App `menairos-agente` ya creada (6.6) y un workflow que crea una etiqueta y una Release de prueba |
| Destinos de red del job del agente | Se ejecuta el workflow con una herramienta de control de salida en modo solo registro y se anota la lista de destinos que necesita |

### 6.6 Cierre del propio H0

- **La App `menairos-agente` se crea ya en el H0** **[propuesta]**, como paso manual de Pedro,
  porque la necesitan las verificaciones. Se usa de verdad en el H1.
- **El H0 se cierra con `/cerrar-hito 0` sobre el propio repo de Menairos** **[propuesta]**: el
  informe, la revisión de Pedro y `--aprobar`, que publica **`v3.0.0`**.
- Se retira la skill `menairos-hola`.
- Se añade `/sincronizar` a la lista de comandos de `diseno.md`.
- El documento de seguimiento del Project se marca como archivado: desde aquí, el seguimiento vive en el
  repo.
- **La especificación del H1 se hace con `/crear-spec --siguiente`** sobre el propio repo de
  Menairos, con el informe del H0 como entrada: la primera vez que Menairos se especifica a sí
  mismo.

### 6.7 Casos límite

- El informe tiene un veredicto mal escrito (`aceptado` en lugar de `aceptada`): error con la
  línea.
- Repetir `--aprobar` después de un fallo a mitad: completa lo que faltaba sin duplicar issues,
  ADRs ni etiquetas.
- El PR de cierre ya está fusionado o la etiqueta ya existe: lo dice y sigue con el resto.
- La Release da 403: deja la orden para lanzarla en local.
- Un hito sin decisiones marcadas o sin fallos funcionales: las secciones salen vacías y el
  cierre sigue.
- Una ✅ cuya orden falla: queda sin marcar y se avisa a Pedro antes de abrir el PR de cierre.

### 6.8 Hecho cuando

- La prueba de punta a punta pasa las siete comprobaciones de la demo funcional, con tus tiempos
  medidos.
- Las siete verificaciones de 6.5 tienen resultado, anotado en el anexo y en `abiertas.md`.
- `menairos informe` y `menairos cierre --aprobar` tienen test de cada paso y de los casos límite
  de 6.7, con el doble de GitHub.
- El H0 está cerrado con su propio `/cerrar-hito`, y `v3.0.0` está publicada.

## Validación funcional

La demo funcional de `../hitos.md` (hito 0), en `pdromer0/menairos-prueba`. Las ✅ las comprueba
el agente con su orden antes del PR de cierre (6.2); las 👁 las juzga Pedro.

- 👁 `/crear-spec` en modo lluvia de ideas con una idea pequeña: la conversación es guiada y los
  documentos salen con el formato de las plantillas.
- ✅ `/validar-spec`: la capa 1 detecta un ciclo de dependencias sembrado a propósito — `uv run pytest tests/demo/test_validar_ciclo.py`
- 👁 `/validar-spec`: el informe del revisor tiene sentido; con el OK, se publican el milestone,
  los issues, las dependencias y las etiquetas.
- ✅ `/preparar-entorno`: `--comprobar` en verde sobre el repo de prueba — `menairos entorno --comprobar --raiz ../menairos-prueba`
- 👁 `/implementar` de una tarea en una sesión en la nube: plan de 8 apartados, PR con anexo y
  fichero de decisiones.
- 👁 `/implementar` de otra tarea en local y en modo didáctico: los conceptos se explican antes.
- ✅ `/cerrar-hito` básico: el informe se genera y `--aprobar` cierra, etiqueta y publica la Release — `uv run pytest tests/demo/test_cierre.py`

## 7. Anexo

*Cada tarea añade aquí su entrada en el mismo PR.*

### T-01 — Repo, protección y pasos manuales

*Hecha el 2026-11-25, en local (WSL2), guiada paso a paso desde el chat. Sin issue ni PR (el repo
aún no existía); esta entrada vive en el Project hasta T-03.*

**Qué se hizo**

- `pdromer0/menairos`, público, creado con `gh repo create --source . --push` desde
  `~/proyectos/menairos`, con un commit inicial (`6d0c765`: `README.md` y `SECURITY.md`) firmado
  con el email privado de GitHub.
- Por la API: fusión solo por *squash*, borrar la rama al fusionar y auto-merge permitido; escaneo
  de secretos y protección de push; alertas de Dependabot sin actualizaciones automáticas; informe
  privado de vulnerabilidades; aprobación de los workflows de PR de forks para cualquier persona
  externa (`all_external_contributors`).
- Ruleset «Proteger main» (id `28079885`) sobre la rama por defecto: sin borrado ni push forzado;
  PR obligatorio (0 aprobaciones, solo *squash*); check `ci` obligatorio con la rama al día;
  excepción solo para el usuario de Pedro (`115772852`) y solo a través de un PR.
- Comprobación final por la API de los cinco criterios de aceptación: todos cumplidos.

**Decisiones del diff**

- Los cinco ajustes de §1.2, confirmados por Pedro: commit inicial antes del ruleset; job `ci`
  sin matriz y T-03 dependiente de T-02; CodeQL en T-02 por la API; excepción por usuario y solo
  por PR; aprobación de los PR de forks por la API.
- 0 aprobaciones en la regla de PR: GitHub no deja aprobar los PR propios; la revisión de Pedro es
  leer el PR y fusionarlo.
- Sin referencias a los proyectos del método v2 en el repo (decisión de Pedro): el `README.md` se
  corrigió enmendando el commit antes del primer push; la versión anterior nunca se subió.
- Licencia aplazada hasta antes de `v3.0.0`; anotada en `abiertas.md`.
- `gh` sin actualizar: nada de T-01 necesitaba una versión más reciente.

**Medidas**

- Versiones: git 2.43.0; gh 2.103.3 (la última publicada era la 2.105.0); token de `gh` con los
  permisos `repo` y `workflow`.
- Tiempo: unos 50 minutos del paso 0 al 6, de los que unos 20 fueron de configurar el editor.

**Diferencias con la documentación**

- `GET /repos/{o}/{r}/automated-security-fixes` con las actualizaciones desactivadas devolvió
  `200` con `{"enabled": false, "paused": false}`, no el `404` documentado: `--comprobar` (T-12)
  debe leer el campo `enabled`.
- El ruleset aceptó como obligatorio un check (`ci`) que nunca se había ejecutado: no hizo falta
  el plan B del ajuste 2.
- El actor `User` funciona en las excepciones de un repo personal: no hizo falta el plan B del
  ajuste 4.
- La aprobación de los PR de forks tiene ruta REST a nivel de repo
  (`/repos/{o}/{r}/actions/permissions/fork-pr-contributor-approval`); la documentación oficial
  consultada solo mostraba la de organización y empresa. Valor por defecto: `first_time_contributors`.
- Al crear la regla de PR, GitHub añade `require_extra_approval_for_unattributed_changes: true`;
  sin efecto con 0 aprobaciones.

**Versiones incorrectas**

- No aplica: T-01 no tiene código.

**Revisión**

- Cada paso lo comprobó el chat contra la salida de la terminal antes del siguiente. Sin PR, no
  hubo revisión de PR.

**Pendiente**

- El push directo a `main` (`GH013`) se comprueba en T-02 (§1.7).
- El check `ci` empieza a existir con el PR de T-02; hasta entonces, ningún PR se puede fusionar
  sin la excepción de Pedro.
- Para T-12: CodeQL y la aprobación de los PR de forks pueden salir de los pasos manuales de
  §3.4; la comprobación de las actualizaciones automáticas lee `enabled`.

### T-02 — Esqueleto del paquete, stack, CI y comprobaciones deliberadas

*Hecha el 2026-11-25, en local (WSL2), con Claude Code (Sonnet, esfuerzo medio, modo plan y
después auto) a partir de encargos del chat. Sin issue. PR #1, fusionado por squash en `42a6b6b`.*

**Qué se hizo**

- Paquete `menairos` `3.0.0.dev0` con layout `src`: CLI con argparse y `--version`, y un test de
  humo.
- Stack: uv; ruff (`E`, `F`, `W`, `I`, `UP`, `B`); pyright en modo estándar sobre `src` y
  `tests`; pytest con pytest-timeout (60 s) y la marca `slow`.
- pre-commit: higiene (fin de fichero, espacios finales, YAML y TOML), gitleaks, ruff format, ruff
  check y pyright, estos tres con `uv run --frozen`.
- `scripts/n1.sh [rutas…]` y `scripts/n3.sh`: dicen qué ejecutan y salen con 0 o 1.
- Workflow `ci`: un solo job `ci`, sin matriz, en `ubuntu-24.04`; permisos de solo lectura; sin
  secretos; acciones fijadas por SHA; uv fijado a 0.13.10; llama a `scripts/n3.sh`.
- Ficheros de trabajo: `AGENTS.md`; `CLAUDE.md`, que importa `AGENTS.md`; `.claude/settings.json`
  con las prohibiciones del método (push forzado, push a `main`, fusionar, `DELETE` por la API,
  `--no-verify`); `menairos.toml`; plantillas de issue (tarea, bug e idea, sin issues en blanco) y
  de PR.
- CodeQL activado por la API con `python` y `actions`; el primer análisis de `main` no dio ningún
  resultado.

**Decisiones del diff**

- Reparto de la estructura de §1.3 por tareas, y scripts `n1`/`n3` hasta la plantilla
  `python-uv` (T-10); la N2 llega con el hook `Stop` (T-20).
- Versión `3.0.0.dev0` en el paquete (PEP 440) frente a `3.0.0-dev` en `menairos.toml`: la misma
  versión escrita como exige cada formato.
- `pyright[nodejs]`: Node llega como dependencia de Python, sin instalarlo en el sistema.
- gitleaks con el hook `gitleaks` (Go): pre-commit descarga Go y lo compila en su caché.
- Entornos de `menairos.toml`: valores por defecto, no una restricción (decisión de Pedro).
- `.claude/settings.json` deja el push sin preguntar; siguen prohibidos el forzado y el push a
  `main` (decisión de Pedro).
- pyright revisa solo `src` y `tests`: ruff ya revisa todos los `.py`, y las plantillas de T-09 y
  T-10 tendrán huecos `{{…}}` que no son Python válido (decisión de Pedro).
- zizmor (analizador de workflows) como comprobación puntual, no como dependencia: sin hallazgos.
- Fusión desde la web: el commit lleva el mensaje por defecto de GitHub (la lista de los seis
  commits, incluidos el test deliberado y su revert); el contenido es idéntico al del PR (mismo
  árbol).

**Medidas**

- Versiones: uv 0.13.10 (actualizado desde 0.13.6), Python 3.14.10, Claude Code 2.1.325, pytest
  9.2.0, pytest-timeout 2.4.0, ruff 0.17.6, pyright 1.1.414, pre-commit 4.7.0, pre-commit-hooks
  v6.0.0, gitleaks v8.30.0, actions/checkout v7.0.1 (`3d3c42e5…`), astral-sh/setup-uv v10.4.0
  (`1db35dd8…`), zizmor 1.33.1. Ninguna dependencia de desarrollo desactualizada
  (`uv tree --outdated`); los SHA, comprobados también con `git ls-remote`.
- CI: entre 11 y 17 s. Primera ejecución de pre-commit: unos 17 minutos, casi todos para compilar
  gitleaks; las siguientes, segundos.
- Tiempo total: de 16:00 a 19:40, con hora y media de espera por una incidencia de GitHub.

**Comprobaciones deliberadas (§1.7)**

| Fallo provocado | Resultado |
| --- | --- |
| Fichero mal formateado | El commit falla: ruff format («files were modified by this hook») |
| Error de tipos | El commit falla: pyright (`reportAssignmentType`), con el fichero en `tests/` |
| Clave falsa (`ghp_` + 36 caracteres aleatorios) | El commit falla: gitleaks (`github-pat`) |
| Test que falla | `ci` en rojo (`1 failed, 3 passed`) y de nuevo en verde tras el revert |
| Push directo a `main` | `GH013`: «Changes must be made through a pull request» y «Required status check "ci" is expected» |

**Diferencias con la documentación e incidencias**

- Incidencia de GitHub (25-11, de 15:55 a 16:52 UTC): errores 502 y de GraphQL al abrir y editar el
  PR, y un primer push a `main` rechazado con «fatal error in commit_refs_rules» en lugar de
  `GH013`. Se repitió tras resolverse.
- `gh pr edit` usa GraphQL: la CLI de Menairos editará los PR por REST (ADR 0016).
- Reintentar en bucle una escritura que no es idempotente (crear un PR) puede duplicarla; aquí se
  creó una sola vez. A tener en cuenta en T-07 y T-08.
- `code-scanning/default-setup` devuelve `languages: []` y `updated_at: null` hasta que termina el
  análisis de configuración.
- Con pre-commit instalado, un commit en una rama sin `.pre-commit-config.yaml` falla; se usó
  `PRE_COMMIT_ALLOW_NO_CONFIG=1` solo para la prueba del push a `main`.

**Versiones incorrectas**

- Las cumplen las comprobaciones deliberadas. Lección: la prueba de tipos con el fichero en la raíz
  no falló, porque pyright solo revisa `src` y `tests`; un hook en verde no dice qué revisó.

**Revisión**

- Revisión propia de Claude Code en el PR. Revisión del chat leyendo la rama en GitHub: los 20
  ficheros del reparto, sin restos de las pruebas, sin datos personales ni nombres de proyectos
  anteriores, scripts ejecutables y árbol fusionado idéntico al del PR.
- El modo auto bloqueó un `git reset --hard` sobre el commit de prueba; se hizo con la autorización
  de Pedro.

**Pendiente**

- Para T-03: el hueco de §0 (issues «desde T-03», pero el publicador llega en T-08).
- Para T-10: los scripts `n1`/`n3` pasan a la plantilla `python-uv`.
- Para T-12: CodeQL por la API, comprobado; puede salir de los pasos manuales de §3.4.

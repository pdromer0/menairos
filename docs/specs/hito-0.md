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
diseño (que el plugin llegue a los proyectos en local y en la nube).

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
│   └── marketplace.json       marketplace de un solo plugin, source ./plugin
├── plugin/
│   ├── .claude-plugin/
│   │   └── plugin.json        manifiesto del plugin (versión = la del paquete)
│   └── skills/
│       └── hola/              skill mínima para la verificación temprana (1.6); se retira en H0.5
├── src/menairos/
│   ├── __init__.py            __version__
│   ├── cli.py                 punto de entrada `menairos` (argparse, sin dependencias)
│   ├── esquemas/              esquemas JSON (H0.1), dentro del paquete (2.2)
│   └── plantillas/            plantillas de documentos y de stack (H0.2), dentro del paquete (3.2)
├── tests/
├── scripts/                   n1.sh, n2.sh y n3.sh de base, y stack/ con las partes de python-uv (3.3, T-10)
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
  `.claude-plugin/marketplace.json` y `plugin/`, con T-04; `src/menairos/esquemas/`, con T-05
  (dentro del paquete; decisión de Pedro, 2026-11-27); `src/menairos/plantillas/`, con T-09 y
  T-10 (también dentro del paquete, para que viajen con la CLI; decisión de Pedro, 2026-11-27).
- **Niveles de comprobación hasta T-10** (aceptado por Pedro el 2026-11-25): `scripts/n1.sh
  [rutas…]` (ruff, pyright y los tests de las rutas dadas) y `scripts/n3.sh` (formato comprobado,
  lint, tipos y todos los tests), los dos con salida 0 o 1 y diciendo qué ejecutaron; el CI llama
  a `scripts/n3.sh`, como hará el workflow de la plantilla `base`. La N2 llega con el hook `Stop`
  (T-20). **Desde T-10**, Menairos usa los scripts que componen `base` y `python-uv` (3.3): las
  rutas de `scripts/n1.sh` son rutas de tests, y cada una va a la plantilla que la tiene por suya;
  `scripts/n2.sh` ya existe y T-20 lo engancha al hook.

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

El riesgo más alto del diseño se comprueba en el primer tramo, no en el último: que el plugin de
Menairos no llegue a los proyectos, en local y en la nube, sin un paso a mano en cada sesión.

La documentación de los entornos en la nube
([cloud-environments](https://code.claude.com/docs/en/cloud-environments), tabla «What carries
over from your setup») ya responde a una parte: una sesión en la nube **no** instala los plugins
que el `.claude/settings.json` del repo declara en `extraKnownMarketplaces` y `enabledPlugins`, y
**sí** carga `.claude/skills/`, `.claude/agents/`, `.claude/commands/` y los hooks del repo.

En local, la documentación se contradice:

- [plugins/loading.md](https://code.claude.com/docs/en/plugins/loading) dice que un plugin
  habilitado solo en el `.claude/settings.json` del proyecto no carga hasta instalarlo (error
  «isn't installed here»), y también que, si falta un marketplace declarado, se clona en segundo
  plano y se descargan los plugins habilitados.
- [plugins/org.md](https://code.claude.com/docs/en/plugins/org#require-plugins-per-repository)
  solo exime de instalar a los marketplaces `directory` o `file` con `source` relativa, y el de
  Menairos se declara con la fuente `github`.

Piezas:

1. **El plugin mínimo** en `plugin/`, con la skill `hola` (`/menairos:hola`), que responde solo
   `menairos <versión> · cargado desde: ${CLAUDE_PLUGIN_ROOT}`. Claude Code sustituye la variable
   cuando carga la skill desde un plugin.
2. **El repo de prueba** `pdromer0/menairos-prueba`, público y sin protección, con un
   `.claude/settings.json` que declara el marketplace y habilita el plugin, y una copia de la
   skill en `.claude/skills/hola/` (`/hola`).

Pruebas, que hace Pedro:

| Prueba | Dónde | Cómo llega el plugin | Esperado |
| --- | --- | --- | --- |
| A1 | Local | Solo por el `.claude/settings.json` del repo, después de aceptar la confianza en la carpeta | Sin documentar (las dos páginas citadas arriba) |
| A2 | Local, solo si A1 no carga | `claude plugin install menairos@menairos --scope project` | Carga |
| B | Nube | Solo por el `.claude/settings.json` del repo | No carga (documentado) |
| C | Nube | Un script de entorno que ejecuta `claude plugin marketplace add` y `claude plugin install` antes de arrancar Claude Code | Sin documentar |
| D | Nube | La copia de la skill en `.claude/skills/` (plan B) | Carga (documentado) |

**Regla de decisión:** si C carga, el plan A para la nube es el plugin con un script de entorno,
que generará la capa nube de `menairos entorno` (T-12); si no, se aplica el plan B de
`diseno.md` 2.1 para la nube, como decisión de Pedro. El resultado va al anexo, a `abiertas.md` y
a `diseno.md` 2.1.

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
- Las pruebas A, B, C y D de 1.6 tienen resultado, anotado en el anexo y en `abiertas.md`, y la
  decisión sobre la nube en `diseno.md` 2.1.

---

## 2. H0.1 — Contratos

### 2.1 Qué se construye

Los tres esquemas JSON que definen el contrato de Menairos y las dos primeras órdenes de la CLI:
`menairos spec validar` (la capa 1 de `/validar-spec`) y `menairos spec publicar`.

### 2.2 Esquemas

JSON Schema (versión 2020-12) en `src/menairos/esquemas/`, dentro del paquete, porque la CLI se
instala con `uv tool install` y solo se empaqueta `src/menairos/`; se leen con `importlib.resources`
(decisión de Pedro, 2026-11-27). Llevan `"additionalProperties": false` en todos los objetos:
**una clave desconocida es un error**, para atrapar las erratas (`modelo` por `modelos`). Los
valores por defecto se declaran en el esquema (`default`) y los aplica la CLI; no tienen valor por
defecto `motivo_critica`, `por_que_no_escalo`, `agente` ni `revisor`, porque no tienen un valor
natural (decisión de Pedro, 2026-11-27).

**Reglas comunes** (decisión de Pedro, 2026-11-27: estricto ahora donde es barato, porque relajar
una regla después no rompe ningún fichero y endurecerla sí):

- «No vacío» excluye también los textos de solo espacios.
- Un entero no se escribe como decimal (`1.0`): JSON Schema 2020-12 lo admite, así que lo comprueba
  la CLI después del esquema.
- Un campo con patrón (ids, ramas, versión, repo, idiomas, área, enlaces y ventana horaria) no
  acaba en salto de línea; también lo comprueba la CLI, porque el `$` de Python lo dejaría pasar.
- En YAML, una clave repetida es un error de lectura (`yaml.safe_load` se queda con el último
  valor sin avisar); en TOML ya lo es.

#### `menairos.schema.json` (para `menairos.toml`)

| Clave | Tipo | Obligatoria | Por defecto | Regla |
| --- | --- | --- | --- | --- |
| `menairos.version` | texto | Sí | — | Versión semántica, con prerelease y sin metadatos de build (`3.0.0`, `3.1.0-dev`; no `3.0.0+b1`) |
| `proyecto.nombre` | texto | Sí | — | No vacío |
| `proyecto.repo` | texto | Sí | — | `dueño/repo`, con las reglas de GitHub: el dueño, letras, dígitos y guiones sueltos; el repo, distinto de `.` y `..` |
| `proyecto.visibilidad` | `publico` \| `privado` | No | `publico` | |
| `proyecto.idioma_docs`, `idioma_codigo` | texto | No | `es`, `en` | Código de idioma de 2 letras |
| `stack.plantillas` | lista de textos | Sí | — | Al menos una, sin repetir; debe incluir `base` |
| `modo.defecto` | `manual` \| `didactico` \| `automatico` | No | `manual` | |
| `modo.resumen_aprendizaje` | booleano | No | `true` | |
| `entornos.*` | ver `diseno.md` 3.1 | No | `nube`, `nube`, `actions` | |
| `modelos.*` | ver `diseno.md` 3.1 | No | Los del punto 17 | `opus` \| `sonnet` \| `haiku`; `plan` e `implementacion` son `{normal, critica}` |
| `revisores.*` | ver `diseno.md` 3.1 | No | Los del punto 17 | `codex` \| `claude` |
| `autonomia.*`, `escalado.*`, `guardarrailes.*` | ver `diseno.md` 3.1 | No | Los de `diseno.md` 3.1 | Enteros ≥ 1; porcentajes 1–100; `rutas_protegidas` sin repetir; `ventana_horaria` vacía o `HH:MM-HH:MM` |
| `modulos.*` | `inactivo` \| `piloto` \| `activo` \| `retirado` | No | `inactivo`, salvo `revisor_plan`: `activo` (5.7) | |

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
| `tareas[].id` | texto | Sí | `T-` y 2 dígitos, o 3 sin cero delante (`T-01`, `T-104`; no `T-001`, que se confundiría con `T-01`) |
| `tareas[].titulo` | texto | Sí | No vacío |
| `tareas[].rama` | texto | Sí | Prefijo `feat/`, `fix/`, `docs/`, `refactor/`, `test/`, `chore/` o `ci/` y después `[a-z0-9._-]+`; sin lo que git rechaza (`..`, un punto al principio o al final, acabar en `.lock`) |
| `tareas[].depende_de` | lista de ids | No (`[]`) | Sin repetir |
| `tareas[].area` | texto | No (`general`) | Minúsculas, dígitos y guiones |
| `tareas[].critica` | booleano | No (`false`) | |
| `tareas[].motivo_critica` | texto | Si `critica` es `true` | |
| `tareas[].donde` | `cualquiera` \| `local` | No (`cualquiera`) | |
| `tareas[].quien` | `claude` \| `codex` | No (`claude`) | |
| `tareas[].modo` | `null` \| modo | No (`null`) | `null` = el del hito |
| `tareas[].especificacion` | lista de textos | Sí | Al menos una; `fichero.md#ancla` o `fichero.md` (el fichero entero, 2.3) |
| `tareas[].criterios_aceptacion` | lista de textos | Sí | Al menos uno, no vacíos |

#### `decisiones.schema.json` (para `decisiones/T-xx.yaml`)

| Clave | Tipo | Obligatoria | Regla |
| --- | --- | --- | --- |
| `tarea` | texto | Sí | El id de la tarea |
| `decisiones` | lista | Sí | Puede estar vacía |
| `decisiones[].id` | texto | Sí | `T-xx-Dn` de la misma tarea, con el id de tarea de `tareas[].id` |
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
- **Un id repetido en el mismo fichero es un error** (decisión de Pedro, 2026-11-27).

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
  (fichero que no existe, argumentos mal). Son de uso: `--raiz` que no es una carpeta, y que falte
  `menairos.toml`, el YAML de tareas del hito, `hito-N.md`, `docs/abiertas.md` o la carpeta
  `docs/decisiones/`; el mensaje va a la salida de error y la normal queda vacía, también con
  `--json`. Lo que falta *dentro* (un fichero enlazado, un ancla, la sección, el ADR `stack`) y
  un fichero que no se puede leer (sintaxis, clave repetida, alias en bucle, no UTF-8) son
  errores de validación.
- **Orden:** si E01 o E02 fallan, no se comprueban E03–E09, que dependen de datos válidos; E10,
  E11 y E12 sí, porque no usan los datos. El E02 de un `hito` que no coincide con la N del nombre
  no corta nada: los datos son válidos. E13 solo necesita un `menairos.toml` válido: si E01
  falla, no se comprueba, y la salida dice qué grupo quedó sin comprobar. A01 y A02 miran el
  documento tal como se escribió, antes de aplicar los valores por defecto.

| Código | Comprobación |
| --- | --- |
| E01 | `menairos.toml` no cumple su esquema |
| E02 | `hito-N.tareas.yaml` no cumple su esquema, o su `hito` no es la N del nombre del fichero |
| E03 | Id de tarea repetido |
| E04 | Rama repetida entre tareas |
| E05 | Dependencia a un id que no existe |
| E06 | Una tarea depende de sí misma |
| E07 | Ciclo de dependencias: un error por cada grupo de tareas que dependen unas de otras (componente fuertemente conexa), con un ciclo de ejemplo en el mensaje (`T-02 → T-04 → T-02`, donde `→` es «depende de») |
| E08 | Enlace de `especificacion` a un fichero que no existe, que sale del repo o que difiere en mayúsculas del de disco; se resuelve desde la carpeta del YAML |
| E09 | Enlace a un ancla que no existe en el fichero |
| E10 | El hito no tiene una sola sección «Validación funcional» con al menos una comprobación ✅ o 👁 (un elemento de lista que empieza por uno de ellos), o una ✅ no termina en ` — ` y su orden entre comillas invertidas (6.2) |
| E11 | `abiertas.md` tiene puntos sin justificación |
| E12 | No hay ningún ADR de tipo `stack` |
| E13 | Una plantilla de `stack.plantillas` no está entre las plantillas de stack de la versión de Menairos instalada (se busca en su lista: `.` o `../docs` no cuentan) |
| A01 | `motivo_critica` presente en una tarea no crítica |
| A02 | Tarea sin `area` explícita (con paralelismo > 1 en `menairos.toml`) |
| A03 | Las coherencias de `menairos.toml` de 2.2 |
| A04 | `quien: codex` en una tarea cuyo modo efectivo no es manual (`tareas[].modo` o, si es `null`, `modo.defecto` de `menairos.toml`) |

H0.3 añade E14, E15 y A05 (4.5).

**Anclas (E09).** Se calculan como GitHub, verificado en T-06 con su API (anexo):

- del encabezado se toma el texto que se ve: el código sin las comillas invertidas, los enlaces
  como su texto, las entidades y los escapes resueltos, y sin etiquetas HTML, marcas de énfasis
  ni imágenes;
- se pasa a minúsculas;
- se quita todo lo que no sea una letra, una marca (los acentos combinados), una cifra decimal,
  `_`, `-` o un espacio: signos, símbolos, emoji, tabuladores, el espacio de no separación y
  cifras como `①` o `²`;
- cada espacio pasa a `-`, sin juntar guiones (`## Hito 0 — Núcleo` → `#hito-0--núcleo`);
- las letras con acento se conservan (`## Validación funcional` → `#validación-funcional`), y
  también `_` (`` ## `idioma_docs` `` → `#idioma_docs`);
- los repetidos llevan sufijo `-1`, `-2`; si el sufijo choca con otro encabezado, se añade otro
  (`Repetido`, `Repetido`, `Repetido-1` → `repetido`, `repetido-1`, `repetido-1-1`); un
  encabezado sin nada que quede (`## ✅`) no tiene ancla, pero cuenta para los repetidos.

Solo cuentan los encabezados ATX (`#` a `######`, con hasta tres espacios delante) fuera de los
bloques de código. GitHub también da ancla a los encabezados subrayados (`===`, `---`) y a los que
están dentro de una lista o una cita, pero Menairos no los cuenta: enlazar uno da E09, y en los
documentos del método no se usan. El ancla se compara tal cual (sin descodificar `%C3%B3`).

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

- **Precondición:** `spec validar` sin errores. Si los hay, no publica nada, no llama a GitHub y
  sale con `1`. Sus avisos pasan a la salida.
- **Siempre por `gh api`** (ADR 0016), con un envoltorio fino que en los tests se sustituye por un
  doble con tope: el envoltorio es `menairos.github` y el doble, `tests/doble_github.py` (T-07).
- **El repo** es `proyecto.repo` de `menairos.toml`.
- **`--seco`** hace las mismas lecturas y muestra lo que haría sin escribir nada en GitHub.
  `/validar-spec` lo enseña a Pedro antes de pedir el OK.
- **Límites de GitHub**, comprobados antes de llamar:
  - el nombre de una etiqueta, 50 caracteres (`area:` y el área);
  - el título de un issue, 256;
  - su cuerpo, 65 536.

  Si se pasa alguno, no llama a GitHub y sale con `1`.

**Primero lee y después escribe.**
- Lee, todo paginado:
  - las etiquetas;
  - los milestones, con `state=all`;
  - los issues, con `state=all` y sin los PR;
  - las relaciones «blocked by» de cada issue abierto de una tarea.
- Si dos issues llevan la misma marca, o un cuerpo la lleva dos veces, para sin escribir nada y
  sale con `1`.
- Después escribe en el orden de abajo, con una pausa de 1 s entre dos escrituras: es lo que pide
  GitHub para no caer en su límite secundario.

Lo que hace, en este orden:

1. **Etiquetas** de `diseno.md` 3.4 y una `area:*` por cada área del YAML
   (`src/menairos/labels.py`): crea las que falten, comparando los nombres sin mayúsculas; no toca
   las que existen.
2. **Milestone**, con el `titulo` del YAML, que ya empieza por «Hito N — »:
   - lo busca por título, sin distinguir mayúsculas ni los espacios de los extremos;
   - lo crea solo si falta y algún issue nuevo lo necesita;
   - si está cerrado, lo usa igual y avisa;
   - se asigna al crear el issue: si cambia el título del hito, los issues ya publicados no se
     mueven.
3. **Issues**, uno por tarea, en el orden del YAML:
   - título `T-01 · título de la tarea`;
   - un cuerpo que genera la orden (la plantilla de issue `tarea.md` va aparte; ver
     `abiertas.md`). Solo depende del YAML y de `proyecto.repo`, y lleva:
     - un resumen: la tarea, el hito, el área y, si es crítica, su motivo;
     - los enlaces a las secciones de la especificación, en `main`;
     - los criterios de aceptación, como casillas;
     - la rama;
     - las dependencias, solo por id (`T-06, T-07`): con el título, renombrar una tarea
       reescribiría el cuerpo de todas las que dependen de ella, y perderían sus casillas
       marcadas. La relación «blocked by» ya enseña los títulos;
     - si necesita el portátil;
     - quién la hace;
     - el modo;
   - etiquetas `tipo:tarea`, `critica` si lo es, `area:*` y `modo:*` si la tarea fija modo;
   - una marca oculta en la última línea del cuerpo,
     `<!-- menairos:tarea=T-01 hito=0 modo=didactico huella=<título>.<cuerpo>.<etiquetas> -->`,
     que es lo que usa la idempotencia (no el título, que Pedro puede cambiar):
     - `modo=` dice qué `modo:*` es de publicar: el de la tarea, si el issue lo lleva una vez
       publicado;
     - va sin `modo=` si la tarea no fija modo o si el issue no lo lleva (tiene otro puesto a
       mano, o Pedro lo quitó);
     - se decide solo al escribir la marca: al crear el issue o cuando cambia la huella;
     - es lo único que mira el issue: el título, el cuerpo y la huella solo dependen del YAML y
       de `proyecto.repo`.
4. **Dependencias nativas «blocked by»**, una por cada `depende_de`, después de crear todos los
   issues. Cada una se escribe con el **id** del issue que bloquea, no con su número.

**La huella** (decisión de Pedro, 2026-11-27: en tres partes desde el plan de T-08, y con el modo
en claro en la marca desde la auditoría de T-08):
- **Qué es:** tres partes, cada una con los 16 primeros caracteres hex de un SHA-256:
  - del título;
  - del cuerpo generado, sin la marca;
  - de las etiquetas del YAML, las que lleva un issue nuevo, en minúsculas, ordenadas y una por
    línea. Incluyen el modo de la tarea también cuando el issue se queda con otro puesto a mano:
    así un choque de modo no se reescribe en cada ejecución.
- **Comparada entera,** dice si la tarea cambió.
- **Por partes,** dice:
  - qué cambió;
  - si el cuerpo actual sigue siendo el generado (antes de comparar, se pasa de CRLF a LF y se le
    quita la marca);
  - si cambiaron las etiquetas del YAML; solo entonces se tocan las del issue.
- **Una marca ilegible** se reconoce por su tarea y su hito y cuenta como cambiada:
  - es ilegible si la huella está rota, o si el `modo=` no es uno de los tres, está repetido o va
    detrás de `huella=`;
  - sin la huella no se lee el `modo=`, así que el `modo:*` del issue cuenta como puesto a mano.
- **Solo cuenta la marca que ocupa una línea entera fuera de los bloques de código**: un issue que
  cita el cuerpo de otro dentro de un bloque no se lleva su marca.

**Etiquetas de un issue.** Publicar solo añade o quita las suyas:
- `tipo:tarea`, `critica` y `area:*` lo son siempre, porque solo las pone el script (3.4);
- un `modo:*` lo es solo si lo dice la marca (`modo=`);
- nunca toca `en-curso`, `necesita-pedro`, `aprobado-pedro` ni un `modo:*` que la marca no diga;
- si la tarea fija un modo y el issue tiene otro puesto a mano, se queda el de Pedro, con un
  aviso, y la marca va sin `modo=`;
- un `modo:*` puesto a mano igual al de la tarea pasa a ser de publicar si el issue lo lleva
  cuando se reescribe la marca (decisión de Pedro tras la auditoría de T-08): si el YAML quita o
  cambia después el modo, publicar lo quita.

**Idempotencia.** Una segunda ejecución sin cambios no hace ninguna escritura.

| Situación | Qué hace |
| --- | --- |
| Tarea nueva | Crea su issue y sus dependencias |
| Misma huella, aunque Pedro haya editado el issue a mano | No toca el issue |
| Huella distinta, issue abierto | Vuelve a leer el issue y reescribe solo las partes que cambiaron, con la marca nueva. El título, si cambió el suyo. El cuerpo, si cambió el suyo; si no, solo cambia la marca dentro del cuerpo actual, y se conserva lo editado a mano. Las etiquetas, si cambiaron las suyas. Si reescribe un cuerpo o un título editados a mano, lo avisa |
| Huella distinta, issue cerrado | No toca nada, tampoco sus dependencias; lo informa como aviso |
| Tarea borrada del YAML | No cierra ni borra el issue; lo informa como aviso |
| Dependencia nueva, quitada o que falta | Añade o quita la relación «blocked by», cambie o no la huella |
| Fallo a mitad | La siguiente ejecución completa lo que falta, sin duplicar |

**Las dependencias entre tareas del hito solo se gestionan en el YAML** (`depende_de`; decisión
de Pedro, 2026-11-27):
- se sincronizan en cada ejecución, en el issue abierto de cada tarea del YAML, frente a todos los
  issues que llevan una marca del hito, también los de tareas borradas del YAML. Las relaciones
  del issue de una tarea borrada no se tocan, igual que el resto de ese issue;
- por eso, **una relación «blocked by» que se añada a mano entre dos issues del hito se quita en
  la publicación siguiente**;
- las relaciones con cualquier otro issue (un bug, otro hito, otro repo) no se tocan, y las de un
  issue cerrado tampoco.

**Nunca borra ni cierra nada** (las reglas del método v2: nada de `DELETE` por la API), salvo una
excepción (decisión de Pedro, 2026-11-27): quitar una relación «blocked by» entre dos issues, que
borra un enlace y no datos. El envoltorio de `gh api` la permite con una lista explícita de un solo
patrón de ruta y rechaza cualquier otro `DELETE` antes de llamar a `gh`.

**Salida:**
- con `--json`: `{"ok", "seco", "repo", "hito", "creados", "actualizados", "quitados",
  "sin_cambios", "avisos", "errores"}`. Cada elemento lleva `tipo` (`etiqueta`, `milestone`,
  `issue` o `dependencia`); los avisos y los errores llevan `codigo` y `mensaje`;
- sin `--json`: un resumen legible;
- sale con `0` si se publicó todo (aunque haya avisos), `1` con errores y `2` en un error de uso,
  como `spec validar`. Son errores los de la especificación, un límite, una marca repetida o un
  fallo de GitHub. En este último, la salida dice qué escritura falló:
  - con resultado desconocido, si no hubo respuesta o fue un 5xx;
  - que no se guardó, si GitHub la rechazó con un 4xx.

| Avisos | Cuándo |
| --- | --- |
| `issue-cerrado` | La tarea cambió y su issue está cerrado |
| `tarea-borrada` | Un issue con la marca de una tarea que ya no está en el YAML |
| `cuerpo-reescrito`, `titulo-reescrito` | Se reescribió un cuerpo o un título editados a mano |
| `modo-a-mano` | La tarea fija un modo y el issue tiene otro puesto a mano |
| `marca-ilegible` | La marca no se puede leer (la huella o el `modo=`) |
| `milestone-cerrado` | El milestone del hito está cerrado |
| `posible-duplicado` | Un issue sin marca con el título de una tarea que aún no tiene issue |
| `issue-cambiado` | El issue se cerró o perdió su marca entre la lectura y la escritura: no se tocan ni él ni sus dependencias |

Los errores son los de `spec validar`, más `limite`, `marca-repetida` y `github`.

**Casos límite** que deben tener test (con el doble de GitHub):

- repo sin ninguna etiqueta ni milestone;
- un issue con la marca oculta, pero editado a mano por Pedro (título cambiado): se reconoce por
  la marca;
- dos issues con la misma marca (un error de antes): para y lo informa, sin escribir;
- fallo de la API a mitad de la publicación: la siguiente ejecución completa lo que faltaba sin
  duplicar;
- paginación: más de 100 issues o etiquetas en el repo;
- una dependencia a una tarea cuyo issue está cerrado: se crea igual;
- un cuerpo guardado con CRLF, como lo deja la web: se reconoce igual.

**Verificado en T-08** (anexo), en la documentación de GitHub y contra el repo de prueba:
- `POST …/issues/{n}/dependencies/blocked_by` con `{"issue_id": <id>}`, el id del issue que
  bloquea, responde 201 con el issue bloqueado;
- `DELETE …/issues/{n}/dependencies/blocked_by/{id}` responde 200 con el issue bloqueado;
- un duplicado, o un issue que depende de sí mismo, da 422 con solo un `message`;
- un id que no existe da 404;
- se puede depender de un issue cerrado, y el listado lo incluye.

### 2.5 Hecho cuando

- Los tres esquemas están en `src/menairos/esquemas/`, con un ejemplo válido y uno inválido por
  regla en `tests/data/esquemas/`.
- `menairos spec validar` detecta los errores E01–E12 y los 4 avisos de 2.3, cada uno con su test, y
  los casos límite tienen test. E13 llegó en T-10, con las plantillas de stack.
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

En `src/menairos/plantillas/docs/`, dentro del paquete para que viajen con la CLI instalada (se
leen con `importlib.resources`, como los esquemas). Los encabezados son **fijos**: los usan las
anclas de las tareas y las comprobaciones de `spec validar`, así que cambiar uno es un cambio de
contrato; un test comprueba cada uno.

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
| Plantillas de issue | Tarea, bug e idea, y `config.yml` (sin issues en blanco); la de Tarea lleva las secciones del cuerpo que genera `spec publicar` (2.4), sin la marca |

**Sustitución de valores sin dependencias:** los huecos se escriben `{{clave}}`
(`{{proyecto.nombre}}`, `{{hito.numero}}`) y los rellena la CLI (`menairos.templates`). No hay
lógica dentro de las plantillas (nada de Jinja):

- los valores salen de `menairos.toml`, validado y con sus valores por defecto, con claves de
  tabla separadas por puntos, y de unas pocas claves que pasa quien llama: `hito.numero`,
  `hito.titulo`, `fecha`, `tarea.id`, `tarea.titulo`, `adr.numero`, `adr.titulo` y `adr.tipo`;
- un valor es un texto no vacío, sin saltos de línea ni caracteres de control, o un entero; un
  booleano, una tabla o una lista es un error;
- un hueco mal escrito (`{{ clave }}`, sin cerrar), un hueco sin rellenar o una clave que no existe
  es un error; salen todos a la vez, con su línea;
- un `{{` literal se escribe `\{{`; el texto se recorre una sola vez, así que un valor con `{{…}}`
  se queda tal cual;
- en las plantillas YAML, un texto solo va en un hueco entre comillas dobles (`"{{clave}}"`), y
  la CLI lo escapa como dentro de ellas; fuera de comillas, solo un entero;
- lo que escribe el autor va en comentarios HTML, nunca en un hueco.

### 3.3 Plantillas de stack y contrato común

Cada plantilla de stack es una carpeta en `src/menairos/plantillas/stacks/` (dentro del paquete,
para que viaje con la CLI) con un **manifiesto `plantilla.toml`** y una carpeta `ficheros/` que
refleja el proyecto. **Cada fichero lleva el sufijo `.plantilla`**, que la composición quita: así
git no lee el `.gitignore` anidado, ruff no toma el `pyproject.toml` anidado y pyright y
`check-yaml` no se topan con los huecos (decisión de Pedro, T-10). Los huecos son los de 3.2,
también en las rutas (`src/{{paquete}}/__init__.py`), más `{{paquete}}`: el nombre del proyecto en
minúsculas y con `-` → `_`. El nombre tiene que ser ASCII, empezar por letra y separar las palabras
con un solo `-` o `_`, y el paquete no puede ser una palabra reservada ni un módulo de la
biblioteca estándar; si no, la composición da un error (solo si alguna plantilla usa el hueco).

El manifiesto lo valida `esquemas/plantilla.schema.json`. Hay dos tipos: **`base`** (una sola, que
se llama así, y la llevan todos los proyectos) y **`lenguaje`** (al menos una por stack; las
extras llegarán con su tipo):

```toml
[plantilla]
nombre = "python-uv"
version = "1.0.0"
tipo = "lenguaje"
requiere = ["base"]

[herramientas]                   # lo que comprueba la capa local; lista cerrada, con su fecha
uv = ">=0.13.10"                 # comprobada con herramientas al crear la plantilla
python = "3.14"

[propiedad]                      # lo que es de la plantilla (solo las de lenguaje)
extensiones = [".py", ".pyi"]
carpetas = ["src/", "tests/"]

[ordenes]                        # el contrato común: /implementar y los hooks solo usan estas
formato = "uv run --frozen ruff format ."
formato_fichero = "uv run --frozen ruff format {fichero}"   # hook PostToolUse (5.5)
lint = "uv run --frozen ruff check ."
tipos = "uv run --frozen pyright"
tests_area = 'uv run --frozen pytest -m "not slow" {rutas}'

[permisos]                       # reglas de .claude/settings.json
permitir = ["Bash(uv run *)", "Bash(uv sync *)"]

[ficheros]
fusionables = [".gitignore", ".pre-commit-config.yaml", ".github/workflows/ci.yml", "AGENTS.md"]

[[comprobaciones]]               # las deliberadas (3.6)
nombre = "formato"
provoca = "un fichero Python mal formateado"
salta = "pre-commit"             # pre-commit | n3 | github
mensaje = "hook id: ruff-format"
```

`base` declara en `[ordenes]` las del proyecto (`n1`, `n2` y `n3`), en `[permisos]` las
prohibiciones (`denegar`), la regla `preguntar` de `menairos cierre * --aprobar` (6.3) y lo que se
permite, y en `[[comprobaciones]]` la clave falsa y las dos remotas.

- **Las versiones del manifiesto** se fijan al crear la plantilla, comprobadas con herramientas en
  ese momento, y se anotan con su fecha.
- **Propiedad** (decisión de Pedro, T-10): un fichero es de la plantilla cuya extensión coincide
  (lo que va tras el último punto del nombre, quitados los puntos del principio); si ninguna, de la
  dueña de la carpeta que lo contiene. Dos plantillas no comparten extensiones ni tienen carpetas
  que se solapen. `formato_fichero` se elige solo por extensión.
- **Cómo lo usan T-20 y T-22:** `menairos.stacks.contract()` da el `Contract`. El hook
  `PostToolUse` (5.5) llama a su `format_command(fichero)` en el mismo proceso. `/implementar`
  (5.2) ejecuta `scripts/n1.sh` con las rutas de tests, que las reparte solo; para elegir el
  `tests_area` según los ficheros tocados, usa `templates_for` (un fichero tocado sin dueña, como
  `docs/…`, se ignora) y `tests_commands` (una ruta de test sin dueña es un error), con la orden
  de la CLI que decida T-22.
- **Composición:** la CLI aplica las plantillas en el orden de `requiere` (cada una detrás de las
  que requiere) y, entre las demás, en el de `stack.plantillas`. Son errores una plantilla que no
  existe, un `requiere` que no está en `stack.plantillas`, un ciclo, un stack sin plantilla de
  lenguaje y dos plantillas que traen el mismo fichero sin declararlo las dos fusionable. Los
  fusionables se combinan así:

  | Fichero | Regla |
  | --- | --- |
  | `.gitignore` | El de `base` tal cual y, tras una línea en blanco, las líneas nuevas de cada plantilla |
  | `.pre-commit-config.yaml` | Cada fragmento empieza por `repos:`; los cuerpos se unen con una línea en blanco (los hooks se suman) |
  | `.github/workflows/ci.yml` | `base` trae el job con una línea marcador; los pasos de cada plantilla de lenguaje (preparar su herramienta) la sustituyen |
  | `AGENTS.md` | El de `base` y la sección de cada plantilla |

- **Lo que genera el código** (no son plantillas, y ninguna plantilla los puede traer):
  `.claude/settings.json`, con las reglas de `[permisos]` de cada plantilla, el marketplace de
  Menairos fijado a `v<menairos.version>` (sin `ref` si es una versión previa, como `3.0.0-dev`,
  que aún no tiene etiqueta) y el plugin habilitado; y `scripts/stack/plantillas.txt`, una línea
  por plantilla de lenguaje con lo que es suyo. **En el H0, `.claude/settings.json` es igual en los
  tres modos** (decisión de Pedro, T-10): el fichero es uno por repo y el modo es por tarea, y un
  `ask` ya falla cerrado en Actions; las diferencias por modo, si hacen falta, llegan en el H1.
- **La N3 de un proyecto generado no valida su especificación** todavía (`abiertas.md`).

**`base`** (todo proyecto la lleva): `.gitignore`; pre-commit con gitleaks y las comprobaciones
de higiene (fin de fichero, espacios finales, YAML y TOML válidos); `SECURITY.md`; el workflow `ci`
fino, que llama a la orden `n3` del contrato; `AGENTS.md` y `CLAUDE.md` base; y los scripts del
proyecto, que componen las partes de cada plantilla de lenguaje.

**`python-uv`:** `pyproject.toml` (Python 3.14; ruff; pyright en modo estándar; pytest con
`timeout = 60` y la marca `slow`); `src/{{paquete}}/__init__.py`; `tests/test_humo.py`;
`.python-version`; hooks locales de ruff y pyright con `uv run --frozen`; los pasos de uv del CI;
y sus partes `scripts/stack/python-uv/n1.sh` (admite `--sin-tests`) y `n3.sh`.

| Script | Qué hace | Cuándo |
| --- | --- | --- |
| `scripts/n1.sh [rutas de tests…]` | Reparte las rutas por propiedad (una ruta sin dueña o fuera del repo es un error) y ejecuta la parte N1 de cada plantilla de lenguaje: con sus rutas, sin argumentos si no se dio ninguna, o con `--sin-tests` si ninguna es suya | Antes de cada commit |
| `scripts/n2.sh` | La N1 con sello: solo si el árbol cambió desde el último verde. La huella es el árbol de git de un índice temporal con todo lo no ignorado; el sello, en `.cache/menairos/` | Al final de cada turno (hook `Stop`) |
| `scripts/n3.sh` | La parte N3 de cada plantilla: formato comprobado, lint, tipos y todos los tests | Antes del push y en el CI |

Los tres ejecutan todas las partes aunque falle una, salen con `0` en verde y `1` en rojo (sea cual
sea el código de la parte) y dicen qué ejecutaron (lección de un proyecto anterior: un verde sin
decir qué revisó no vale). Son bash porque el CI de un proyecto no tiene la CLI (ver arriba) y el
contrato sirve para cualquier lenguaje. **Un test vigila que no se separen de Menairos**: `base` +
`python-uv` con el `menairos.toml` del repo dan sus scripts, su CI y sus hooks, salvo una lista
declarada de diferencias (decisión de Pedro, T-10).

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
| **local** | Herramientas del manifiesto y sus versiones (`git`, `gh` con sesión, `uv`, `claude`; `codex` si algún revisor de `menairos.toml` es Codex, y `docker` si una plantilla lo pide); el repo bajo `~/proyectos/` (si no, aviso) y nunca en una unidad de Windows (`/mnt/<letra>/`); `.wslconfig` con memoria y swap (solo aviso). Solo lee |
| **repo** | Aplica las plantillas sin sobrescribir; lo que necesita cada plantilla de lenguaje (en python-uv, `uv sync` y `pre-commit install`); primer commit en `main` si el repo es nuevo, con todo lo que no ignora el `.gitignore` y sin push |
| **github** | Crea el repo con la visibilidad de `menairos.toml` (con `--source --push`); ruleset de `main` (solo en público o con GitHub Pro; si no, aviso); escaneo de secretos y protección de push; Dependabot; informe privado de vulnerabilidades; fusión solo por *squash*; borrar la rama al fusionar; auto-merge permitido; etiquetas (las mismas de `spec publicar`) |
| **nube** | Genera `scripts/entorno-nube.sh` (instala la CLI de Menairos y el plugin de Menairos fijados a la versión —`claude plugin marketplace add` y `claude plugin install`, comprobado en T-04—, `uv sync`, comprueba `gh`, amplía el tiempo máximo de los comandos para la N3) y las instrucciones para pegarlo en el entorno de la nube de Claude Code y de Codex |

Decisiones de comportamiento:

- **La CLI no instala herramientas del sistema** (uv, gh, Docker…): las comprueba y, si faltan o
  son viejas, da la orden exacta para instalarlas como paso `manual`. Solo actúa dentro del
  proyecto y en GitHub.
- **En un repo que ya existe (modo MVP), nunca sobrescribe:** aplica lo que falta y lista los
  conflictos (un `pyproject.toml` que ya existe, un CI distinto) para que los resuelva
  `/preparar-entorno` con Pedro.
- **`menairos.toml` lo crea `/crear-spec`**, porque es donde se decide el stack.
  `/preparar-entorno` lo necesita y para si no existe.
- **Una capa para en su primer paso que no queda en `ok` o `hecho`**, y lista los que no
  ejecutó. Sin capa, la de repo solo se ejecuta si la local queda en verde. Con conflictos, no hay
  `uv sync`, ni `pre-commit install`, ni primer commit (decisiones de Pedro, T-11).
- **Salida:** `0` si todo queda en `ok` o `hecho`; `1` si hay algún `manual` o `error`; `2` si no
  se puede ejecutar (sin `menairos.toml`, o con uno no válido). Un aviso no cambia el estado.

**Pasos manuales de Pedro**, al final y en una lista: crear la GitHub App `menairos-agente` e
instalarla (en H0 solo se deja preparado; se usa en H1); CodeQL; la aprobación de los PR de forks;
y pegar el script de entorno en la nube. Objetivo: **15 minutos como mucho**, medido en el
anexo.

**`--comprobar`** no escribe nada: verifica por la API todo lo que se puede verificar (también lo
que Pedro hizo en la web) y marca como `manual` lo que no tiene API (el entorno de la nube), con
lo que hay que mirar. En las capas local y repo, lo que la orden haría también sale como `manual`,
con la orden exacta (`menairos entorno repo`).

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
| A05 | Fases marcadas «a revisar» en `.menairos/estado-spec.toml` |

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
- E14, E15 y A05 tienen test, y los casos límite de 4.6 tienen test donde son deterministas.

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
| `PostToolUse` (Edit, Write) | Formatea el fichero editado con el `formato_fichero` de la plantilla dueña de su extensión (`[propiedad]` del manifiesto, 3.3; `Contract.format_command`); si ninguna lo es, no hace nada |
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
| El plugin en `claude-code-action` | Un workflow mínimo en el repo de prueba que lanza `claude-code-action` con el token OAuth de Max y pide la skill `hola` (`/menairos:hola`) |
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
- Se retira la skill `hola` (`/menairos:hola`).
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

### T-03 — Documentos al repo y los 20 ADRs

*Hecha el 2026-11-25, en local (WSL2), con Claude Code (Sonnet, modo plan y después auto) a partir
de un encargo del chat. Sin issue.*

**Qué se hizo**

- La especificación entra en `docs/`: `producto.md`, `diseno.md`, `hitos.md`, `abiertas.md`,
  `specs/hito-0.md` y `specs/hito-0.tareas.yaml`.
- 20 ADRs (0001–0020) con su índice `docs/decisiones/README.md`: punto → ADR, tipo y
  reversibilidad.
- `docs/proceso/lecciones.md` con las reglas de T-01 y T-02.
- `AGENTS.md` actualizado: el paso del issue remite a §0 hasta T-09 y la sección «Dónde está el
  resto» describe lo que ya hay en `docs/`.
- Los ficheros los preparó el chat a partir del Project y llegaron en un zip; esta sesión los
  comprobó y abrió el PR.

**Decisiones del diff**

Todas de Pedro, 2026-11-25.

- T-01 a T-08 sin issue; los issues del hito se publican en T-08.
- Los ficheros, preparados por el chat.
- Los proyectos del método v2, citados de forma genérica; las referencias al documento de
  seguimiento del Project, sustituidas por `docs/decisiones/` y su índice.
- Formato de los ADRs: metadatos en líneas de lista y «Alternativas consideradas» solo con las que
  constan.
- `lecciones.md` sí y diario no (quitado de §1.3).
- Desde T-04, los cambios de especificación entran en el PR de la tarea y el anexo lo escribe
  Claude Code en el mismo PR.

**Medidas**

- 28 ficheros en `docs/`; 20 ADRs (0001–0020), uno de tipo `stack` (el 0020).
- Duración de esta sesión: unos minutos desde la primera comprobación (20:23, hora local) hasta el
  push; la hora de apertura del PR consta en su cuerpo (Métricas).

**Comprobaciones**

- 28 ficheros en `docs/`.
- Búsqueda sobre todo el repo (sin `.git` ni `.venv`) de los nombres de proyectos anteriores y de
  la ruta del documento de seguimiento: sin resultados.
- Ningún email en `docs/`.
- `hito-0.tareas.yaml` carga con `yaml` y tiene 28 tareas; sus 42 enlaces de `especificacion`
  apuntan a encabezados existentes de `hito-0.md` (ancla calculada como GitHub).
- 20 ADRs, cada uno con su línea `- **Tipo:** …`; solo el 0020 es de tipo `stack`.
- Enlaces relativos y anclas entre los ficheros de `docs/`: ninguno roto.
- `uv run pre-commit run --all-files`: en verde, sin cambios en `docs/`; `scripts/n3.sh` en 0.

**Revisión**

- Revisión propia de Claude Code sobre el diff completo; los hallazgos, sin corregir en `docs/`,
  constan en el PR (restos de referencias al Project y a su documento de seguimiento en §0, §1.1, §1.4 y §6.6
  de `hito-0.md`, y el hueco de §0 que T-02 dejó para T-03, resuelto en `AGENTS.md`).

**Pendiente**

- Archivar en el Project los documentos que ya viven en el repo (lo hace el chat tras fusionar).
- Pedro revisa en el PR, sobre todo, la tabla de tipo y reversibilidad de
  `docs/decisiones/README.md`.

### T-04 — Verificación temprana del plugin (V-plugin) y repo de prueba

*Hecha el 2026-11-26, en local y en la nube, con Claude Code. Sin issue.*

**Qué se hizo**

- Marketplace en `.claude-plugin/marketplace.json` y plugin mínimo en `plugin/` con la skill
  `hola`.
- `tests/test_plugin.py`: comprobaciones del marketplace, del manifiesto del plugin y de la skill.
- Repo de prueba `pdromer0/menairos-prueba`, con su `.claude/settings.json` y la copia de la skill
  en `.claude/skills/hola/`.
- Las pruebas de §1.6, hechas por Pedro con Claude Code 2.1.326:

| Prueba | Entorno | Cómo llega el plugin | Resultado |
| --- | --- | --- | --- |
| A1 | Local | Solo por el `.claude/settings.json` de `menairos-prueba`, tras aceptar la confianza en la carpeta | **Carga**: `/menairos:hola` responde con una ruta de la caché local de plugins. A2 no hizo falta. La copia (`/hola`) responde con `${CLAUDE_PLUGIN_ROOT}` sin sustituir |
| B | Nube | Solo por el `.claude/settings.json` del repo | **No carga**: `/menairos:hola` no existe y `claude plugin list` no muestra `menairos`. Coincide con la documentación |
| C | Nube, entorno dedicado `menairos-prueba` | El script de entorno ejecuta `claude plugin marketplace add "pdromer0/menairos#ci/h0-v-plugin"` y `claude plugin install menairos@menairos`, con `CLAUDE_CODE_PLUGIN_PREFER_HTTPS=1` | **Carga**: `/menairos:hola` responde «menairos 3.0.0.dev0 · cargado desde: /root/.claude/plugins/cache/menairos/menairos/3.0.0.dev0». `claude plugin list` muestra `menairos@menairos` 3.0.0.dev0 dos veces, habilitado, con Scope `user` (lo instaló el script) y Scope `project` (el `enabledPlugins` del repo): es un solo plugin |
| D | Nube | La copia de la skill en `.claude/skills/` (plan B) | **Carga**: `/hola` responde con `${CLAUDE_PLUGIN_ROOT}` sin sustituir |

- **Decisión de Pedro (2026-11-26):** opción 1, plugin más script de entorno en la nube; el plan B,
  probado, queda como respaldo; los plugins de la cuenta de claude.ai, como alternativa sin probar.
  Resultado reflejado en `diseno.md` 2.1 y 8, `hitos.md`, el ADR 0002 y `abiertas.md`.

**Decisiones del diff**

- El plugin vive en `plugin/` y no en la raíz: la caché solo copia el plugin, y `claude plugin
  validate` no avisa del `CLAUDE.md` de la raíz.
- Skill `hola` (`/menairos:hola`), cuya respuesta dice desde dónde se cargó.
- `description` añadida al marketplace por el aviso de `validate`.
- Sin `LICENSE` ni icono: son requisitos del catálogo de Anthropic (`--profile directory`) que no
  cambian el veredicto; la licencia queda aplazada (`abiertas.md`).
- La prueba A se hizo en dos pasos (A1 y, solo si hacía falta, A2).
- Entorno dedicado en la nube para la prueba C.
- Decisión de Pedro: opción 1, plan B como respaldo y claude.ai como alternativa sin probar.

**Medidas**

- Claude Code 2.1.326.
- `claude plugin validate` de `.` y de `./plugin`: «Validation passed», sin avisos.
- Ruta de carga en la nube: `/root/.claude/plugins/cache/menairos/menairos/3.0.0.dev0`.

**Diferencias con la documentación**

- `plugins/loading.md` y `plugins/org.md` no coinciden para un marketplace `github` con plugin de
  ruta relativa; en la práctica (A1) carga en local solo con el `settings.json` del proyecto.
- En la nube, con el marketplace registrado por el script, el `enabledPlugins` del repo también
  surte efecto (el plugin aparece con Scope `user` y `project`).
- Los plugins sincronizados desde claude.ai («Synced from claude.ai», por ejemplo
  `cowork-plugin-management@synced`) llegan a las sesiones en la nube. No se probó con Menairos.

**Versiones incorrectas**

Las seis del plan, cada una deshecha sin commit y con el test de `tests/test_plugin.py` que falló:

| Versión incorrecta | Test que falló |
| --- | --- |
| `version` de `plugin.json` distinta de la del paquete | `test_la_version_de_plugin_json_es_la_del_paquete` |
| Versión de la skill distinta de la del paquete | `test_la_version_de_la_skill_es_la_del_paquete` |
| Skill sin la línea de respuesta | `test_la_version_de_la_skill_es_la_del_paquete` |
| `source` mal | `test_el_source_de_la_entrada_existe_y_contiene_el_plugin` |
| Nombre de la entrada distinto del del plugin | `test_la_entrada_del_marketplace_se_llama_como_el_plugin` |
| Marketplace sin `owner` | `test_marketplace_es_json_valido_con_sus_campos_obligatorios` |

**Revisión**

- Revisión propia de Claude Code. El chat leyó la rama y `menairos-prueba` en GitHub; la copia de
  la skill es idéntica byte a byte.

**Pendiente**

- Tras fusionar: quitar el ref de `.claude/settings.json` de `menairos-prueba` y cambiar el script
  del entorno `menairos-prueba` a `"pdromer0/menairos"` sin ref.
- La capa nube de T-12 genera ese script.
- Actions, en T-26.
- La versión del plugin durante el desarrollo, en T-22.
- La línea de instalación del `README`, cuando se documente cómo se instala Menairos.

### T-05 — Esquemas JSON

*Hecha el 2026-11-27, en local (WSL2), con Claude Code (Opus 5.5, modo plan y después auto) a partir
de un encargo del chat. Sin issue. El plan pasó dos rondas: la primera, con las dudas P1–P5; la
segunda, con las respuestas de Pedro y sus ajustes A1–A4, revisados en el chat.*

**Qué se hizo**

- Los tres esquemas en `src/menairos/esquemas/` (`menairos`, `tareas` y `decisiones`, JSON Schema
  2020-12), dentro del paquete y leídos con `importlib.resources`. Todos llevan `$schema`, `$id`,
  `additionalProperties: false` en cada objeto, un `default` en cada clave opcional (salvo las
  cuatro sin valor natural) y una `description` en español en cada clave.
- `src/menairos/schemas.py`:
  - `load_schema` y `load_document`: TOML con `tomllib` y YAML con una subclase de
    `yaml.SafeLoader` que rechaza las claves repetidas;
  - `validate`: el esquema con `Draft202012Validator` y, después, las comprobaciones estrictas
    (`1.0` donde va un entero, un salto de línea final en un patrón anclado). Devuelve `Issue`s
    con la ruta del formato de 2.3 y el mensaje en español;
  - `apply_defaults`;
  - `is_marked`, que calcula la marca;
  - `check_decisions`: el id es de la tarea, no se repite, y difícil + alto + agente es un error.
- `tests/data/esquemas/`: 158 casos (48 válidos y 110 inválidos). Cada uno declara en su cabecera
  la regla que prueba y, si es inválido, la ruta y la palabra clave del error esperado.
  `tests/test_esquemas.py` (220 tests) comprueba que cada caso da exactamente esos errores y que
  cada regla de 2.2 tiene al menos un caso válido y uno inválido.
- El registro de decisiones empieza: `docs/specs/hito-0/decisiones/T-05.yaml`, con 20 decisiones
  (17 de Pedro y 3 del agente) y validado por un test.
- Cambios de especificación: §1.3, §2.2 y §2.5 de este documento; la cabecera y el criterio 1 de
  T-05 en `hito-0.tareas.yaml`; `diseno.md` §3.3 (la marca no se escribe); un punto nuevo en
  `abiertas.md` (dónde viven las plantillas, para T-09); y la sección «Contratos» de
  `lecciones.md`.

**Decisiones del diff**

Las 20 de `decisiones/T-05.yaml`. Las de Pedro:

- Los esquemas, dentro del paquete; jsonschema y PyYAML como dependencias del paquete; el registro
  de decisiones desde T-05.
- Módulo `schemas.py` (P1).
- Sin `default` en `motivo_critica`, `por_que_no_escalo`, `agente` ni `revisor` (P2).
- `revisor_plan` activo por defecto (P3).
- Ancla opcional en `especificacion` (P4).
- Lo aprobado en el plan va con `decidido_por: pedro` (P5, según §5.4: el encargo decía lo
  contrario).
- Estricto ahora donde es barato (A1): solo espacios = vacío; `1.0` no es un entero; la versión no
  admite metadatos de build (P6); un patrón anclado no acaba en salto de línea (P7).
- Un id de decisión repetido es un error (A2).
- Una clave repetida en YAML es un error de lectura (A3).
- `quien: codex` solo en manual, para T-06 (A4).
- Y las interpretaciones del plan: tablas con `default: {}`, `uniqueItems` en tres listas, formato
  de los errores, la matriz en código, el `$id` en `main` y el test del wheel.

Del agente, durante la implementación (con `decidido_por: agente`):

- `SCHEMA_NAMES` y `format_path` públicos, para T-06 (T-05-D18).
- Tras la revisión propia, `rama` y `proyecto.repo` rechazan también lo que git y GitHub no
  admiten (T-05-D19), con el mismo principio de A1.
- Las comprobaciones estrictas siguen en su recorrido, con un test que limita las palabras clave
  de los esquemas (T-05-D20), en lugar de ampliar el validador.

**Medidas**

- Versiones, resueltas por `uv add`: jsonschema 4.26.0 (con attrs 26.1.0, jsonschema-specifications
  2025.9.1, referencing 0.37.0 y rpds-py 2026.9.1) y PyYAML 6.0.4, todas con soporte para
  Python 3.14 (3.14.10) y wheels `cp314` donde hay código compilado. `uv tree --outdated`: ninguna
  desactualizada.
- pyright 1.1.414 trae los stubs de PyYAML y jsonschema: no hizo falta ningún `types-*`.
- El wheel (`uv build --wheel`) lleva `menairos/esquemas/*.schema.json`. `uv tool install --python
  3.14 .` en carpetas temporales: `menairos --version` responde, y la CLI instalada carga los tres
  esquemas desde su `site-packages`.
- Los 220 tests de `test_esquemas.py`, en menos de medio segundo; los 229 del repo, también.
- Tiempo: plan desde las 09:50 (hora local), aprobado a las 10:47; implementación y revisión hasta las
  11:15. La hora de apertura del PR y el resultado de la N3 constan en su cuerpo (Métricas y
  Comprobaciones).

**Diferencias con la documentación y hallazgos**

- JSON Schema 2020-12 cuenta `1.0` como entero, y `jsonschema` evalúa `pattern` con `re` de
  Python: `$` acepta un salto de línea final (`"T-01\n"` pasaba `^T-[0-9]{2,3}$`) y `\d` admite
  cifras que no son ASCII. Por eso los patrones usan `[0-9]` y el código rechaza el `1.0` y el
  salto final.
- `yaml.safe_load` se queda en silencio con el último valor de una clave repetida. `tomllib` ya da
  error («Cannot overwrite a value»).
- El hook `check-yaml` de pre-commit también rechaza las claves repetidas, así que esos casos van
  dentro del test y no en `tests/data/`.
- El `\S` de Python no cuenta U+FEFF como espacio, y ECMA-262 sí: «no vacío» usa `[^\s\uFEFF]`.
- `[a-z0-9._-]+` dejaba pasar ramas que git rechaza (`a..b`, `.x`, `x.`, `x.lock`, comprobado
  con `git check-ref-format --branch`).
- `diseno.md` §3.3 contaba «marcada» entre los campos del fichero de decisiones; la tabla de 2.2 se
  había quedado atrás en `area`, `modelos`/`revisores`, `modulos` y `especificacion`. Corregido.

**Versiones incorrectas**

Las 17 del plan, cada una aplicada sin commit, con los tests lanzados y deshecha con `git checkout`
(el árbol quedó limpio):

| Versión incorrecta | Tests que fallaron |
| --- | --- |
| Sin `additionalProperties: false` en `guardarrailes.max_turnos` | 2: el meta-test de objetos y `clave-desconocida-anidada` |
| `if` sin `required: ["critica"]` | 59: todos los válidos de tareas sin `critica`, empezando por `minimo` |
| Patrón de id sin anclas | 4, entre ellos `id-cuatro-digitos` |
| `texto_no_vacio` con `minLength: 1` | 4, entre ellos `nombre-solo-espacios` |
| `aviso_presupuesto_pct` con `exclusiveMaximum: 100` | 3, entre ellos `pct-100` |
| `revisor_plan` por defecto `inactivo` | 1: defaults = diseño §3.1 |
| `apply_defaults` con `default is not None` | 1: los defaults de una tarea (`modo: null`) |
| `apply_defaults` sin `deepcopy` | 1: las listas no se comparten |
| La comprobación de enteros sin seguir `$ref` | 4, entre ellos `paralelismo-uno-punto-cero` |
| La comprobación de enteros sobre cualquier `float` | 1: `paralelismo-decimal` (dos errores en vez de uno) |
| `is_marked` con `and` | 2: la marca con difícil + bajo y con reversible + alto |
| La matriz con `or` | 4: los tres válidos de la matriz y `T-05.yaml` |
| El id repetido comparado consigo mismo | 16: todos los válidos con decisiones |
| `yaml.safe_load` a secas | 1: la clave repetida en YAML |
| El cargador que cuenta `<<` como clave | 1: la fusión |
| Un cargador basado en `yaml.Loader` | 1: `!!python/tuple` |
| Índices como `.3` | 49: los inválidos con ruta de lista |

Y dos más tras la revisión propia: con `anyOf` en un esquema falla el test de palabras clave, y con
el `\S` de antes falla `titulo-solo-bom`.

La primera pasada de la novena no encontró su texto: `_strict` seguía los `$ref` al entrar y
`_children` también, así que quitar uno de los dos no lo habría detectado ningún test. Se dejó en
un solo sitio (commit `refactor:`) y entonces sí falló.

**Revisión**

- `/code-review` alto sobre el diff, antes de la N3: 10 hallazgos, clasificados antes de tocar
  nada.
- **Corregidos:**
  - un alias de YAML que se contiene a sí mismo hacía fallar `validate` con `ValueError` en lugar
    de dar un error (reproducido; ahora tiene test);
  - un texto que solo tiene U+FEFF pasaba como no vacío;
  - `rama` y `proyecto.repo` admitían nombres que git y GitHub rechazan;
  - las fechas salían en los mensajes como si fueran textos;
  - el patrón del id de tarea estaba copiado en `decisiones.schema.json` (ahora `$defs/id_tarea`,
    con un test de que coincide con el de tareas);
  - `SCHEMA_NAMES` repetía el `Literal` a mano;
  - los recorridos de las comprobaciones estrictas y de los defaults solo siguen `properties`,
    `items` y `$ref`: ahora un test limita los esquemas a esas palabras clave. La alternativa de
    ampliar el validador queda para T-06, si Pedro la prefiere.
- **Sin corregir:**
  - `1`/`true` o `1`/`1.0` como claves de YAML se dan por repetidas, porque en Python son la
    misma clave y una pisaría a la otra; los tres formatos solo usan claves de texto;
  - cachear el esquema y el validador: no hay ninguna medida que lo justifique; T-06 puede hacerlo
    si la hay.

**Pendiente**

- Para T-06:
  - `quien: codex` solo en modo manual (A4, decisión de Pedro);
  - A01 tiene que mirar el documento antes de aplicar los valores por defecto;
  - `spec validar` reutiliza `load_document`, `validate`, `Issue` y `format_path`.
- Para T-09: dónde viven las plantillas (`abiertas.md`; cerrado en T-09, T-09-D1).
- Para T-21: el nombre del fichero de decisiones frente a su `tarea`; de momento lo comprueba el
  test de los ficheros del repo.
- Casos conocidos que no se tratan: una `ventana_horaria` con inicio igual al fin, y las plantillas
  que no existen (E13).
- Con `v3.0.0` (T-28) se puede fijar el `$id` de los esquemas a la etiqueta.
- El grep de los nombres de los proyectos anteriores lo lanza Pedro o el chat: esta sesión no
  los conoce y no escribió ninguno.

### T-06 — `menairos spec validar`

*Hecha el 2026-11-27, en local (WSL2), con Claude Code (Opus 5.5, modo plan y después auto) a partir
de un encargo del chat. Sin issue. El plan llevaba las dudas P1–P7. Pedro lo aprobó sin
responderlas una a una, así que se aplicaron las recomendaciones. A mitad de la tarea, el chat
corrigió el encargo: E10 se comprueba siempre.*

**Qué se hizo**

- `menairos spec validar [--hito N] [--json] [--raiz RUTA]` (`src/menairos/cli.py`):
  - subórdenes de argparse;
  - salida legible o JSON `{"ok", "errores", "avisos"}`;
  - sale con 0, 1 o 2;
  - argparse en español: `uso:`, `opciones`, `-h` y los mensajes de error que da la orden.
- `src/menairos/spec_validation.py`:
  - E01–E12 y A01–A04, con `load_document`, `validate`, `apply_defaults` y `format_path` de
    `menairos.schemas`;
  - E07 con Tarjan iterativo: un error por componente fuertemente conexa, con el ciclo más corto
    como ejemplo;
  - si fallan E01 o E02, no se comprueban E03–E09, y E10–E12 siempre;
  - lo que falta es un error de uso; lo que no se puede leer, un error de su comprobación.
- `src/menairos/markdown.py`: los encabezados ATX fuera de los bloques cercados, su ancla como
  GitHub y sus secciones. T-09 y T-24 lo pueden reutilizar.
- `scripts/n3.sh` (y con él el CI) valida la especificación del propio repo, que pasa sin errores
  ni avisos.
- Tests:
  - `tests/test_markdown.py` (31): las anclas de `tests/data/spec_validar/anclas.md`, comparadas
    con las que dio GitHub;
  - `tests/test_spec_validar.py` (137): cada código, cada caso límite de 2.3, el JSON, los
    códigos de salida y el propio repo.
- Patrón del id de tarea: con tres dígitos no empieza por cero (P5). Hay casos nuevos en
  `tests/data/esquemas/`.
- Cambios de especificación:
  - §2.2, §2.3, §2.5, §4.5 y §4.7 de este documento (A04 de las fases pasa a A05);
  - T-06, T-10 y T-15 en `hito-0.tareas.yaml` (E13 pasa a T-10, que depende de T-06);
  - un punto nuevo en `abiertas.md` (`uv tool install` y el `uv.lock`, para T-22);
  - `lecciones.md`.

**Decisiones del diff**

Las 22 de `decisiones/T-06.yaml`.

De Pedro, en el encargo y en el plan:
- E13 pasa a T-10 y N3 valida el repo;
- verificar las anclas con la API de contenidos (P1);
- A04 y A05 (P2);
- el título de T-06 (P3);
- el lector propio de Markdown (P4);
- el patrón del id (P5);
- el hito del nombre frente al del YAML (P6);
- argparse en español (P7);
- y las interpretaciones del plan: errores de uso, orden de las comprobaciones (con la
  corrección de E10), E07 por componente, enlaces y anclas, rutas en Markdown, avisos y regla de
  anclas según GitHub.

Del agente (`decidido_por: agente`):
- dos casos de anclas que GitHub no confirmó (T-06-D17);
- `--hito` sin ceros delante y sin abreviaturas (T-06-D18);
- E09 para un destino ilegible y E08 para una carpeta (T-06-D19);
- escapes para los caracteres invisibles, también en un test de T-05 (T-06-D20);
- los commits 5 a 7 del plan, en uno (T-06-D21);
- tras la revisión, las listas numeradas y anidadas también valen en E10 (T-06-D22).

**Medidas**

- **`POST /markdown`** (`gh api markdown -f mode=gfm`), lanzado una vez con los casos difíciles:
  da los `<h2>`, pero sin `id`.
- **API de contenidos** con `Accept: application/vnd.github.html+json`:
  - sí da los `id`. Sobre `hito-0.md` de `main` (9b1f887), la regla coincidió en los 64
    encabezados;
  - sobre `tests/data/spec_validar/anclas.md`, subido a la rama antes del PR y leído una vez,
    dio los 50 valores que son ahora los esperados de `test_markdown.py`. Por ejemplo:
    - `idioma_docs-y-stackplantillas`;
    - `snake_case-y-a_b_c`;
    - `init-y-doble-y-doble`;
    - `hecho--y--revisado-`;
    - `c--c--10--23`;
    - `entidades---`;
    - `imagen--fin`;
    - `repetido`, `repetido-1`, `repetido-1-1`, `repetido-2`, `repetido-3`;
    - `é-combinado` (con la marca combinante);
    - `ελληνικά-漢字--` (sin `①` ni `²`);
    - `i̇stanbul-ß`;
    - `tabseparado`;
    - `norompible`;
    - `-1` para `¿?` (detrás de `## ✅`, que no tiene `id`).

    También dio `id` a los encabezados setext y a los de una lista o una cita (que Menairos no
    cuenta), y ninguno a `##` vacío.
- **El propio repo:** `uv run menairos spec validar` sale con 0, sin errores ni avisos; los 43
  enlaces de `hito-0.tareas.yaml` resuelven.
- **Tests:** 401 en el repo, todos en 2,6 s. Los 168 de T-06 tardan unos 2 s, y el ciclo de 1000
  tareas, menos de un segundo.
- **Tiempo:**
  - plan desde las 11:49 (hora local);
  - primer commit a las 11:53;
  - implementación y versiones incorrectas hasta las 12:11;
  - revisión propia y correcciones hasta las 12:14.

  La apertura del PR y la N3 constan en su cuerpo.

**Diferencias con la documentación y hallazgos**

- **`POST /markdown`:** no da `id` a los encabezados, así que no sirve para comprobar anclas. La
  API de contenidos con HTML sí los da.
- **La regla de 2.3** («se quitan los signos de puntuación salvo guiones») era incompleta:
  - GitHub conserva `_` y las marcas combinantes;
  - quita los símbolos, los emoji, los tabuladores, el espacio de no separación y cifras como `①`;
  - descodifica las entidades;
  - ignora las imágenes;
  - un sufijo que choca añade otro (`repetido-1-1`).

  2.3 está corregida. El `\w` de Python no sirve: quita las marcas y conserva `①`. Hace falta
  `\p{L}\p{M}\p{Nd}\p{Pc}`, el `\p{Word}` de Ruby.
- **A04** ya estaba usado en §4.5 para las fases «a revisar», que pasa a A05.
- **T-001 y T-01** cumplían los dos el patrón del id y eran ids distintos.
- **argparse:**
  - calcula el `prog` de las subórdenes con `prefix=""`, así que un `prefix or "uso: "` repetía
    «uso:» tres veces;
  - con `allow_abbrev`, `--js` valía por `--json`.
- **Caracteres invisibles:** escribir `"\ufeff"` en el código acabó, en este entorno, como un BOM
  literal invisible en el fichero. Lo detectó una versión incorrecta cuyo texto no aparecía.

**Versiones incorrectas**

38: las 25 del plan, algunas desglosadas, y las que salieron al implementar. Cada una se aplicó sin commit, se lanzaron los tests de T-06 y se
deshizo con `git checkout`; el árbol quedó limpio.

| Versión incorrecta | Tests que fallaron |
| --- | --- |
| Slug que quita `_` / con el `\w` de Python | 1 / 1: las anclas de GitHub |
| Slug que junta guiones | 7, entre ellos `63-menairos-cierre-n---aprobar` |
| Slug que quita acentos (NFKD) | 21 |
| Repetidos desde `-2` | 4, entre ellos `repetido-1` |
| Repetidos sin comprobar el choque (`if` en vez de `while`) | 0 al principio; con el test nuevo `a`, `a-1`, `a`, 1 |
| Encabezados de un cercado que cuentan | 9 |
| Cercado cerrado por el otro carácter | 3 |
| Markdown sin quitar el BOM | 1: BOM y CRLF |
| Entidades sin descodificar / imágenes con su texto | 1 / 1: las anclas de GitHub |
| Tarjan recursivo | 1: el ciclo de 1000 tareas |
| Un error por ciclo elemental | 2 |
| Componentes en el orden de un `set` | 1: varios ciclos a la vez |
| Autodependencia en el grafo | 0: equivalente, el filtro de tamaño ya la quita |
| Autodependencia como componente de E07 | 1: E06 sin E07 |
| E03–E09 con E01/E02 | 15 |
| E10 omitido con E01/E02 | 2 |
| E11 y E12 omitidos con E01 | 2 |
| A02 sobre los valores por defecto | 2 |
| A04 solo con `tareas[].modo` / con `== "automatico"` | 2 / 2 |
| Enlaces desde `--raiz` | 84 |
| Enlace sin ancla como E09 | 70 |
| Ancla en minúsculas antes de comparar | 1 |
| ✅ sin orden aceptada / con varios fragmentos | 6 / 1 |
| Justificación buscada en todo el fichero | 1 |
| E12 con «stack» en cualquier sitio / que cuenta README.md | 2 / 2 |
| Hito elegido por orden de texto | 1 |
| Hito del YAML sin comparar con el nombre | 1 |
| Salida 1 en un error de uso / con avisos | 5 / 1 |
| Error de uso en stdout | 5 |
| JSON con `ensure_ascii` | 1 |
| Prefijo de uso con `or` | 7 |
| El patrón de id de antes (`[0-9]{2,3}`) | 5, entre ellos `id-tres-digitos-con-cero` |

**Revisión**

- `/code-review` alto sobre la rama, antes de la N3: 8 hallazgos, clasificados antes de tocar
  nada.
- **Corregidos**, cada uno con un test que fallaba antes de la corrección:
  - una `--raiz` con `..` (`docs/..`) daba E08 en los 43 enlaces del repo (reproducido): la raíz
    se normaliza al empezar;
  - una ✅ con otra raya antes de la orden (« — `a` falla — `uv run x`») daba un falso E10;
  - las listas numeradas (`1. ✅ …`) y los subelementos sangrados se juntaban con el elemento
    anterior y daban un falso E10;
  - una carpeta que no se puede leer salía como una traza: ahora es E08, E12 o un error de uso;
  - `--json=x` daba el detalle de argparse en inglés.
- **Corregido en la especificación:** el E02 de un `hito` que no coincide con el nombre no corta
  E03–E09 (P6), pero el «Orden» de 2.3 no lo decía.
- **Sin corregir:**
  - un ADR que es un symlink a un fichero de fuera del repo cuenta para E12: es hipotético, y E12
    solo comprueba que exista uno;
  - el rendimiento (listar las carpetas en cada enlace): con 43 enlaces son milisegundos y no hay
    ninguna medida que lo justifique.

**Pendiente**

- **Para T-10:** E13, contra las plantillas de stack del paquete.
- **Para T-22:** si `uv tool install` respeta el `uv.lock` (`abiertas.md`).
- **Para T-15:** A05 (antes A04).
- **Sin verificar con GitHub:** si `##` vacío cuenta para los repetidos, y el orden «`a`, `a-1`,
  `a`» (T-06-D17).
- **El grep de los nombres de los proyectos anteriores:** lo lanza Pedro o el chat. Esta sesión no
  los conoce y no escribió ninguno.

### T-07 — Envoltorio de `gh api` y doble de GitHub con tope

*Hecha el 2026-11-27, en local (WSL2), con Claude Code (Opus 5.5, modo plan y después auto) a partir
de un encargo del chat. Sin issue. El plan llevaba las dudas P1–P4. Pedro lo aprobó sin
responderlas una a una, así que se aplicaron las recomendaciones. La excepción del `DELETE` venía
decidida en el encargo.*

**Qué se hizo**

- `src/menairos/github.py`, en dos capas:
  - **transporte `GhCli`:**
    - una orden `gh api --method M --include --header … -- RUTA` por petición;
    - el cuerpo va en JSON por stdin (`--input -`);
    - 30 s de tiempo máximo y `GH_PROMPT_DISABLED=1`;
    - lee la línea de estado, las cabeceras y el cuerpo de la salida de `--include`;
  - **cliente `GitHub`:**
    - `request`, `get`, `get_all`, `post`, `patch`, `put` y `delete`;
    - valida la ruta y rechaza GraphQL;
    - rechaza todo `DELETE` salvo el de `_ALLOWED_DELETES` (quitar una relación «blocked by»);
    - pagina siguiendo `Link: rel="next"`, con `per_page=100`;
    - reintenta solo un `GET` con 5xx, como mucho 3 veces, con esperas de 1, 2 y 4 s;
    - convierte los fallos en `GitHubError` o `RateLimited`, con el código HTTP y un mensaje en
      español.
- `tests/doble_github.py`:
  - `FakeGitHub`, que guarda en memoria etiquetas, milestones, issues y PRs y relaciones «blocked
    by»;
  - registra las llamadas, pagina como GitHub y admite fallos programables (por número de llamada,
    método o ruta, una o varias veces, y con la escritura hecha);
  - lanza `RunawayLoop` al pasar su tope (500 por defecto).
- `tests/conftest.py`:
  - la fixture `doble_github`, que conecta el doble a `menairos.github` y anota las esperas sin
    esperar;
  - la fixture autouse `_sin_github_real`, que hace fallar cualquier ejecución de `gh`, en dos capas:
    - en el proceso de pytest, un `subprocess.Popen` que la rechaza con `RealGitHubCall` (también tras
      `env`, en `sh -c` y en cada orden de una línea de shell);
    - en los procesos hijos y en `os.system`, un `gh` falso, primero en el `PATH`, que sale con 97.
- Tests:
  - `tests/test_github.py` (137): argv, salida, rutas, `DELETE`, GraphQL, errores, reintentos y
    paginación;
  - `tests/test_doble_github.py` (47): paginación, fidelidad, fallos, tope y fixture;
  - `tests/test_sin_github_real.py` (34): la fixture autouse y el test estático, que recorre con
    `ast` los módulos de `src/menairos/` salvo `github.py`.
- Cambios de especificación:
  - §2.4 de este documento: la excepción del `DELETE` y dónde están el envoltorio y el doble;
  - el 4.º criterio de T-07 en `hito-0.tareas.yaml`;
  - en `abiertas.md`, la nota sobre la ruta de «blocked by» (para T-08) y un punto nuevo, la
    versión de `gh` en la nube;
  - `lecciones.md`.

**Decisiones del diff**

Las de `decisiones/T-07.yaml`.

De Pedro, en el encargo y en el plan:
- la excepción del `DELETE`, sin tocar `.claude/settings.json` ni `AGENTS.md` (P4);
- dónde van el envoltorio, el doble y la fixture;
- las dos capas;
- la paginación propia con `Link`;
- solo cuatro opciones de `gh`, con la versión mínima comprobada (P2);
- solo REST;
- los errores;
- los reintentos (P1);
- la fidelidad del doble;
- `RunawayLoop` como `BaseException`;
- las dos barreras;
- la comprobación real;
- el criterio nuevo (P3).

Del agente (`decidido_por: agente`):
- rutas más estrictas que en el plan: solo ASCII visible, sin tramos vacíos ni `.`/`..`, sin
  cuerpo en `GET`/`DELETE` y con `--` antes de la ruta (T-07-D15);
- `Response.text` y las piezas públicas para probarlas por separado (T-07-D16);
- el doble rechaza también los parámetros y campos que no modela (T-07-D17);
- tras la revisión, la barrera en dos capas (T-07-D18);
- tras la revisión, más reglas de la ruta, los parámetros, el `next` y las cabeceras de límite
  (T-07-D19).

**Medidas**

- **Comprobación real**, una vez y en solo lectura, contra `pdromer0/menairos-prueba` con
  `GitHub(GhCli())`:
  - `get_all("repos/pdromer0/menairos-prueba/labels", {"per_page": 2})` dio 10 etiquetas en 5
    páginas, de unos 1,2 s cada una;
  - el `Link` de cada página apunta a `https://api.github.com/repositories/1473593649/labels?per_page=2&page=N`
    (no a `repos/{dueño}/{repo}`), con `prev`, `next`, `last` y `first` en ese orden. La primera
    página solo lleva `next` y `last`, y la última, `prev` y `first`. El doble copia esa forma;
  - un `GET` de una etiqueta que no existe: `gh` sale con 1 y escribe `gh: Not Found (HTTP 404)`
    en stderr, pero la línea de estado, las cabeceras y el cuerpo salen por stdout. El cuerpo es
    `{"message": "Not Found", "documentation_url": …, "status": "404"}`, con `status` como texto;
  - en la salida de `--include`, la línea de estado acaba en LF y las cabeceras en CRLF.
- **Versiones de `gh`:**
  - `--method`, `--include`, `--input` y `--header` ya están en el código fuente de `gh` en sus
    versiones 1.0.0 y 2.0.0 (leído por la API de contenidos): la versión mínima es 1.0.0;
  - WSL2: 2.103.3;
  - Actions (`ubuntu-24.04`, según la lista de software de la imagen del runner): 2.105.0;
  - la nube: sin comprobar desde aquí (`abiertas.md`).
- **Tests:** 620 en el repo, en unos 3 s; los 218 de T-07, en 0,3 s, sin ninguna espera real.
- **Tiempo:**
  - plan desde las 13:31 (hora local);
  - primer commit a las 13:34;
  - comprobación real a las 13:39;
  - implementación y versiones incorrectas hasta las 13:49;
  - revisión propia y correcciones hasta las 14:01.

  La apertura del PR y la N3 constan en su cuerpo.

**Diferencias con la documentación y hallazgos**

- **Ayuda de `gh api`:** sin `--slurp`, `--paginate` no junta las páginas en un solo JSON. Con él
  haría falta una versión reciente de `gh` que en la nube no está comprobada.
- **El `Link` de GitHub** cambia `repos/{dueño}/{repo}` por `repositories/{id}`: quien siga las
  páginas no puede reconstruir la URL a mano, y el doble tiene que aceptar las dos formas.
- **`--input` y `-f`** cambian el método por defecto de `gh api` a POST: el envoltorio pasa
  siempre `--method`.
- **`gh api` también sustituye `:owner`, `:repo` y `:branch`** en la ruta (lo dice su código, no
  su ayuda): un nombre de etiqueta como `estado:repo` sin codificar iría a otra ruta.
- **Patrón del `DELETE`:** sin prohibir los tramos `..`, `repos/x/../issues/1/…` lo pasaría, con
  `..` como nombre de repo. Por eso las rutas rechazan `.` y `..`.

**Versiones incorrectas**

35: cada una se aplicó sin commit con un script, se lanzaron los tests de T-07 y se deshizo con
`git checkout`; el árbol quedó limpio.

| Versión incorrecta | Tests que fallaron |
| --- | --- |
| `DELETE` con `match` en vez de `fullmatch` / con ceros delante | 5 / 2 |
| `DELETE` comprobado después de llamar al transporte | 23 |
| Método sin pasar a mayúsculas | 13 |
| GraphQL solo con `== "graphql"` | 4 |
| Ruta que empieza por `-` / con llaves / con `.` y `..` | 1 / 1 / 2 |
| Sin `--method` / cuerpo con `-f` / sin `timeout` | 2 / 1 / 1 |
| Separador de cabeceras solo con LF / cabeceras sensibles a mayúsculas | 4 / 5 |
| Paginación por página corta y `page+1` / sin `per_page=100` / sin detectar el `next` repetido | 5 / 8 / 1 |
| Reintento en escrituras / en 4xx | 9 / 14 |
| 2 reintentos / 4 reintentos | 4 / 2 |
| Espera constante / sin inyectar | 3 / 6 |
| 403 de límite como permiso / 422 sin el detalle | 4 / 4 |
| Tope con `>=` / `RunawayLoop(Exception)` | 5 / 1 |
| Tope que no se repite | 0: equivalente, porque las llamadas solo crecen. El indicador se quitó (commit `refactor:`) |
| Doble con `state=all` por defecto / con `id == number` / con etiquetas sensibles a mayúsculas | 1 / 2 / 1 |
| `fail(call=N)` desde 0 / `apply` que no escribe | 3 / 1 |
| Sin la fixture autouse (con un `gh` falso primero en el `PATH`, para no llamar a GitHub) | 9 |
| Sin el `gh` falso de la fixture (con otro `gh` falso que sale con 3) | 2: el proceso hijo y `os.system` |
| Test estático que solo ve `"gh"` exacto | 4 |

**Revisión**

- `/code-review` alto sobre la rama, antes de la N3: 10 hallazgos, clasificados antes de tocar
  nada.
- **Corregidos**, cada uno con su test. Los 14 tests nuevos del envoltorio fallan con el código de
  antes. Los de la barrera no se lanzaron contra la barrera de antes, porque habrían ejecutado el
  `gh` real; la capa del `PATH` se comprobó con su versión incorrecta (tabla de arriba):
  - la barrera solo vigilaba el proceso de pytest: un proceso hijo, `os.system` o `cd x && gh …`
    lanzaban el `gh` real (ahora, el `gh` falso en el `PATH` y un `launches_gh` que mira más
    allá de la primera palabra);
  - `gh` sustituye `:owner`, `:repo` y `:branch` en la ruta (comprobado en su código);
  - una lista o `None` en los parámetros se mandaba como texto de Python;
  - un `next` de otro host (GitHub Enterprise) se habría seguido con el prefijo `/api/v3` repetido;
  - un `Retry-After` con `²` o un `X-RateLimit-Reset` fuera de rango rompían el mensaje de error;
  - preparar el doble con una etiqueta, un milestone o un issue que no existen daba la excepción
    interna del doble (ahora, un `ValueError` que dice qué falta);
  - el doble rehacía su tabla de rutas en cada llamada;
  - `abiertas.md`, el registro y este anexo nombraban otros proyectos por su nombre (`AGENTS.md`):
    ahora se citan de forma genérica.
- **Sin corregir:** la doble comprobación de las etiquetas al crear un issue en el doble (422 en la
  ruta y `ValueError` en `add_issue`) se queda: son dos errores distintos, para el código probado y
  para quien prepara el test.

**Pendiente**

- **Para T-08:**
  - verificar la ruta de «blocked by» y, si cambia, el patrón de `_ALLOWED_DELETES` y las rutas
    del doble a la vez;
  - ampliar el doble con lo que necesite, sin relajar su «más estricto ante la duda»;
  - los tests de `spec publicar` usan la fixture `doble_github`.
- **Versión de `gh` en la nube:** Pedro la mira con `gh --version` en una sesión en la nube, o se
  cierra en T-22 (`abiertas.md`).
- **Un ancla del anexo de T-06** («istanbul» con U+0307 tras la i) lleva la marca combinante
  literal, porque es el ancla que dio GitHub. Ya estaba en `main`, y T-07 no la toca.
- **El grep de los nombres de los proyectos anteriores:** lo lanza Pedro o el chat. Esta sesión no
  los conoce y no escribió ninguno.

### T-08 — `menairos spec publicar`

*Hecha el 2026-11-27, en local (WSL2), con Claude Code (Opus 5.5, modo plan y después auto) a partir
de un encargo del chat. Sin issue. Tarea crítica: antes de enseñarlo, un subagente revisó el plan a
la contra (18 hallazgos, incorporados). Pedro lo revisó en el chat y aprobó P1–P8 con la
recomendación, más un añadido: las dependencias entre tareas del hito solo se gestionan en el
YAML.*

**Qué se hizo**

- `menairos spec publicar [--hito N] [--seco] [--json] [--raiz RUTA]` (`src/menairos/cli.py`):
  - comparte `--hito`, `--json` y `--raiz` con `spec validar`;
  - salida legible o JSON;
  - sale con 0, 1 o 2.
- `src/menairos/spec_publication.py` (`publish_spec`):
  - la precondición de `spec validar` y los límites de GitHub, antes de cualquier llamada;
  - primero lee todo y comprueba las marcas repetidas; después escribe etiquetas, milestone,
    issues y dependencias, con 1 s entre escrituras;
  - la tabla de idempotencia de 2.4, con el issue releído antes de cada `PATCH`;
  - las dependencias, sincronizadas siempre y solo entre issues con marca del hito, por id;
  - ante un fallo de GitHub, dice qué escritura quedó con resultado desconocido.
- `src/menairos/task_issues.py`:
  - el título, el cuerpo y las etiquetas del issue de una tarea;
  - la marca, con la huella de tres partes;
  - la lectura de la marca, en dos niveles;
  - las etiquetas de la vez anterior, deducidas de la huella.

  T-19 lo puede reutilizar para el `desfase`.
- `src/menairos/labels.py`: el catálogo de `diseno.md` 3.4, con el color y la descripción de cada
  etiqueta, y los límites de GitHub. T-12 lo reutilizará.
- `src/menairos/github.py`:
  - `GitHub(write_interval=…)`, la pausa entre escrituras;
  - el patrón del único `DELETE` ya era el bueno: solo cambia su comentario.
- `tests/doble_github.py`, más fiel y más estricto:
  - `POST` de «blocked by» devuelve el issue bloqueado;
  - el duplicado y la autodependencia dan 422 con solo un `message`;
  - `add_foreign_blocked_by` crea un bloqueante de otro repo;
  - los límites de longitud de GitHub dan 422.
- `tests/data/spec_publicar/ejemplo/`: un proyecto sintético, el hito 0 con 4 tareas y 2 áreas, que
  pasa `spec validar` sin errores ni avisos. Lo usan los tests y es lo que se publicó en
  menairos-prueba.
- Tests (169 nuevos):
  - `tests/test_spec_publicar.py` (118): la tabla de idempotencia, los casos límite de 2.4 y del
    plan, la CLI y los dos barridos de fallos;
  - `tests/test_cuerpo_issue.py` (31): los cuerpos esperados, escritos a mano, y la huella,
    recalculada con `hashlib`;
  - `tests/test_etiquetas.py` (5): el catálogo frente a la tabla de 3.4;
  - 10 en `tests/test_doble_github.py` y 4 en `tests/test_github.py`.
- Cambios de especificación:
  - §2.4 de este documento, reescrita: la huella, el cuerpo, las etiquetas, el milestone, lo que se
    lee antes de escribir, los límites, la tabla de idempotencia, la regla de las dependencias, la
    pausa, la salida y lo verificado;
  - `abiertas.md`: se cierra la ruta de «blocked by» (resultado abajo) y se abre la unificación de
    la plantilla de issue con el cuerpo generado, para T-09;
  - `lecciones.md`.

**Decisiones del diff**

Las 21 de `decisiones/T-08.yaml`.

De Pedro, en el encargo y en el plan:
- la huella en la marca, en tres partes (decisión 1 y P1);
- la actualización por partes, con el issue releído (P2);
- las dependencias, siempre y solo entre issues del hito, y solo desde el YAML (P3 y el añadido);
- el título del milestone (P4);
- la verificación de la ruta (P5);
- el ejemplo (P6);
- la pausa (P7);
- la plantilla de issue (P8);
- el cuerpo generado;
- las etiquetas propias y el modo;
- leer antes de escribir;
- la salida;
- ninguna escritura fuera de menairos-prueba (decisión 2).

Del agente (`decidido_por: agente`):
- la lectura y la escritura en un solo commit (T-08-D14);
- cuatro ejecuciones reales más (T-08-D15);
- los avisos `titulo-reescrito` e `issue-cambiado` (T-08-D16);
- el test del CRLF endurecido (T-08-D17);
- tras la revisión:
  - las etiquetas siempre propias (T-08-D18);
  - la marca fuera de los bloques de código (T-08-D19);
  - los mensajes de un fallo de escritura (T-08-D20);
  - un solo camino para el modo seco (T-08-D21).

**Medidas**

- **La ruta de «blocked by»**, primero en la documentación de GitHub (issue-dependencies,
  2022-11-28) y después contra `pdromer0/menairos-prueba`. Se crearon los issues de prueba #1 (A),
  #2 (B) y #3 (C, cerrado), y los tres quedaron cerrados al terminar.

  | Llamada | Resultado |
  | --- | --- |
  | `POST …/issues/1/dependencies/blocked_by {"issue_id": <id de B>}` | 201, con el issue **bloqueado** (#1), no el que bloquea |
  | El mismo `POST` repetido | 422: «An error occurred while adding the blocking issue to the issue. Validation failed: Target issue has already been taken», solo con `message`, sin `errors` |
  | `{"issue_id": <id de A>}` en A | 422: «… Target issue cannot be the same as the source issue» |
  | `{"issue_id": <id de C>}` (cerrado) | 201 |
  | `{"issue_id": 0}` | 404 |
  | `GET …/issues/1/dependencies/blocked_by` | B y C, con su `id` (C cerrado) |
  | `DELETE …/issues/7/dependencies/blocked_by/<id>`, lanzado por la CLI | 200, con el issue bloqueado (#7) |

  - **Ruta:** `…/issues/{n}/dependencies/blocked_by` y, para quitar, `…/blocked_by/{issue_id}`.
  - **Id o número:** el **id** del issue que bloquea, en el cuerpo y en el `DELETE`.

  Coincide con el patrón de `_ALLOWED_DELETES` y con las rutas del doble, que no cambian. El doble
  sí cambia: devolvía el issue que bloquea y un 422 con `errors`. No se probó un número de issue
  como `issue_id`: los id son globales, y uno pequeño puede ser el de un issue real de otro repo.

  El listado de issues trae `issue_dependencies_summary`, y en él `total_blocked_by` cuenta
  también los cerrados; `spec publicar` no lo usa todavía.
- **Publicación real en menairos-prueba**, con `--raiz tests/data/spec_publicar/ejemplo` y siempre
  con `menairos.github`. Lo que se creó: las 12 etiquetas (las 10 de 3.4, `area:datos` y
  `area:entorno`), el milestone #1 «Hito 0 — Ejemplo de spec publicar (T-08)», los issues #4 a #7
  (T-01 a T-04) y las relaciones #5 ← #4, #6 ← #4 y #7 ← #5, #6.

  | Ejecución | Escrituras | Tiempo |
  | --- | --- | --- |
  | `--seco` | 0 (haría 21) | — |
  | 1.ª | 21 | 51 s (20 pausas de 1 s) |
  | 2.ª | **0** (7 GET) | 8 s |
  | 3.ª, con una variante en el scratchpad (T-04 sin depender de T-03 y un criterio de T-02 cambiado) | 3: 2 `PATCH` del cuerpo y el `DELETE` | 16 s |
  | 4.ª, la misma variante | 0 | — |
  | 5.ª y 6.ª, con un transporte que anota las respuestas: el original y otra vez la variante | 3 y 3 (las respuestas, en la tabla de arriba) | — |
  | 7.ª, el original | 3: deja el repo como el ejemplo | — |
  | 8.ª, después de guardar con `gh api` el cuerpo de #4 con CRLF (GitHub lo guarda tal cual, también al final) | **0** | — |
  | 9.ª, el original, con el código final (tras la revisión) | **0** | — |

  Las huellas de los cuatro issues reales son las del test de valor fijo
  (`test_las_huellas_del_ejemplo_no_cambian_sin_querer`). En el HTML del issue #6, la marca no
  aparece y la casilla es una `task-list-item`. Los enlaces dan 404 porque el ejemplo no está en
  ese repo.
- **`--seco` contra `pdromer0/menairos`** (rama de T-08, solo GET, 4 s; repetido con el código
  final, con la misma salida): haría 91 escrituras, que
  son 17 etiquetas, el milestone, los 28 issues y las 45 dependencias. No hay ningún aviso: el repo
  no tiene issues con marca, solo los 6 PR de T-02 a T-07, que se ignoran. La salida:

  ```text
  spec publicar · hito 0 · pdromer0/menairos
  En seco: no se escribe nada en GitHub; esto es lo que haría.

  Se crearían (91):
    etiqueta     tipo:tarea
    etiqueta     tipo:bug
    etiqueta     tipo:idea
    etiqueta     critica
    etiqueta     modo:manual
    etiqueta     modo:didactico
    etiqueta     modo:automatico
    etiqueta     en-curso
    etiqueta     necesita-pedro
    etiqueta     aprobado-pedro
    etiqueta     area:arranque
    etiqueta     area:contratos
    etiqueta     area:plantillas
    etiqueta     area:entorno
    etiqueta     area:especificar
    etiqueta     area:implementar
    etiqueta     area:cierre
    milestone    (nuevo) Hito 0 — Núcleo en modo manual
    issue        (nuevo) T-01 · Repo, protección y pasos manuales
    issue        (nuevo) T-02 · Esqueleto del paquete, stack, CI y comprobaciones deliberadas
    issue        (nuevo) T-03 · Documentos al repo y los 20 ADRs
    issue        (nuevo) T-04 · Verificación temprana del plugin (V-plugin) y repo de prueba
    issue        (nuevo) T-05 · Esquemas JSON
    issue        (nuevo) T-06 · menairos spec validar (E01–E12 y avisos)
    issue        (nuevo) T-07 · Envoltorio de gh api y doble de GitHub con tope
    issue        (nuevo) T-08 · menairos spec publicar
    issue        (nuevo) T-09 · Plantillas de documentos y sustitución {{…}}
    issue        (nuevo) T-10 · Plantillas base y python-uv, manifiesto y composición
    issue        (nuevo) T-11 · menairos entorno: capas local y repo
    issue        (nuevo) T-12 · menairos entorno: capas GitHub y nube, y --comprobar
    issue        (nuevo) T-13 · Comprobaciones deliberadas automáticas
    issue        (nuevo) T-14 · /preparar-entorno
    issue        (nuevo) T-15 · /crear-spec (lluvia de ideas) con spec nuevo, estado y fase
    issue        (nuevo) T-16 · Modo MVP, inventario-mvp y E14
    issue        (nuevo) T-17 · /crear-spec --siguiente
    issue        (nuevo) T-18 · /validar-spec, revisor (Claude y Codex), informe y E15
    issue        (nuevo) T-19 · menairos contexto
    issue        (nuevo) T-20 · Hooks en Python (incluido el anti-bucle)
    issue        (nuevo) T-21 · menairos decisiones validar
    issue        (nuevo) T-22 · /implementar (manual y didáctico) y revisor-plan
    issue        (nuevo) T-23 · /sincronizar y mutante
    issue        (nuevo) T-24 · menairos informe
    issue        (nuevo) T-25 · menairos cierre --aprobar y /cerrar-hito
    issue        (nuevo) T-26 · Verificaciones en Actions (App menairos-agente)
    issue        (nuevo) T-27 · Prueba de punta a punta
    issue        (nuevo) T-28 · Cierre del H0 y v3.0.0
    dependencia  (nuevo) T-02 depende de (nuevo) T-01
    dependencia  (nuevo) T-03 depende de (nuevo) T-02
    dependencia  (nuevo) T-04 depende de (nuevo) T-02
    dependencia  (nuevo) T-05 depende de (nuevo) T-02
    dependencia  (nuevo) T-06 depende de (nuevo) T-05
    dependencia  (nuevo) T-07 depende de (nuevo) T-02
    dependencia  (nuevo) T-08 depende de (nuevo) T-06
    dependencia  (nuevo) T-08 depende de (nuevo) T-07
    dependencia  (nuevo) T-09 depende de (nuevo) T-05
    dependencia  (nuevo) T-10 depende de (nuevo) T-09
    dependencia  (nuevo) T-10 depende de (nuevo) T-06
    dependencia  (nuevo) T-11 depende de (nuevo) T-10
    dependencia  (nuevo) T-12 depende de (nuevo) T-11
    dependencia  (nuevo) T-12 depende de (nuevo) T-07
    dependencia  (nuevo) T-13 depende de (nuevo) T-10
    dependencia  (nuevo) T-14 depende de (nuevo) T-12
    dependencia  (nuevo) T-14 depende de (nuevo) T-13
    dependencia  (nuevo) T-15 depende de (nuevo) T-09
    dependencia  (nuevo) T-16 depende de (nuevo) T-15
    dependencia  (nuevo) T-17 depende de (nuevo) T-15
    dependencia  (nuevo) T-18 depende de (nuevo) T-06
    dependencia  (nuevo) T-18 depende de (nuevo) T-08
    dependencia  (nuevo) T-18 depende de (nuevo) T-15
    dependencia  (nuevo) T-19 depende de (nuevo) T-06
    dependencia  (nuevo) T-19 depende de (nuevo) T-07
    dependencia  (nuevo) T-20 depende de (nuevo) T-10
    dependencia  (nuevo) T-21 depende de (nuevo) T-05
    dependencia  (nuevo) T-22 depende de (nuevo) T-19
    dependencia  (nuevo) T-22 depende de (nuevo) T-20
    dependencia  (nuevo) T-22 depende de (nuevo) T-21
    dependencia  (nuevo) T-23 depende de (nuevo) T-07
    dependencia  (nuevo) T-23 depende de (nuevo) T-22
    dependencia  (nuevo) T-24 depende de (nuevo) T-21
    dependencia  (nuevo) T-24 depende de (nuevo) T-07
    dependencia  (nuevo) T-25 depende de (nuevo) T-24
    dependencia  (nuevo) T-26 depende de (nuevo) T-04
    dependencia  (nuevo) T-27 depende de (nuevo) T-14
    dependencia  (nuevo) T-27 depende de (nuevo) T-16
    dependencia  (nuevo) T-27 depende de (nuevo) T-17
    dependencia  (nuevo) T-27 depende de (nuevo) T-18
    dependencia  (nuevo) T-27 depende de (nuevo) T-22
    dependencia  (nuevo) T-27 depende de (nuevo) T-23
    dependencia  (nuevo) T-27 depende de (nuevo) T-25
    dependencia  (nuevo) T-28 depende de (nuevo) T-26
    dependencia  (nuevo) T-28 depende de (nuevo) T-27

  Resultado: haría 91 escrituras.
  ```
- **Tests:** 789 en el repo, en unos 8 s; los 154 de los tres ficheros nuevos, en unos 5 s. El
  barrido de la actualización (18 llamadas × 2) tarda 1,4 s.
- **Tiempo:**
  - plan desde antes de las 15:55 (hora local);
  - aprobación a las 16:15;
  - verificación de la ruta, de 16:15 a 16:16;
  - primer commit a las 16:17;
  - implementación hasta las 16:40;
  - versiones incorrectas, de 16:36 a 16:40;
  - publicación real, de 16:40 a 16:45;
  - revisión propia y correcciones, de 16:47 a 17:02.

  La apertura del PR y la N3 constan en su cuerpo.

**Diferencias con la documentación y hallazgos**

- **La documentación de issue-dependencies no dice qué issue devuelven** el `POST` y el `DELETE`:
  es el bloqueado. Tampoco da la forma del 422, que solo trae `message`.
- **GitHub guarda el cuerpo tal como llega, CRLF incluido**: quien busque la marca anclada al
  final de la línea tiene que pasar antes a LF.
- **2.4 decía «Milestone «Hito N — título»»**, pero el `titulo` del YAML ya empieza así (P4).
- **La revisión a la contra del plan** encontró, entre otros:
  - escribir sobre una lectura de minutos antes, que podía deshacer un `en-curso`;
  - una prueba con un número de issue como `issue_id`, que podía escribir fuera del repo de
    prueba;
  - que el listado de bloqueantes tenía que incluir los cerrados;
  - que el CRLF tenía que pasarse a LF antes de buscar la marca.

**Versiones incorrectas**

34. Cada una se aplicó sin commit con un script, se lanzaron los tests de T-08 (y los del
envoltorio y del catálogo) y se deshizo con `git checkout`; el árbol quedó limpio.
- Una no hizo fallar su test a la primera: la del CRLF. El test se endureció (T-08-D17) y después
  falló.
- Después de las correcciones de la revisión, se lanzaron otra vez las 34 sobre el código final; la
  tabla da esa segunda pasada.
- Como el script deshace con `git checkout -- src`, se lanza siempre con las correcciones ya en un
  commit.

| Versión incorrecta | Tests que fallaron |
| --- | --- |
| Huella sin la parte de las etiquetas | 12, entre ellos `test_modo_de_publicar_se_quita` |
| Contenido comparado con la marca dentro | 13 |
| Issues buscados por título | 7 |
| `GET issues` sin `state=all` | 4 |
| Los PR sin filtrar | 1 |
| `get` en vez de `get_all` | 2, entre ellos el de más de 100 issues |
| Marcas repetidas comprobadas tras crear las etiquetas | 2 |
| Dependencia con el número en vez del id | 89 |
| Relaciones comparadas por número / se quitan todas las que sobran | 1 / 1: `test_relaciones_ajenas_no_se_tocan` |
| Dependencias escritas junto a cada issue | 3, entre ellos la dependencia hacia delante |
| Relaciones de publicar = solo las de las tareas del YAML | 1 |
| Dependencias solo con la huella distinta | 18, entre ellos los barridos de fallos |
| `PATCH` sin releer el issue | 6 |
| Issue cerrado tratado como abierto | 3 |
| Se quita cualquier `modo:*` / sin deducir, un `modo:*` se quita / no se quita el de publicar | 4 / 4 / 2 |
| Choque de modo: se añade igual | 1 |
| Cuerpo reescrito aunque su parte no cambie / aviso de cuerpo reescrito siempre | 2 / 8 |
| Marca sin anclar a la línea | 3 |
| CRLF sin pasar a LF | En la primera pasada, 0; con el test endurecido, 3 |
| Etiquetas comparadas con mayúsculas / milestones sin `state=all` | 1 / 1 |
| `--seco` que escribe / sin la precondición / sin comprobar los límites | 3 / 2 / 3 |
| Sin pausa / pausa antes de la primera escritura / pausa en los GET | 1 / 4 / 3 |
| Sale con 0 tras un fallo / JSON con `ensure_ascii` | 2 / 1 |
| Etiqueta de área sin límite en el catálogo | 2 |

**Revisión**

- `/code-review` alto sobre la rama, antes de la N3: 10 hallazgos, clasificados antes de tocar
  nada.
- **Corregidos**, cada uno con un test que falla con el código de antes (9 tests nuevos, los 9
  comprobados contra el commit anterior a las correcciones):
  - una `critica` o un `area:*` de más se quedaban cuando la huella deducía las etiquetas de antes,
    y se quitaban cuando no; ahora se quitan siempre, porque son de publicar;
  - un issue cerrado durante la publicación (`issue-cambiado`) recibía igual sus dependencias;
  - un `ForbiddenRequest` del envoltorio (un `next` fuera de api.github.com) salía como una
    traza, sin informe;
  - un bug que citara el cuerpo de un issue dentro de un bloque de código se llevaba su marca: o
    paraba todo con `marca-repetida`, o se quedaba el issue;
  - con la marca ilegible, el título se reescribía sin aviso, y el cuerpo sí avisaba;
  - un 4xx en una escritura se presentaba como «resultado desconocido»;
  - `_stop` no se usaba;
  - el modo seco tenía su propio camino para el informe, que podía separarse del real.

  Ahora hay un solo `_apply`, cuyo `_send` no llama a GitHub en seco.
- **Corregido en la especificación:** el texto de 2.4 decía que las dependencias se sincronizan
  «entre los issues» con marca, también los de tareas borradas. Se podía leer que el issue de una
  tarea borrada también se sincroniza, y no se hace: «no se toca» (P3). El texto lo aclara.
- **Sin corregir:**
  - la marca no tiene que ser la última línea: Pedro escribe sus notas al final del cuerpo, y
    pasaría a crearse un issue duplicado;
  - en un choque de modo, la huella guarda el modo del YAML. Si Pedro cambiara después su
    etiqueta justo por esa y el YAML quitara el modo, publicar la quitaría. Es la contrapartida
    elegida en el plan: con la huella de las etiquetas que se ponen, la orden no convergería y
    escribiría en cada ejecución.

**Pendiente**

- **Para Pedro, tras fusionar:**
  - publicar el hito 0 en `pdromer0/menairos` con `uv run menairos spec publicar`, con `--seco`
    delante (el de arriba es el de esta rama);
  - cerrar los issues de T-01 a T-08 con un enlace a su PR (§0). `spec publicar` nunca cierra
    nada.
- **En menairos-prueba quedan:**
  - los issues #4 a #7 del ejemplo, abiertos;
  - el milestone #1;
  - las 12 etiquetas.

  Pedro puede cerrarlos cuando quiera. Si se publicara otra vez el ejemplo, no se duplicaría nada.
- **Para T-09:** unificar la plantilla de issue «Tarea» con el cuerpo generado (`abiertas.md`;
  cerrado en T-09, T-09-D2).
- **Para T-19:** el `desfase` puede reutilizar `task_issues` (la marca y la huella).
- **Sin probar en real**, para no crear etiquetas que no se pueden borrar:
  - los límites de longitud de GitHub (50, 256 y 65 536), que salen de su documentación y de sus
    mensajes de error;
  - asignar un milestone cerrado a un issue nuevo.
- **Al reescribir un cuerpo**, las casillas marcadas a mano se pierden; el aviso `cuerpo-reescrito`
  lo dice.
- **El grep de los nombres de los proyectos anteriores:** lo lanza Pedro o el chat. Esta sesión no
  los conoce y no escribió ninguno.

**Corrección tras la auditoría** (2026-11-27, rama `fix/h0-spec-publicar-cuerpo`; T-08-D22 a D27)

- **El cuerpo nombra las dependencias solo por id** (`T-02, T-03`). Con el título, renombrar una
  tarea reescribía el cuerpo de las que dependen de ella y borraba sus casillas marcadas.
- **La marca lleva el modo en claro** (`… hito=0 modo=didactico huella=… -->`): es el modo de la
  tarea si el issue lo lleva cuando se escribe la marca.
  - Sustituye a «las etiquetas de la vez anterior, deducidas de la huella» (arriba), que fallaba
    cuando el área vieja ya no estaba en ningún sitio.
  - Deja de valer el segundo «Sin corregir», porque en un choque la marca ya no reclama el modo.
  - La parte de etiquetas de la huella se queda (P1).
- **Prueba real**, con el código final y la CLI:

  | Ejecución | Resultado |
  | --- | --- |
  | `--seco` en menairos-prueba | 3 cuerpos que cambiar (T-02 a T-04) y 0 avisos |
  | 1.ª | 3 `PATCH` solo con `body`, 0 avisos, 14 s. T-01 no se toca: su marca no cambia |
  | 2.ª | **0** escrituras, 7 s |
  | `--seco` en `pdromer0/menairos` | 91 escrituras y 0 avisos; la salida legible, la de arriba |

  Las huellas del test de valor fijo pasan a ser estas: T-02 `…8322ddfaa2e11a4c…`, T-03
  `…c8747acd4eb1cfa4…` (con `modo=didactico`) y T-04 `…690b9f7ba2acfcc0…`. La de T-01 no cambia.
- **Tests:** 808 en el repo, 19 más que antes. Hay 12 versiones incorrectas, y todas hacen
  fallar algún test, también sobre el código final.
- **Revisión:**
  - **del plan, a la contra:** 15 hallazgos, cribados en una tabla;
  - **`/code-review` alto:** 9 hallazgos. Se corrigieron 2 (el cuerpo, formado en un solo sitio, y
    una ayuda de los tests) y se aclaró 2.4. Se aceptaron sin código las marcas viejas, que solo
    hay en menairos-prueba, y la reescritura única de los cuerpos con dependencias.
- **Pendiente:** cambiar el texto fijo del cuerpo (T-09) reescribe todos los cuerpos abiertos
  (`abiertas.md`; cerrado en T-09, que no cambia el cuerpo: T-09-D2).

### T-09 — Plantillas de documentos y sustitución `{{…}}`

*Hecha el 2026-11-27, en local (WSL2), con Claude Code (Opus 5.5, modo plan y después auto), a
partir del issue #17 y de un encargo del chat. Tarea no crítica: plan corto, sin revisión a la
contra. Pedro aprobó P1–P5 con la recomendación.*

**Qué se hizo**

- Las plantillas de 3.2 están en `src/menairos/plantillas/docs/`, dentro del paquete:
  - los documentos `producto.md`, `diseno.md`, `hitos.md`, `hito-N.md`, `abiertas.md`, `adr.md`,
    `anexo-tarea.md`, `revision-hito-N.md` e `inventario-mvp.md`;
  - los YAML `hito-N.tareas.yaml` y `decisiones-tarea.yaml`;
  - las copias exactas de la plantilla de PR y de las de issue (con `config.yml`).
- `menairos.templates` (`read`, `values`, `fill` y `render`) hace la sustitución `{{clave}}`, con
  las reglas de 3.2.
- `.github/ISSUE_TEMPLATE/tarea.md` tiene ahora las secciones del cuerpo de `spec publicar`. El
  cuerpo generado, `task_issues.py` y las huellas no cambian.
- `hito-0.md` 1.3, 3.2 y 3.3 y `diseno.md` 2.3 dicen dónde viven las plantillas. Se cierran dos
  puntos de `abiertas.md`.

**Decisiones del diff** (registro: `hito-0/decisiones/T-09.yaml`, de T-09-D1 a D8)

- D1, las plantillas dentro del paquete. D2, manda el cuerpo de `spec publicar`: la huella de
  T-09, calculada desde el YAML, es la de la marca del issue #17.
- D3, valores de `menairos.toml` y de una lista cerrada de claves de quien llama, textos o
  enteros. D4, un `{{` literal se escribe `\{{` (Handlebars). D5, en YAML, un texto va entre
  comillas dobles y se escapa.
- D6, encabezados sin número, `config.yml` y `diseno.md` alineado con 3.2. D7 (agente):
  `check-yaml` no mira `hito-N.tareas.yaml`, que no es YAML sin rellenar. D8 (agente, de la
  revisión): ni caracteres de control ni textos YAML fuera de comillas.

**Medidas**

- 16 plantillas: 11 documentos, la de PR, las 3 de issue y `config.yml`. `templates.py` tiene
  232 líneas; `test_plantillas.py`, 547 líneas con 156 tests, uno de ellos lento (el wheel).
- El esqueleto da exactamente E02, E10 y E12 (con el hito 0 y con el 3). Con el contenido mínimo
  (la tarea de ejemplo descomentada, una ✅ con su orden y un ADR de stack desde `adr.md`) pasa
  sin errores ni avisos.

**Versiones incorrectas**

Las ocho del plan fallan en su test:
1. un hueco desconocido que se deja tal cual;
2. `True` aceptado como número;
3. `if not value`, que rechaza el hito 0;
4. el YAML sin escapar;
5. la sustitución en bucle;
6. un `- ✅` dentro del comentario de «Validación funcional»: E10 lo cuenta, porque no salta los
   comentarios HTML;
7. un encabezado cambiado;
8. `## Datos` cambiado en `tarea.md`.

**Revisión**

- **`/code-review`:** 10 hallazgos. Se corrigieron 8:
  - el YAML con caracteres que no admite (`\x7f`, `\x9f`, sustitutos sueltos): ahora un valor con
    caracteres de control es un error;
  - un texto en un hueco YAML sin comillas (`hito: {{hito.numero}}` con `"1 # x"` cargaba 1):
    ahora solo admite enteros, y el comentario de `decisiones-tarea.yaml` ya no lleva un texto;
  - los caracteres invisibles de este anexo;
  - §3.3, que todavía ponía las plantillas de issue y de PR en `base`;
  - la exclusión de `check-yaml`, limitada a `hito-N.tareas.yaml`;
  - las referencias de T-06 y T-08 a puntos de `abiertas.md` ya cerrados;
  - el recuento de líneas, que ya no es cuadrático.

  No se corrigieron 2:
  - `_NOT_BLANK`, repetido de `schemas.py`, que no se toca en esta tarea;
  - que `markdown.parse` no salte los comentarios HTML, que va a Pendiente.

  Las correcciones suman menos de 100 líneas de `src/`, así que no hubo segunda revisión.
- Se repitió la lección de T-06: los escapes de U+FEFF y U+2028 acabaron escritos como los
  caracteres, en `templates.py`, en los tests y en este anexo. U+2028 es de la categoría Zl, que la
  búsqueda no miraba; ahora busca también Zl y Zp.

**Pendiente**

- T-15 (`spec nuevo`) decide dónde se escribe cada plantilla y qué valores pasa.
- **Para Pedro:** `spec validar` no salta los comentarios HTML. Si alguien deja comentado un
  `- ✅ …` en «Validación funcional», o un `###` en `abiertas.md`, E10 lo cuenta como comprobación
  y E11 como punto. Las plantillas evitan esas líneas en sus comentarios; arreglarlo en
  `markdown.parse` cambia E10 y E11, y queda para una tarea de `spec validar` (por ejemplo T-18).
- No se migran los documentos del propio Menairos a las plantillas (decisión del encargo).

### T-10 — Plantillas base y python-uv, manifiesto y composición

*Hecha el 2026-11-27, en local (WSL2), con Claude Code (Opus 5.5, modo plan y después auto), a
partir del issue #18 y de un encargo del chat. Tarea crítica: plan revisado a la contra por un
subagente (15 hallazgos, criba en el plan) y en el chat; Pedro aprobó P1–P8 con la recomendación
y añadió la prueba de faltas de la N3 de Menairos.*

**Qué se hizo**

- `base` y `python-uv` en `src/menairos/plantillas/stacks/`: `plantilla.toml` (validado por
  `esquemas/plantilla.schema.json`) y ficheros con el sufijo `.plantilla`.
- `menairos.stacks`: carga y ordena las plantillas (`requiere` y `stack.plantillas`), compone en
  memoria con cuatro reglas de fusión (`.gitignore`, pre-commit, CI con marcador y `AGENTS.md`),
  genera `.claude/settings.json` y `scripts/stack/plantillas.txt`, y da el `Contract`.
- Scripts del contrato: `n1.sh` reparte las rutas de tests por propiedad, `n2.sh` sella con la
  huella del árbol (índice temporal y `git write-tree`) y `n3.sh` ejecuta las partes de cada
  plantilla. Menairos los usa ya.
- E13 en `spec validar`. §3.3 reescrita; 1.3, 2.3, 2.5 y 5.5, `diseno.md` 2.3, 5 y 6,
  `AGENTS.md` y un punto nuevo en `abiertas.md`.

**Decisiones del diff** (registro: `hito-0/decisiones/T-10.yaml`, de T-10-D1 a D13)

- D1: Menairos adopta los scripts compuestos; la equivalencia admite dos diferencias. D2: la N3
  generada no valida la especificación. D3: el contrato sirve para varias tecnologías. D4: los
  ajustes, iguales en los tres modos en el H0.
- D5–D11: solo `base` es un error, gitleaks v8.30.1, CI fusionable, el sufijo, `{{paquete}}`, las
  rutas de tests y E13 por lista. D12 (agente): `if`/`then`/`else` en el esquema. D13 (agente):
  los mensajes de las comprobaciones.

**Medidas**

- Versiones (2026-11-27, PyPI, `git ls-remote` y `--version`): ruff 0.17.6, pyright 1.1.414,
  pytest 9.2.0, pytest-timeout 2.4.0, pre-commit 4.7.0, uv 0.13.10, pre-commit-hooks v6.0.0 y
  gitleaks v8.30.1 (la única nueva). Las acciones conservan los SHA de T-02.
- `stacks.py` tiene 767 líneas. Hay 154 tests nuevos (111 de composición y contrato, 41 de los
  scripts y 2 lentos); el del proyecto generado tarda unos 5 s con la caché de uv.
- Mensajes comprobados provocando cada falta en un proyecto generado:

  | Falta | Mensaje |
  | --- | --- |
  | Formato | `hook id: ruff-format` |
  | Tipos | `hook id: pyright` |
  | Clave `ghp_` inventada | `leaks found` (`github-pat`) |
  | Test que falla | `1 failed` |
- **La N3 nueva de Menairos no da un verde falso** (añadido de Pedro). Una falta de cada tipo en
  el repo, deshecha después, y en todas `scripts/n3.sh` salió con 1 y nombró el paso:

  | Falta | Paso que falló |
  | --- | --- |
  | Mal formato | `ruff format --check`, con el fichero |
  | Error de tipos | `pyright`, con la línea |
  | Test que falla | `pytest`, con el test |
  | Punto sin justificación | `spec` (E11) y `pytest`, por `test_el_propio_repo_valida` |

**Versiones incorrectas**

Las 22 del plan fallan en su test; un script aplica cada una, ejecuta su test y la deshace.
Entre ellas: la N1 que para en la primera parte, el `GIT_INDEX_FILE` solo en `git add`, el
marcador que queda, una línea más en un script de Menairos y un fichero oculto fuera del wheel.

**Revisión**

- **`/code-review` (alto):** 10 hallazgos. Se corrigieron 6:
  - un nombre propio en el `CLAUDE.md` de `base`;
  - las rutas relativas, que por un enlace simbólico salían del repo (reproducido, con test);
  - toda plantilla de lenguaje requiere `base`;
  - `plantillas.txt` sin una plantilla del stack es un error;
  - dos limpiezas.

  No se corrigieron 4: `git push *` permitido (decisión de T-02, y el ruleset es la primera
  barrera); bash 4 y el `realpath` de GNU (el entorno es WSL2 o Linux); `--frozen` sin `uv.lock`
  (el `uv sync` es de T-11); y `contract()` relee las plantillas en cada llamada (milisegundos).
  Menos de 100 líneas de `src/`, sin segunda revisión.

**Pendiente**

- T-11: escribir sin sobrescribir, con el bit de ejecución, y `uv sync` antes del primer commit.
  T-13: provocar las comprobaciones por `salta`. T-20: `Stop` lanza `scripts/n2.sh` y
  `PostToolUse` usa `Contract.format_command`. T-22: la orden de `tests_commands`.
- **Para Pedro:** los scripts necesitan bash 4 y el `realpath` de GNU: no van en un macOS de serie.

### T-11 — `menairos entorno`: capas local y repo

*Hecha el 2026-11-27, en local (WSL2), con Claude Code (Opus 5.5, modo plan y después auto), a
partir del issue #19 y de un encargo del chat. Tarea delicada, no crítica: plan corto, sin revisión
a la contra; Pedro aprobó P1–P6 con la recomendación.*

**Qué se hizo**

- `menairos.environment` (paquete: `core`, `local` y `repo`): pasos con los cuatro estados de 3.4,
  el informe por capas y el protocolo `System`, que los tests sustituyen por un doble.
- **Capa local**, que solo lee: ruta, herramientas y versiones de los manifiestos, sesión de `gh`,
  `codex` si algún revisor lo es y `.wslconfig`.
- **Capa repo**: la composición de T-10 sin sobrescribir nunca, `git init -b main`, `uv sync`,
  `pre-commit install` y el primer commit, sin push. Para en el primer paso que no queda en verde.
- `menairos entorno [local|repo] [--comprobar] [--json] [--raiz RUTA]`. §3.4 corregida y un punto
  nuevo en `abiertas.md` (bash 4 y el `realpath` de GNU).

**Decisiones del diff** (registro: `hito-0/decisiones/T-11.yaml`, de T-11-D1 a D10)

- D1: lo que prepara cada plantilla de lenguaje va en una tabla del código. D2: `pre-commit
  install`, en la capa repo. D3: el primer commit lleva todo (`git add -A`), y nunca con
  conflictos. D4: con `--comprobar`, lo que se haría es `manual`. D5: sin capa, repo solo tras una
  local en verde. D6: cualquier `/mnt/<letra>/`. D7: lo que interpreta el plan.
- D8 (agente): un paquete en vez de un módulo de 880 líneas. D9 (agente): el bit que falta se pone;
  un enlace en el camino es un conflicto; la identidad, con `git var`. D10 (agente): git con
  `LC_ALL=C` y la orden de `core.hooksPath` con `--show-origin`.

**Medidas**

- `environment` tiene 931 líneas en cuatro ficheros. Hay 90 tests nuevos (42 de local, 33 de repo
  y 15 de la CLI); git es el real en `tmp_path`, sin la configuración de la máquina.
- Comprobado con las herramientas: `uv sync --check` no escribe; con un `uv.lock` desfasado,
  `--check --locked` sale con 1 y `uv sync --locked` falla sin tocarlo (`uv lock --check` lo
  distingue). `pre-commit install` no instala con `core.hooksPath`, y su hook lleva la marca
  `# File generated by pre-commit`. `git var` sin identidad sale con 128.
- **Prueba real** (una vez, en esta máquina):

  | Orden | Resultado | Tiempo |
  | --- | --- | --- |
  | `entorno local` en Menairos | todo `ok`, también `.wslconfig` | 1,8 s |
  | `entorno repo` en un proyecto nuevo en `/tmp` | 5 pasos `hecho`: 17 ficheros, `uv.lock`, hook y un commit de 19 ficheros, sin remoto | 5,4 s |
  | `scripts/n3.sh` del proyecto nuevo | verde: formato, lint, tipos y tests | 2,9 s |
  | `entorno repo` otra vez | los 5 pasos, `ok` | 0,2 s |
  | `entorno --comprobar` en Menairos | 10 conflictos listados, nada escrito | — |

  El primer commit tardó poco porque gitleaks ya estaba compilado en la caché de pre-commit.

**Versiones incorrectas**

Las 18 del plan (la 13, en sus dos sentidos) fallan en su test; un script aplica cada una, ejecuta
su test y la deshace. Entre ellas: escribir sobre un fichero distinto, un `git init` con
`--comprobar`, versiones comparadas como texto, `3.140` por `3.14`, solo `/mnt/c`, un commit con
conflictos o con historia, un push, un enlace seguido y la barrera quitada.

**Revisión**

- **`/code-review` (alto):** 10 hallazgos. Se corrigieron 9:
  - la orden de `core.hooksPath` no quitaba un valor global;
  - un `--version` que falla daba `ok` sin versión mínima;
  - un fallo de `rev-parse` que no es «no es un repo» llevaba a `git init`;
  - `RealSystem` pasaba `GIT_DIR` y compañía;
  - `%USERPROFILE%` en la página de códigos OEM;
  - un `OSError` salía como traceback;
  - `python` sin uv era `error`;
  - la raíz del JSON no estaba resuelta;
  - el entorno de gh, en dos copias.

  No se corrigió uno: `stacks.resolve` corre tres veces (milisegundos).
- **Segunda revisión ligera** (unas 100 líneas de `src/`): con git en español, «not a git
  repository» no casaba y un proyecto nuevo no arrancaba. Se corrigió con `LC_ALL=C` en los git,
  junto con la orden exacta de `core.hooksPath` (`--show-origin`) y el aviso del bit. Tras las
  correcciones, la prueba real se repitió en una carpeta nueva y quedó igual de verde.

**Pendiente**

- T-12: las capas github y nube sobre los mismos pasos; el «repo existe en GitHub pero no en local,
  y al revés» de 3.7. T-14: `/preparar-entorno` lee `--json` y resuelve los conflictos con Pedro.
- Cuando llegue una segunda plantilla de lenguaje, la tabla de D1 pasa al manifiesto.

# Lecciones

Reglas aprendidas al construir Menairos, reutilizables entre tareas. El anexo de cada tarea cuenta
qué pasó; aquí queda la regla que sale de ahí. Cada lección indica la tarea de origen y las
tareas a las que afecta.

## GitHub y su API

- **Lo que se ajusta en la web se comprueba después por la API**, no se da por puesto (lección de
  un proyecto anterior; aplicada en T-01).
- **La API puede no coincidir con su documentación: se comprueba leyendo los campos de la
  respuesta, no el código HTTP.** Por ejemplo, `GET /repos/{o}/{r}/automated-security-fixes` con
  las actualizaciones desactivadas devuelve `200` con `{"enabled": false}`, no el `404`
  documentado. *Origen:* T-01. *Afecta a:* T-12 (`--comprobar`).
- **Antes de dar por imposible un paso manual, se busca su ruta en la API.** La aprobación de los
  PR de forks y CodeQL tienen API, aunque la especificación los tenía como pasos en la web.
  *Origen:* T-01 y T-02. *Afecta a:* T-12 y T-14.
- **Un ajuste que necesita contenido se activa cuando el contenido existe**: el check obligatorio
  `ci` se puede exigir antes de que corra, pero CodeQL necesita código en la rama por defecto y
  `default-setup` devuelve `languages: []` hasta que termina su primer análisis. *Origen:* T-01 y
  T-02.
- **Órdenes de `gh` que usan GraphQL**, como `gh pr edit`, fallan donde GraphQL falla (la nube, o
  una incidencia de GitHub): en la CLI, siempre `gh api` por REST (ADR 0016). *Origen:* T-02.
  *Afecta a:* T-07 y todas las órdenes que escriben en GitHub.
- **Reintentar en bucle una escritura que no es idempotente puede duplicarla** (crear un PR, un
  issue o un milestone): antes de reintentar, se comprueba si la primera llegó a hacerse.
  *Origen:* T-02. *Afecta a:* T-07, T-08 y T-25.
- **Ante errores raros de GitHub (502, errores internos), se mira su página de estado antes de
  depurar**, y lo que salga durante una incidencia no cuenta como comprobación. *Origen:* T-02.

## Comprobaciones

- **Una comprobación deliberada vale solo si el fallo cae dentro de lo que la herramienta
  revisa**: un error de tipos en un fichero fuera del `include` de pyright no hace fallar nada
  (lección de un proyecto anterior; repetida en T-02). *Afecta a:* T-13.
- **Un hook en verde no dice qué revisó**: los scripts de comprobación dicen siempre qué
  ejecutan. *Origen:* lección de un proyecto anterior; aplicada en T-02.

## Herramientas

- **Con pre-commit instalado, un commit en una rama sin `.pre-commit-config.yaml` falla.** Para
  una prueba puntual, `PRE_COMMIT_ALLOW_NO_CONFIG=1`. *Origen:* T-02.
- **La primera ejecución del hook de gitleaks compila gitleaks** con el Go que descarga pre-commit
  (unos minutos); las siguientes tardan segundos. *Origen:* T-02. *Afecta a:* T-10 y T-11 (aviso
  en la capa local).
- **Las versiones de las herramientas se fijan con herramientas** (`uv add`,
  `pre-commit autoupdate`, `gh api` o `git ls-remote` para los SHA), nunca de memoria. *Origen:*
  T-02.

## Forma de trabajar

- **Los nombres de los proyectos anteriores no entran en el repo**: se citan como «el método v2»
  o «un proyecto anterior». El patrón de búsqueda no se guarda en el repo, porque haría fallar el
  propio grep. *Origen:* T-01 y T-03.
- **En modo auto, Claude Code bloquea las acciones destructivas** (por ejemplo, `git reset --hard`)
  y pide autorización; es el comportamiento buscado. Las prohibiciones de
  `.claude/settings.json` son una segunda barrera; la primera es el ruleset. *Origen:* T-02.

## Plugins y Claude Code

- **La documentación de Claude Code puede contradecirse entre páginas**: cuando pasa, se prueba y
  se anota el resultado. *Origen:* T-04.
- **Una skill que imprime su origen (`${CLAUDE_PLUGIN_ROOT}`) distingue si se cargó como plugin o
  como copia en `.claude/skills/`**: en la copia, la variable sale sin sustituir. *Origen:* T-04.
- **En la nube, el `.claude/settings.json` del repo no instala plugins**: los instala el script de
  entorno. *Origen:* T-04.

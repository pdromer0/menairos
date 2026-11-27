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
- **`POST /markdown` no pone `id` a los encabezados**: para ver las anclas que GitHub calcula, se
  lee un fichero ya subido con la API de contenidos y `Accept: application/vnd.github.html+json`
  (vale con una rama, `?ref=`). *Origen:* T-06. *Afecta a:* T-09 y T-24.
- **`gh api --include` da el código HTTP, las cabeceras y el cuerpo también en un error**, por
  stdout (y sale con 1): el código se lee de la línea de estado, no del texto de stderr. La línea
  de estado acaba en LF y las cabeceras en CRLF. *Origen:* T-07. *Afecta a:* todo lo que use
  `menairos.github`.
- **Las URLs del `Link` de la paginación usan `repositories/{id}`**, no `repos/{dueño}/{repo}`: se
  siguen tal cual, sin rehacerlas, y un doble tiene que aceptar las dos formas. *Origen:* T-07.
  *Afecta a:* T-08, T-19.
- **`--input` y `-f` cambian el método por defecto de `gh api` a POST**: se pasa siempre
  `--method`. *Origen:* T-07.
- **Las dependencias entre tareas del hito solo se gestionan en el YAML (`depende_de`)**:
  `spec publicar` las sincroniza en cada ejecución, así que una relación «blocked by» que se añada
  a mano entre dos issues del hito se quita en la publicación siguiente. Las relaciones con otros
  issues no se tocan. *Origen:* T-08 (decisión de Pedro). *Afecta a:* T-19, T-22, T-25 y al
  trabajo de Pedro en la web.
- **Una dependencia «blocked by» se crea con el `id` del issue que bloquea, no con su número**, y
  la respuesta es el issue **bloqueado**:
  - un duplicado da 422 con solo un `message`, sin `errors`;
  - el listado incluye los bloqueantes cerrados.

  *Origen:* T-08. *Afecta a:* T-19 y T-23.
- **Los `id` de GitHub son globales**: para probar una ruta con un id que no exista se usa `0`,
  nunca un número pequeño inventado, que puede ser el de un issue real de otro repo. *Origen:* T-08
  (revisión del plan). *Afecta a:* toda verificación contra la API.
- **GitHub guarda el cuerpo de un issue tal como llega, también con CRLF**: quien busque en él una
  línea anclada al final (como la marca) pasa antes de CRLF a LF. *Origen:* T-08. *Afecta a:* T-19
  (`desfase`).
- **Lo que se lee al principio de una orden larga puede haber cambiado al escribir**: antes de un
  `PATCH` se vuelve a leer el issue, para no deshacer un `en-curso` o una edición hecha entretanto.
  *Origen:* T-08 (revisión del plan). *Afecta a:* T-23 y T-25.

## Comprobaciones

- **Una comprobación deliberada vale solo si el fallo cae dentro de lo que la herramienta
  revisa**: un error de tipos en un fichero fuera del `include` de pyright no hace fallar nada
  (lección de un proyecto anterior; repetida en T-02). *Afecta a:* T-13.
- **Para probar que una barrera impide lanzar un programa real sin lanzarlo**, la versión incorrecta
  que quita la barrera se ejecuta con un programa falso primero en el `PATH`. *Origen:* T-07
  (`gh`). *Afecta a:* T-13.
- **Un hook en verde no dice qué revisó**: los scripts de comprobación dicen siempre qué
  ejecutan. *Origen:* lección de un proyecto anterior; aplicada en T-02.
- **Los datos de un test tienen que tener la forma real**: el test del CRLF pasaba aunque el cuerpo
  no se normalizara, porque la marca era la última línea sin salto final; la web deja también un
  CRLF detrás. Lo destapó la versión incorrecta. *Origen:* T-08.
- **Para verificar en real una escritura que el deny de `.claude/settings.json` impide desde el
  shell** (un `DELETE`), se usa la propia orden de la CLI, que pasa por la lista de
  `menairos.github`, y no un script que esquive el deny. *Origen:* T-08 (P5).

## Contratos

- **Estricto ahora donde es barato**: relajar una regla de un esquema después no rompe ningún
  fichero; endurecerla sí, y es una versión mayor. Por eso un texto de solo espacios cuenta como
  vacío y `1.0` no vale como entero. *Origen:* T-05 (decisión de Pedro). *Afecta a:* T-06, T-21 y
  cualquier cambio de esquema.
- **JSON Schema 2020-12 acepta `1.0` como entero**: la comprobación estricta va en código, después
  del esquema. *Origen:* T-05.
- **El `if` de un `if/then` necesita el `required` de la clave que mira**: sin él, si la clave
  falta, la condición se cumple y el `then` se aplica igual. *Origen:* T-05.
- **Los patrones de JSON Schema se evalúan con `re` de Python, que no es ECMA-262**: `$` acepta un
  salto de línea final y `\d` admite cifras que no son ASCII. En los patrones, `[0-9]`; el salto
  final lo rechaza el código. *Origen:* T-05. *Afecta a:* T-06.
- **`yaml.safe_load` se queda con el último valor de una clave repetida, sin avisar**: los YAML de
  Menairos se leen con `load_document` de `menairos.schemas`, que lo convierte en un error.
  *Origen:* T-05. *Afecta a:* todo lo que lea YAML.
- **Las anclas de GitHub conservan el `\p{Word}` de Ruby** (letras, marcas, cifras decimales y
  `_`), además de `-` y los espacios: el `\w` de Python no sirve, porque quita las marcas
  combinantes y conserva `①` y `²`. Las anclas se calculan con `menairos.markdown`. *Origen:*
  T-06. *Afecta a:* T-09 y T-24.
- **Lo que la CLI necesita en tiempo de ejecución va dentro de `src/menairos/`**: `uv tool install`
  solo instala el paquete. Se comprueba mirando el wheel. *Origen:* T-05. *Afecta a:* T-09 y T-10
  (plantillas).

## Herramientas

- **Con pre-commit instalado, un commit en una rama sin `.pre-commit-config.yaml` falla.** Para
  una prueba puntual, `PRE_COMMIT_ALLOW_NO_CONFIG=1`. *Origen:* T-02.
- **La primera ejecución del hook de gitleaks compila gitleaks** con el Go que descarga pre-commit
  (unos minutos); las siguientes tardan segundos. *Origen:* T-02. *Afecta a:* T-10 y T-11 (aviso
  en la capa local).
- **Las versiones de las herramientas se fijan con herramientas** (`uv add`,
  `pre-commit autoupdate`, `gh api` o `git ls-remote` para los SHA), nunca de memoria. *Origen:*
  T-02.

- **Un escape como `"\ufeff"` puede acabar escrito como el carácter invisible**: antes de
  commitear código o tests con BOM, espacios especiales o marcas combinantes, se buscan los
  caracteres de las categorías `Cf`, `Mn` y `Zs` (salvo el espacio) y se dejan como escapes.
  *Origen:* T-06.

## Forma de trabajar

- **El plan de una tarea crítica se revisa a la contra antes de enseñarlo**, con un subagente de
  contexto limpio que lee el código y la especificación. En T-08 encontró fallos de verdad: escribir
  sobre una lectura vieja y una prueba que podía escribir fuera del repo de prueba. *Origen:* T-08.
  *Afecta a:* las tareas críticas hasta que exista `revisor-plan` (T-22).

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

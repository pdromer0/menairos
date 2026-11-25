# Menairos — producto

> **Estado:** v2 (2026-11-25), revisado por Pedro. Aceptados: el reparto de los casos de uso por
> hito, los criterios de éxito del hito 0, la convención de idiomas y los entornos de ejecución
> (sesiones en la nube de Claude Code incluidas).
> El qué y el porqué. El cómo va en `diseno.md`. Las decisiones de fondo están en `decisiones/`
> (ADRs); su índice relaciona cada punto del diseño del método con su ADR.

## 1. Visión

Menairos es un método estándar, distribuido como plugin de Claude Code, para llevar una idea o
un MVP de demo hasta un producto con un equipo de agentes. Pedro define el producto y valida el
resultado; los agentes especifican con él, preparan el entorno, implementan, revisan e integran.
En modo automático, un hito completo se construye sin intervención humana salvo decisiones o
problemas críticos, y al final Pedro revisa las decisiones tomadas y el producto funcionando.

## 2. Problema

Hoy, con el método v2:

- **Pedro está en todas las puertas:** lanza cada tarea, aprueba cada plan, revisa cada PR,
  fusiona, sincroniza y mueve el tablero. Su tiempo es el cuello de botella, no la capacidad de
  los agentes.
- **El método se copia a mano entre proyectos** (`portabilidad.md`, `arranque.md`): cada proyecto
  nuevo cuesta un hito 0 de configuración, y las mejoras de un proyecto no llegan a los demás.
- **Las especificaciones dependen de una conversación larga con el chat**, sin un formato que un
  script pueda comprobar ni publicar.
- **El consumo de cuota se dispara** con sesiones largas y repetición de trabajo (el 93 % del
  consumo de un día de trabajo con el método v2 venía de sesiones largas).
- **Las decisiones que toman los agentes** quedan repartidas por PRs y anexos: no hay un sitio
  donde revisarlas juntas.

## 3. Usuarios

| Usuario | Papel |
| --- | --- |
| **Pedro** (único usuario humano) | Dueño de producto: define requisitos, stack y coste; responde escalados; valida funcionalmente cada hito; decide la autonomía |
| **Agentes** (Claude Code, Codex) | Ejecutores: especifican con Pedro, revisan, implementan e integran siguiendo el método |

## 4. Casos de uso

| Id | Caso de uso | Actor | Resultado | Hito |
| --- | --- | --- | --- | --- |
| CU-01 | Especificar un producto desde una idea (`/crear-spec`, lluvia de ideas) | Pedro + agente | `producto.md`, `diseno.md`, `hitos.md`, ADRs, especificación y tareas del primer hito | H0 |
| CU-02 | Especificar un producto desde un MVP (`/crear-spec`, modo MVP) | Pedro + agente | Inventario de lo que hay + los mismos documentos, con cada herencia decidida | H0 |
| CU-03 | Validar y publicar la especificación (`/validar-spec`) | Agente revisor + Pedro (OK) | Informe de bloqueantes, mejoras y preguntas; milestone e issues publicados | H0 |
| CU-04 | Preparar el entorno de un proyecto nuevo (`/preparar-entorno`) | Agente + Pedro (pasos manuales) | Repo, plantilla del stack, CI, ruleset y entornos (local, nube de Claude Code y Actions) listos; `--comprobar` en verde | H0 |
| CU-05 | Implementar una tarea en modo manual (`/implementar`) | Agente + Pedro (puertas) | PR con plan aprobado, N1–N3, anexo y fichero de decisiones. Por defecto, en una **sesión en la nube de Claude Code**, que Pedro lanza y sigue desde la web o el móvil; en local, si la tarea necesita el portátil | H0 |
| CU-06 | Implementar una tarea en modo didáctico | Agente + Pedro | Lo mismo que CU-05 (también en la nube por defecto), con conceptos explicados antes y sección de conceptos en el PR | H0 |
| CU-07 | Construir un hito en modo automático (`/implementar --auto`) | Orquestador + agentes | Tareas implementadas, revisadas y fusionadas sin intervención salvo escalados; las sesiones corren en GitHub Actions | H1 |
| CU-08 | Responder a un escalado (`necesita-pedro`) | Pedro | Decisión registrada como «decidido por Pedro» y tarea relanzada | H1 |
| CU-09 | Pausar y reanudar el modo automático (`MENAIROS_PAUSA`) | Pedro | El orquestador se detiene y retoma donde estaba | H1 |
| CU-10 | Cerrar un hito (`/cerrar-hito`, y `--aprobar` tras la revisión) | Agente + Pedro | Informe del hito, correcciones encauzadas, ADRs, etiqueta y Release | H0 (básico) / H1 (completo) |
| CU-11 | Crear la plantilla de un stack nuevo (`/preparar-entorno --plantilla-nueva`) | Agente + Pedro | Plantilla que cumple el contrato, con comprobaciones deliberadas, propuesta al repo de Menairos | Posterior |
| CU-12 | Actualizar Menairos en un proyecto (`/actualizar-menairos`) | Agente + Pedro | PR con las migraciones de la versión nueva | Posterior |
| CU-13 | Especificar el siguiente hito (`/crear-spec --siguiente`) | Pedro + agente | Especificación y tareas del hito N+1, con las lecciones del cierre como entrada | H0 |

**Reparto por hito** (aceptado):

- **H0, el núcleo en modo manual:** CU-01 a CU-06, CU-10 básico (informe y cierre sin las partes
  del modo automático) y CU-13. Con H0 terminado, Menairos ya sustituye al método v2 en un
  proyecto nuevo.
- **H1, el modo automático:** CU-07 a CU-09 y CU-10 completo (decisiones marcadas, métricas de
  consumo, guardarraíles, ajuste de autonomía).
- **Posterior:** CU-11 (hasta que haga falta un stack sin plantilla) y CU-12 (hasta que exista una
  segunda versión que migrar).

## 5. Entornos de ejecución

| Entorno | Uso por defecto |
| --- | --- |
| **Sesiones en la nube de Claude Code** (claude.ai/code) | Modos manual y didáctico: Pedro lanza `/implementar N` desde la web o el móvil y el portátil queda libre |
| **GitHub Actions** | Modo automático: las sesiones las lanza el orquestador |
| **Local (WSL2)** | Solo las tareas que necesitan el portátil: Docker, ficheros locales, ver la app en el navegador |

- El entorno por defecto de cada modo está en `menairos.toml` (`[entornos]`); es el de por
  defecto, no una restricción: en los modos manual y didáctico se puede trabajar en local o en la
  nube. La tarea solo declara si necesita el portátil (`donde: local | cualquiera`), y solo
  `donde: local` obliga a trabajar en local.
- **Alternativa configurable** para el modo automático: las tareas programadas en la nube de
  Claude Code (antes «routines»), cuando salgan de la vista previa.
- Todo funciona igual en los tres entornos: GitHub siempre por REST, la rama siempre la del
  issue, el script de entorno de la nube lo genera `/preparar-entorno`, y nada depende del
  tablero.

## 6. Alcance

**Incluye:** el plugin de Claude Code (comandos, subagentes, hooks), los scripts deterministas,
las plantillas de documentos, la plantilla de Python + uv, los workflows de GitHub Actions, el
script de entorno de las sesiones en la nube, el formato de `menairos.toml` y la compatibilidad
con Codex a través de `AGENTS.md`.

**Fuera de alcance (por ahora):**

- equipos de varias personas;
- proyectos fuera de GitHub;
- despliegue a producción;
- plantillas de otros stacks (llegan con CU-11 cuando un proyecto las necesite);
- la migración de los proyectos que usan el método v2 (siguen con él).

## 7. Restricciones

- **Suscripciones:** Claude Max (uso principal) y Codex Pro, sin API keys de pago por uso.
- **GitHub:** cuenta personal; repos **públicos por defecto** (los rulesets en repos privados
  requieren GitHub Pro).
- **Entorno:** Windows con WSL2 en local; sesiones en la nube de Claude Code; GitHub Actions.
- **Compatibilidad con la nube:** nada de GraphQL (el proxy de la nube daba 403 con el método
  v2); las operaciones que la nube no permita (etiquetas y Releases, por verificar) tienen su
  alternativa.
- **Nada personal en los repos:** datos sintéticos; configuración real y secretos, fuera.
- **Idiomas:** documentación, especificaciones y commits en español; código en inglés (como en el
  método v2).
- **Coste de cuota:** el modo automático no debe impedir el uso interactivo de Claude de Pedro.

## 8. Criterios de éxito

**Del hito 0 (Menairos sustituye al método v2):**

- En un proyecto de prueba, de una idea a los issues publicados solo con conversación y el OK de
  Pedro (`/crear-spec` + `/validar-spec`).
- `/preparar-entorno` deja un proyecto nuevo listo con una lista de pasos manuales de Pedro de
  como mucho 15 minutos, y `--comprobar` en verde.
- Una tarea completa en modo manual con `/implementar`, de punta a punta, con el mismo nivel de
  calidad que una tarea del método v2 (plan de 8 apartados, N1–N3, anexo), **en una sesión en la
  nube de Claude Code** y también en local.

**Del hito 1 y del piloto (Menairos en modo automático):** los criterios del piloto
(`hitos.md`, «Después: el piloto»): hito completado en automático, ≤ 3 escalados justificados,
sin bloqueantes funcionales o corregidos en el N.1, ≥ 80 % de decisiones marcadas aceptadas,
tiempo de Pedro medido y comparado con un hito manual del método v2, dentro de la cuota de Max, y
pocas falsas alarmas de los guardarraíles.

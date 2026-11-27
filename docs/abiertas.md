# Menairos — preguntas abiertas y supuestos

> **Estado:** v1 (2026-11-25); añadida la licencia al preparar T-01.
> Formato (lo comprueba `menairos spec validar`, E11): cada punto abierto es un encabezado `###` y
> lleva una línea **Justificación:** que dice por qué sigue abierto y dónde se cierra. Cuando un
> punto se resuelve, se borra de aquí y su resultado va al anexo de la tarea y, si es una decisión,
> a un ADR.

## Verificaciones del hito 0

### ¿Se instala el plugin en `claude-code-action`?

**Justificación:** igual que la anterior, pero en GitHub Actions; necesita un workflow mínimo. Se
cierra en **T-26**. Si no, el plan B de `diseno.md` 2.1 (probado en T-04).

### ¿Sirve el token OAuth de Max para sesiones largas en `claude-code-action`?

**Justificación:** el modo automático del H1 depende de ello y no hay forma de saberlo sin una
sesión de 20 a 30 minutos de verdad. Se cierra en **T-26**. Si no sirve, el H1 usa las tareas
programadas de Claude Code o la ejecución en local (`diseno.md` §8).

### ¿Expone `claude-code-action` el consumo de cada sesión?

**Justificación:** los presupuestos de tokens del punto 17 dependen de poder leerlo. Se cierra en
**T-26**. Si no, los presupuestos se quedan en sesiones y tiempo.

### ¿Puede la revisión de Codex funcionar como check bloqueante?

**Justificación:** la revisión de Codex en GitHub se publica como comentario, no como check; hay
que probar si un workflow puede convertirla. Se cierra en **T-26**. Mientras tanto, el revisor
bloqueante es Claude y Codex es segunda opinión (punto 14).

### ¿Se pueden crear etiquetas y Releases con el token de una GitHub App?

**Justificación:** con el método v2, la nube daba 403 al crear Releases; con el token de la App puede ser
distinto. Se cierra en **T-26**. Si no, `menairos cierre --aprobar` deja la orden para lanzarla en
local (6.3).

### ¿Qué destinos de red necesita el job del agente?

**Justificación:** la lista de destinos permitidos contra la exfiltración (punto 18) solo se puede
hacer observando un job real. Se cierra en **T-26**, con una herramienta de control de salida en
modo solo registro.

### ¿Qué versión de `gh` hay en las sesiones en la nube?

**Justificación:** el envoltorio de T-07 solo usa opciones de `gh api` que existen desde gh 1.0.0
(`--method`, `--include`, `--input` y `--header`, comprobado en el código fuente de `gh`), y en
WSL2 (2.103.3) y Actions (2.105.0) está verificado; en la nube no se pudo mirar desde la sesión
local. Se cierra cuando Pedro lance `gh --version` en una sesión en la nube, o en **T-22**, con la
primera tarea hecha allí.

### ¿Qué opciones de `codex exec` dan solo lectura y salida a fichero?

**Justificación:** el revisor Codex de `/validar-spec` depende de ellas y no se dan por supuestas
de memoria. Se cierra en **T-18**. Si no hay una forma limpia, `revisores.spec` usa Claude por
defecto.

### ¿Funciona `/implementar` de punta a punta en una sesión en la nube?

**Justificación:** es el entorno por defecto de los modos manual y didáctico (punto 13) y combina
varias piezas (REST, rama del issue, script de entorno, N3 dentro del tiempo máximo). Se cierra en
**T-22**, con la primera tarea hecha en la nube.

## Repo de Menairos

### ¿Qué licencia lleva Menairos?

**Justificación:** el repo es público desde T-01, pero sin licencia nadie puede reutilizar ni
adaptar el plugin. Pedro lo decide antes de publicar `v3.0.0` (T-28); opciones valoradas: MIT y
Apache-2.0, con el aviso de copyright a nombre de `pdromer0` (nada personal). El fichero `LICENSE`
entra por PR, como cualquier otro cambio.

### ¿Dónde viven las plantillas para que viajen con la CLI?

**Justificación:** la CLI se instala con `uv tool install`, que solo empaqueta `src/menairos/`, así
que una carpeta `plantillas/` en la raíz (`hito-0.md` 1.3 y `diseno.md` 2.3) no llegaría a la CLI
instalada. A los esquemas les pasaba lo mismo, y en T-05 se movieron a `src/menairos/esquemas/`
(decisión de Pedro, 2026-11-27). Se decide en **T-09**, la primera tarea que crea plantillas.

### ¿Cómo se unifican la plantilla de issue «Tarea» y el cuerpo que genera `spec publicar`?

**Justificación:** desde T-08, `menairos spec publicar` genera el cuerpo de los issues de tarea
(resumen, especificación, criterios, datos y la marca; `hito-0.md` 2.4), y
`.github/ISSUE_TEMPLATE/tarea.md` (Objetivo, Alcance, Criterios de aceptación, Dependencias) no
cambió, así que hoy no coinciden. Se cierra en **T-09**, que crea las plantillas de documentos y de
issue (3.2) y las unifica.

### ¿Qué versión lleva el plugin durante el desarrollo?

**Justificación:** con `version` fijada en `plugin.json`, un proyecto se queda en esa versión
hasta que cambie, así que durante `3.0.0.dev0` los cambios del plugin no llegan solos. Se decide
en **T-22**, cuando el plugin empiece a cambiar de verdad.

### ¿Sirven los plugins de la cuenta de claude.ai para distribuir Menairos?

**Justificación:** en T-04 se vio que los plugins sincronizados desde claude.ai llegan a las
sesiones en la nube. Sería una vía sin script de entorno, pero con una sola versión para todos los
proyectos y subida a mano. No hace falta mientras funcione el script de entorno; se revisa al
cerrar el H0 (T-28).

### ¿Respeta `uv tool install` el `uv.lock`?

**Justificación:** las dependencias del paquete (jsonschema y PyYAML) solo tienen cota inferior en
`pyproject.toml`. Si `uv tool install` no usa las versiones de `uv.lock`, una versión mayor nueva
de cualquiera de ellas podría romper la CLI instalada; en ese caso, se ponen cotas superiores a
jsonschema y PyYAML. Se verifica en **T-22**, cuando el plugin empiece a usar la CLI instalada.

## Producto

### ¿Cuál es el producto piloto?

**Justificación:** Pedro lo elegirá más adelante; se necesita antes del paso 3 de la secuencia del
punto 20 (piloto, hito 0), es decir, después de los hitos 0 y 1 de Menairos. Debe cumplir las
características del punto 20: útil para Pedro, pequeño, Python + uv, sin Docker en su hito 1, sin
datos personales y con algo de criterio de producto.

## Supuestos

Lo que se da por cierto para trabajar y se revisará si deja de serlo:

- Las suscripciones siguen siendo Claude Max y Codex Pro, sin API keys de pago por uso.
- Los repos de Menairos y del piloto son públicos (GitHub Free no aplica rulesets a los privados).
- El portátil de trabajo sigue siendo Windows con WSL2.
- Las funciones en vista previa (tareas programadas de Claude Code, Agent Teams) no son la opción
  por defecto de nada.

# Menairos — preguntas abiertas y supuestos

> **Estado:** v1 (2026-11-25); añadida la licencia al preparar T-01.
> Formato (lo comprueba `menairos spec validar`, E11): cada punto abierto es un encabezado `###` y
> lleva una línea **Justificación:** que dice por qué sigue abierto y dónde se cierra. Cuando un
> punto se resuelve, se borra de aquí y su resultado va al anexo de la tarea y, si es una decisión,
> a un ADR.

## Verificaciones del hito 0

### ¿Se instala solo el plugin en una sesión en la nube de Claude Code?

**Justificación:** depende del comportamiento real de las sesiones en la nube con un marketplace
declarado en el `.claude/settings.json` del proyecto; solo se sabe probándolo. Se cierra en
**T-04** (V-plugin). Si no se instala solo, plan B de `diseno.md` 2.1: copiar el plugin a
`.claude/` del proyecto.

### ¿Se instala el plugin en `claude-code-action`?

**Justificación:** igual que la anterior, pero en GitHub Actions; necesita un workflow mínimo. Se
cierra en **T-26**. Si no, el mismo plan B.

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

### ¿Cuál es la ruta REST para crear y quitar dependencias «blocked by»?

**Justificación:** el método v2 solo leía las dependencias por REST; la escritura no está comprobada. Se
cierra en **T-08**, en la documentación de GitHub y contra el repo de prueba.

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

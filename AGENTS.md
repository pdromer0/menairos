# AGENTS.md

Instrucciones para cualquier agente de IA que trabaje en este repositorio.

## Qué es Menairos

Menairos es un método de desarrollo con agentes de IA, distribuido como plugin de
Claude Code. Este repositorio contiene el paquete Python `menairos`, su CLI y la
documentación del método.

## Flujo de trabajo de una tarea

Mientras no exista `/implementar`, cada tarea sigue estos pasos:

1. Issue de la tarea (desde T-09; hasta entonces, el encargo del chat: ver §0 de `docs/specs/hito-0.md`).
2. Plan con 8 apartados, aprobado por Pedro antes de tocar nada:
   1. Contexto.
   2. Lo que el plan interpreta.
   3. Diferencias con las notas.
   4. Valores a mano, con su cálculo ejecutado.
   5. Casos límite.
   6. Versiones incorrectas.
   7. Comprobaciones.
   8. Cuándo parar.
3. Rama de la tarea.
4. Commits pequeños, cada uno comprobado con `scripts/n1.sh`.
5. Una sola `scripts/n3.sh` antes de abrir el PR.
6. PR con la plantilla de `.github/pull_request_template.md`.
7. Pedro revisa y fusiona (por squash).

## Órdenes

```bash
uv sync                                  # instala dependencias
scripts/n1.sh [rutas de tests]           # comprobación rápida
scripts/n3.sh                            # comprobación completa
uv run menairos --version                # humo de la CLI
uv run pre-commit run --all-files        # todos los hooks
```

## Idiomas

- En español: documentación, commits, mensajes de PR y tests.
- En inglés: código, nombres y docstrings.
- En español: textos que la CLI muestra al usuario.

## Git

- Ramas con prefijo `feat/`, `fix/`, `docs/`, `refactor/`, `test/`, `chore/` o `ci/`.
- Commits convencionales en español: `feat:`, `fix:`, `docs:`, `chore:`, `ci:`,
  `test:`, `refactor:`.
- Nunca `git push` a `main` ni push forzado.
- Nunca `--no-verify`.
- Nunca fusionar un PR: lo hace Pedro.
- Nunca borrar nada por la API.

## Reglas de contenido

- Nada personal en el repositorio: datos sintéticos en los tests y ningún secreto.
- Las referencias a otros proyectos, siempre genéricas, sin nombres propios.

## Dónde está el resto

- `docs/producto.md`, `docs/diseno.md` y `docs/hitos.md`: producto, diseño e hitos.
- `docs/specs/`: especificación y tareas del hito en curso, con su anexo.
- `docs/decisiones/`: ADRs, con su índice.
- `docs/proceso/lecciones.md`: reglas aprendidas.
- `menairos.toml`: configuración del método para este proyecto.

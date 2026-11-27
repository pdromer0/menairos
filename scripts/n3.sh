#!/usr/bin/env bash
# N3: comprobación completa (formato, lint, tipos, todos los tests, incluidos los slow, y la
# especificación del propio repo con menairos spec validar).
# Uso: scripts/n3.sh
set -uo pipefail

# Raíz del repositorio, para que funcione desde cualquier directorio.
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 1

resumen=()
fallo=0

# Ejecuta un paso: anuncia la orden, la corre y anota OK o FALLO.
paso() {
    local orden="$*"
    echo "N3 · ${orden}"
    if "$@"; then
        echo "OK"
        resumen+=("OK     ${orden}")
    else
        echo "FALLO"
        resumen+=("FALLO  ${orden}")
        fallo=1
    fi
    echo
}

paso uv run --frozen ruff format --check .
paso uv run --frozen ruff check .
paso uv run --frozen pyright
paso uv run --frozen pytest
paso uv run --frozen menairos spec validar

echo "Resumen N3:"
printf '  %s\n' "${resumen[@]}"

# Siempre 1 ante cualquier fallo, no el código de la herramienta.
if [ "$fallo" -ne 0 ]; then
    exit 1
fi
exit 0

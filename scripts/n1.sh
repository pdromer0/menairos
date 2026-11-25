#!/usr/bin/env bash
# N1: comprobación rápida (formato, lint, tipos y tests no lentos).
# Uso: scripts/n1.sh [rutas de tests…]   (por defecto: tests)
set -uo pipefail

# Raíz del repositorio, para que funcione desde cualquier directorio.
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 1

# Rutas de tests: las dadas como argumentos o "tests" por defecto.
if [ "$#" -eq 0 ]; then
    rutas=(tests)
else
    rutas=("$@")
fi

resumen=()
fallo=0

# Ejecuta un paso: anuncia la orden, la corre y anota OK o FALLO.
paso() {
    local orden="$*"
    echo "N1 · ${orden}"
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
paso uv run --frozen pytest -m "not slow" "${rutas[@]}"

echo "Resumen N1:"
printf '  %s\n' "${resumen[@]}"

# Siempre 1 ante cualquier fallo, no el código de la herramienta.
if [ "$fallo" -ne 0 ]; then
    exit 1
fi
exit 0

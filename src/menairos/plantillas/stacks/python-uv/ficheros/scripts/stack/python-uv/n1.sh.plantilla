#!/usr/bin/env bash
# N1 de python-uv: formato, lint, tipos y tests no lentos. La lanza scripts/n1.sh.
# Uso: scripts/stack/python-uv/n1.sh [--sin-tests | rutas de tests…]   (por defecto: tests)
set -uo pipefail

# Raíz del repositorio, para que funcione desde cualquier directorio.
cd "$(dirname "${BASH_SOURCE[0]}")/../../.." || exit 1

# Rutas de tests: las dadas como argumentos o "tests" por defecto; --sin-tests no ejecuta ninguno.
tests=1
if [ "$#" -eq 1 ] && [ "$1" = "--sin-tests" ]; then
    tests=0
    set --
fi
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
if [ "$tests" -eq 1 ]; then
    paso uv run --frozen pytest -m "not slow" "${rutas[@]}"
else
    echo "N1 · sin tests: ninguna de las rutas dadas es de python-uv"
    echo
    resumen+=("--     pytest (ninguna ruta de python-uv)")
fi

echo "Resumen N1 (python-uv):"
printf '  %s\n' "${resumen[@]}"

# Siempre 1 ante cualquier fallo, no el código de la herramienta.
if [ "$fallo" -ne 0 ]; then
    exit 1
fi
exit 0

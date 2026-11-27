#!/usr/bin/env bash
# N3: comprobación completa de cada plantilla de lenguaje del stack (formato comprobado, lint,
# tipos y todos los tests, incluidos los slow), con su parte scripts/stack/<plantilla>/n3.sh.
# Uso: scripts/n3.sh
# Sale con 0 si todo pasa y con 1 si algo falla.
set -uo pipefail

# Raíz del repositorio, para que funcione desde cualquier directorio.
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 1
lista="scripts/stack/plantillas.txt"

# Las plantillas de lenguaje, en su orden.
plantillas=()
if [ ! -r "$lista" ]; then
    echo "N3 · no se puede leer ${lista}: lo genera menairos con las plantillas de stack"
    exit 1
fi
while read -r plantilla _ || [ -n "${plantilla:-}" ]; do
    if [ -z "${plantilla:-}" ] || [[ $plantilla == \#* ]]; then
        continue
    fi
    plantillas+=("$plantilla")
done <"$lista"
if [ "${#plantillas[@]}" -eq 0 ]; then
    echo "N3 · ${lista} no tiene ninguna plantilla de lenguaje"
    exit 1
fi

resumen=()
fallo=0

# Ejecuta un paso: lo anuncia, lo corre y anota OK o FALLO.
paso() {
    local nombre=$1
    shift
    echo "N3 · ${nombre} · $*"
    if "$@"; then
        echo "OK"
        resumen+=("OK     ${nombre}")
    else
        echo "FALLO"
        resumen+=("FALLO  ${nombre}")
        fallo=1
    fi
    echo
}

for plantilla in "${plantillas[@]}"; do
    paso "$plantilla" "scripts/stack/${plantilla}/n3.sh"
done
# En Menairos, la N3 valida también la especificación del propio repo.
paso spec uv run --frozen menairos spec validar

echo "Resumen N3:"
printf '  %s\n' "${resumen[@]}"

# Siempre 1 ante cualquier fallo, no el código de la parte.
if [ "$fallo" -ne 0 ]; then
    exit 1
fi
exit 0

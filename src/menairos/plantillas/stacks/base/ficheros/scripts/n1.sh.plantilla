#!/usr/bin/env bash
# N1: comprobación rápida de cada plantilla de lenguaje del stack (formato, lint, tipos y tests
# no lentos), con su parte scripts/stack/<plantilla>/n1.sh.
# Uso: scripts/n1.sh [rutas de tests…]   (sin rutas: todos los tests rápidos)
# Cada ruta va a la plantilla que la tiene por suya, según scripts/stack/plantillas.txt: primero
# por su extensión y después por su carpeta. Una plantilla sin rutas suyas se comprueba sin
# tests (--sin-tests). Sale con 0 si todo pasa y con 1 si algo falla.
set -uo pipefail

raiz="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)" || exit 1
lista="scripts/stack/plantillas.txt"

# Las rutas, relativas a la raíz del repo; se calculan antes de cambiar de carpeta.
relativas=()
for ruta in "$@"; do
    relativa="$(realpath -s -m --relative-to="$raiz" -- "$ruta")" || exit 1
    if [[ $relativa == ".." || $relativa == ../* ]]; then
        echo "N1 · la ruta «${ruta}» está fuera del repo"
        exit 1
    fi
    relativas+=("$relativa")
done
cd "$raiz" || exit 1

# Las plantillas de lenguaje, en su orden, y lo que es de cada una.
plantillas=()
declare -A propias
if [ ! -r "$lista" ]; then
    echo "N1 · no se puede leer ${lista}: lo genera menairos con las plantillas de stack"
    exit 1
fi
while read -r plantilla resto || [ -n "${plantilla:-}" ]; do
    if [ -z "${plantilla:-}" ] || [[ $plantilla == \#* ]]; then
        continue
    fi
    plantillas+=("$plantilla")
    propias[$plantilla]="${resto:-}"
done <"$lista"
if [ "${#plantillas[@]}" -eq 0 ]; then
    echo "N1 · ${lista} no tiene ninguna plantilla de lenguaje"
    exit 1
fi

# La plantilla dueña de una ruta: la de su extensión y, si ninguna, la de su carpeta.
duena() {
    local ruta=$1 nombre sin extension plantilla patron
    local -a patrones
    nombre=${ruta##*/}
    sin=${nombre#"${nombre%%[!.]*}"}
    extension=""
    if [[ $sin == *.* && $sin != *. ]]; then
        extension=".${sin##*.}"
    fi
    if [ -n "$extension" ]; then
        for plantilla in "${plantillas[@]}"; do
            read -ra patrones <<<"${propias[$plantilla]}"
            for patron in "${patrones[@]}"; do
                if [[ $patron != */ && $patron == "$extension" ]]; then
                    echo "$plantilla"
                    return 0
                fi
            done
        done
    fi
    for plantilla in "${plantillas[@]}"; do
        read -ra patrones <<<"${propias[$plantilla]}"
        for patron in "${patrones[@]}"; do
            if [[ $patron == */ && "${ruta}/" == "$patron"* ]]; then
                echo "$plantilla"
                return 0
            fi
        done
    done
    return 1
}

duenas=()
for ruta in "${relativas[@]}"; do
    if ! propietaria="$(duena "$ruta")"; then
        echo "N1 · la ruta «${ruta}» no es de ninguna plantilla (ver ${lista})"
        exit 1
    fi
    duenas+=("$propietaria")
done

resumen=()
fallo=0

# Ejecuta la parte de una plantilla: la anuncia, la corre y anota OK o FALLO.
paso() {
    local plantilla=$1
    shift
    echo "N1 · ${plantilla} · $*"
    if "$@"; then
        echo "OK"
        resumen+=("OK     ${plantilla}")
    else
        echo "FALLO"
        resumen+=("FALLO  ${plantilla}")
        fallo=1
    fi
    echo
}

for plantilla in "${plantillas[@]}"; do
    argumentos=()
    if [ "${#relativas[@]}" -gt 0 ]; then
        for i in "${!relativas[@]}"; do
            if [ "${duenas[$i]}" = "$plantilla" ]; then
                argumentos+=("${relativas[$i]}")
            fi
        done
        if [ "${#argumentos[@]}" -eq 0 ]; then
            argumentos=(--sin-tests)
        fi
    fi
    paso "$plantilla" "scripts/stack/${plantilla}/n1.sh" "${argumentos[@]}"
done

echo "Resumen N1:"
printf '  %s\n' "${resumen[@]}"

# Siempre 1 ante cualquier fallo, no el código de la parte.
if [ "$fallo" -ne 0 ]; then
    exit 1
fi
exit 0

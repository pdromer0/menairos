#!/usr/bin/env bash
# N2: la N1 con sello. Solo ejecuta scripts/n1.sh si el árbol de trabajo cambió desde el último
# verde. La huella cuenta lo confirmado, lo modificado y lo nuevo, y no lo que ignora git.
# Uso: scripts/n2.sh   (al final de cada turno, desde el hook Stop)
# Sale con 0 si no hay cambios o la N1 pasa, y con 1 si la N1 falla o no hay un repo git.
set -uo pipefail

# Raíz del repositorio, para que funcione desde cualquier directorio.
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 1
sello=".cache/menairos/n2.sello"

# Huella del árbol: el árbol de git de un índice temporal con todo lo que no está ignorado.
# El índice temporal solo existe dentro de la subshell: la N1 no lo hereda.
huella() {
    (
        set -e
        temporal="$(mktemp -d)"
        trap 'rm -rf "$temporal"' EXIT
        indice="$(git rev-parse --git-path index)"
        if [ -f "$indice" ]; then
            cp "$indice" "${temporal}/index"
        fi
        export GIT_INDEX_FILE="${temporal}/index"
        git add -A
        git write-tree
    )
}

if ! actual="$(huella)"; then
    echo "N2 · no se puede calcular la huella del árbol: hace falta un repo git"
    exit 1
fi
if [ -f "$sello" ] && [ "$(cat "$sello")" = "$actual" ]; then
    echo "N2 · sin cambios desde el último verde (huella ${actual}): no se ejecuta nada"
    exit 0
fi

echo "N2 · hay cambios desde el último verde: se ejecuta scripts/n1.sh"
echo
if scripts/n1.sh; then
    mkdir -p "$(dirname "$sello")"
    printf '%s\n' "$actual" >"$sello"
    echo "N2 · verde: sello guardado (huella ${actual})"
    exit 0
fi
echo "N2 · rojo: no se guarda el sello"
exit 1

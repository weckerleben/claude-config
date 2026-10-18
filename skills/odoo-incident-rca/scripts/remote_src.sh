#!/usr/bin/env bash
# Leer el source de Odoo directamente del servidor, sin checkout local.
#
# Odoo.sh despliega los tres árboles con rutas fijas, iguales en toda
# instancia — no son configurables por persona, así que van hardcodeados
# acá en vez de en config.env:
#   odoo        /home/odoo/src/odoo         core community
#   enterprise  /home/odoo/src/enterprise   enterprise
#   user        /home/odoo/src/user         el repo custom desplegado, INCLUIDOS
#                                           sus submódulos, si los tiene
#
# Leer de acá en vez de un checkout local tiene una ventaja real, no solo de
# comodidad: es exactamente el código que corrió. No hace falta preguntarse
# si el checkout local está sincronizado con lo desplegado.
#
# Uso:
#   remote_src.sh [--instance <nombre>] <root> lines <path> <linea-inicio> [linea-fin]
#   remote_src.sh [--instance <nombre>] <root> grep <patron> [path...]
#   remote_src.sh [--instance <nombre>] <root> cat <path>
#   remote_src.sh [--instance <nombre>] <root> exec <comando...>
#
# <root> es uno de: odoo | enterprise | user
#
# Ejemplos:
#   remote_src.sh user lines my_module/models/res_users.py 47 64
#   remote_src.sh odoo grep "_check_credentials" odoo/addons/base/models/res_users.py
#   remote_src.sh --instance v16 user cat my_module/models/account_move.py
set -uo pipefail

# shellcheck source-path=SCRIPTDIR source=lib.sh
. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib.sh"
load_config
warn_if_unconfigured

split_instance_flag "$@"
set -- "${ARGS[@]+"${ARGS[@]}"}"

declare -A ROOTS=(
  [odoo]="/home/odoo/src/odoo"
  [enterprise]="/home/odoo/src/enterprise"
  [user]="/home/odoo/src/user"
)

ROOT="${1:?uso: remote_src.sh [--instance <nombre>] <odoo|enterprise|user> <lines|grep|cat|exec> ...}"
CMD="${2:?falta el subcomando: lines | grep | cat | exec}"
shift 2

ROOTPATH="${ROOTS[$ROOT]:-}"
if [ -z "$ROOTPATH" ]; then
  echo "ERROR: root desconocido '$ROOT'. Usá odoo, enterprise o user." >&2
  exit 2
fi

select_instance "$INSTANCE_ARG" || exit $?
if [ -z "$SSH_TARGET" ]; then
  echo "ERROR: falta $(_upper "$INSTANCE")_SSH_TARGET en config.env." >&2
  exit 2
fi
echo "[instancia: $INSTANCE]" >&2

run_remote() {
  # Reconstruye el comando de forma segura para pasarlo por ssh, aunque
  # los argumentos traigan comillas, espacios o pipes.
  local quoted
  printf -v quoted '%q ' "$@"
  ssh -o ConnectTimeout=20 "$SSH_TARGET" "cd $(printf '%q' "$ROOTPATH") && $quoted"
}

case "$CMD" in
  lines)
    PATH_ARG="${1:?falta el path del archivo}"
    START="${2:?falta la línea de inicio}"
    END="${3:-$START}"
    run_remote sed -n "${START},${END}p" "$PATH_ARG"
    ;;
  grep)
    PATTERN="${1:?falta el patrón}"
    shift
    if [ $# -eq 0 ]; then
      run_remote grep -rn "$PATTERN" .
    else
      run_remote grep -n "$PATTERN" "$@"
    fi
    ;;
  cat)
    PATH_ARG="${1:?falta el path del archivo}"
    run_remote cat "$PATH_ARG"
    ;;
  exec)
    run_remote "$@"
    ;;
  *)
    echo "ERROR: subcomando desconocido '$CMD'. Usá lines, grep, cat o exec." >&2
    exit 2
    ;;
esac

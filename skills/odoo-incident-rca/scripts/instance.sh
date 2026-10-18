#!/usr/bin/env bash
# Muestra qué instancia resolvería el skill y qué le falta. Nunca imprime secretos.
#
# Uso:
#   instance.sh [--instance <nombre>]     # perfil resuelto + chequeos
#   instance.sh --list                    # todas las instancias configuradas
#
# Es lo primero que conviene correr en un incidente: confirma que se va a mirar
# la instancia correcta antes de bajar logs o consultar datos.
set -uo pipefail

# shellcheck source-path=SCRIPTDIR source=lib.sh
. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib.sh"
load_config
warn_if_unconfigured

if [ "${1:-}" = "--list" ]; then
  echo "config: ${CONFIG_FILE:-<ninguno>}"
  echo "default: ${DEFAULT_INSTANCE:-<ninguna>}"
  for i in $INSTANCES; do
    printf '  %-8s odoo %-5s repo-match=%s\n' "$i" "$(inst_var "$i" ODOO_VERSION)" "$(inst_var "$i" REPO_MATCH)"
  done
  exit 0
fi

split_instance_flag "$@"
select_instance "$INSTANCE_ARG" || exit $?

mark() { [ -n "$2" ] && echo "  ok   $1" || echo "  FALTA $1"; }

echo "instancia:      $INSTANCE   (Odoo ${ODOO_VERSION:-?})"
echo "config:         ${CONFIG_FILE:-<ninguno>}"
echo "repo local:     ${REPO_DIR:-<sin definir>}"
echo "incidentes en:  ${INCIDENTS_DIR:-<sin definir>}"
echo
echo "Qué hace falta para cada paso:"
mark "SSH_TARGET   (logs y source: fetch_logs.sh, remote_src.sh)" "$SSH_TARGET"
mark "REPO_DIR     (deploys.sh y la rama del fix)"               "$REPO_DIR"
mark "URL / DB / USER / API_KEY (odoo_query.py)" \
     "$(for v in URL DB USER API_KEY; do [ -z "$(inst_var "$INSTANCE" $v)" ] && printf x; done | grep -q x || echo set)"
if [ -n "$REPO_DIR" ] && [ ! -d "$REPO_DIR/.git" ]; then
  echo "  (!) REPO_DIR no es un repo git: $REPO_DIR"
fi
if [ -n "$INCIDENTS_DIR" ] && [ ! -f "$INCIDENTS_DIR/INDEX.md" ]; then
  echo "  (i) $INCIDENTS_DIR/INDEX.md no existe todavía: se crea desde templates/INDEX.md al cerrar el primer incidente."
fi

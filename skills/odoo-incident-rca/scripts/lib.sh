# shellcheck shell=bash
# Cargado internamente por los demás scripts de este skill — no se invoca directo.
#
# Modelo: el skill no sabe de qué instancia Odoo habla. Todo lo que cambia entre
# instancias (SSH, URL, base, repo, versión) vive en un *perfil* dentro de
# config.env, y los scripts lo resuelven por nombre.
#
# Resolución de la instancia, en este orden:
#   1. --instance <nombre>        (flag de cualquier script)
#   2. $RCA_INSTANCE              (entorno)
#   3. autodetección              (el remote `origin` del cwd coincide con <NOMBRE>_REPO_MATCH)
#   4. $DEFAULT_INSTANCE          (config.env)
#   5. la única instancia de INSTANCES, si hay una sola
#
# Cada perfil usa variables con el nombre de la instancia en mayúsculas como
# prefijo, p. ej. para `v19`: V19_SSH_TARGET, V19_URL, V19_DB, V19_USER,
# V19_API_KEY, V19_REPO_DIR, V19_REPO_MATCH, V19_ODOO_VERSION, V19_INCIDENTS_DIR.
SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Dónde está config.env. Fuera de ~/.claude a propósito: ese directorio es un
# repo git y config.env puede traer credenciales.
find_config() {
  local c
  for c in "${RCA_CONFIG:-}" \
           "${XDG_CONFIG_HOME:-$HOME/.config}/odoo-incident-rca/config.env" \
           "$SKILL_DIR/config.env"; do
    [ -n "$c" ] && [ -f "$c" ] && { printf '%s\n' "$c"; return 0; }
  done
  return 1
}

load_config() {
  CONFIG_FILE="$(find_config || true)"
  if [ -n "$CONFIG_FILE" ]; then
    # shellcheck disable=SC1090
    . "$CONFIG_FILE"
  fi
  : "${INSTANCES:=}"
  : "${DEFAULT_INSTANCE:=}"
}

warn_if_unconfigured() {
  [ -n "${CONFIG_FILE:-}" ] && return 0
  cat >&2 <<EOF
(!) No encontré config.env (busqué en \$RCA_CONFIG, ~/.config/odoo-incident-rca/ y $SKILL_DIR).
    Para crearlo:
      mkdir -p ~/.config/odoo-incident-rca
      cp "$SKILL_DIR/config.env.example" ~/.config/odoo-incident-rca/config.env
    y completá ahí tus instancias.
EOF
}

# Saca --instance de los argumentos. Deja INSTANCE_ARG y el array ARGS.
# Uso: split_instance_flag "$@"; set -- "${ARGS[@]+"${ARGS[@]}"}"
split_instance_flag() {
  ARGS=(); INSTANCE_ARG=""
  while [ $# -gt 0 ]; do
    case "$1" in
      --instance)   INSTANCE_ARG="${2:?--instance necesita un nombre}"; shift 2 ;;
      --instance=*) INSTANCE_ARG="${1#*=}"; shift ;;
      *)            ARGS+=("$1"); shift ;;
    esac
  done
}

_upper() { printf '%s' "$1" | tr '[:lower:]-' '[:upper:]_'; }

# inst_var <instancia> <SUFIJO> → valor de <INSTANCIA>_<SUFIJO> ("" si no está)
inst_var() {
  local name; name="$(_upper "$1")_$2"
  printf '%s' "${!name:-}"
}

# Nombre del repo del cwd según su remote origin (sin .git ni dueño).
_cwd_repo_name() {
  local url; url="$(git -C "${1:-.}" remote get-url origin 2>/dev/null)" || return 1
  basename "$url" .git
}

autodetect_instance() {
  local repo i match
  repo="$(_cwd_repo_name . 2>/dev/null)" || return 1
  for i in $INSTANCES; do
    match="$(inst_var "$i" REPO_MATCH)"
    [ -n "$match" ] && [ "$match" = "$repo" ] && { printf '%s\n' "$i"; return 0; }
  done
  return 1
}

# select_instance [nombre] — fija INSTANCE y las variables derivadas. Sin
# argumento toma el --instance que dejó split_instance_flag (INSTANCE_ARG).
select_instance() {
  local want="${1:-${INSTANCE_ARG:-${RCA_INSTANCE:-}}}"
  if [ -z "$want" ]; then want="$(autodetect_instance || true)"; fi
  if [ -z "$want" ]; then want="$DEFAULT_INSTANCE"; fi
  if [ -z "$want" ]; then
    # shellcheck disable=SC2086
    set -- $INSTANCES
    if [ $# -eq 1 ]; then want="$1"; fi
  fi
  if [ -z "$want" ]; then
    echo "ERROR: no pude decidir la instancia. Pasá --instance <nombre> (INSTANCES='${INSTANCES}')." >&2
    return 2
  fi
  case " $INSTANCES " in
    *" $want "*) ;;
    *) echo "ERROR: instancia '$want' no está en INSTANCES='${INSTANCES}' de ${CONFIG_FILE:-config.env}." >&2
       return 2 ;;
  esac
  INSTANCE="$want"
  SSH_TARGET="$(inst_var "$INSTANCE" SSH_TARGET)"
  ODOO_VERSION="$(inst_var "$INSTANCE" ODOO_VERSION)"
  REPO_DIR="$(inst_var "$INSTANCE" REPO_DIR)"
  INCIDENTS_DIR="$(inst_var "$INSTANCE" INCIDENTS_DIR)"
  # Sin REPO_DIR explícito: si el cwd es el repo de esta instancia, usarlo.
  if [ -z "$REPO_DIR" ]; then
    local match; match="$(inst_var "$INSTANCE" REPO_MATCH)"
    if [ -n "$match" ] && [ "$(_cwd_repo_name . 2>/dev/null)" = "$match" ]; then
      REPO_DIR="$(git rev-parse --show-toplevel)"
    fi
  fi
  if [ -z "$INCIDENTS_DIR" ] && [ -n "$REPO_DIR" ]; then
    INCIDENTS_DIR="$REPO_DIR/docs/incidents"
  fi
  export INSTANCE SSH_TARGET ODOO_VERSION REPO_DIR INCIDENTS_DIR
}

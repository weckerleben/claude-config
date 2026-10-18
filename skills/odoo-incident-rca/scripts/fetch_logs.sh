#!/usr/bin/env bash
# Download Odoo.sh logs. Handles the two quirks that break the obvious approach:
#   - the SFTP subsystem is unavailable, so scp needs -O (legacy protocol)
#   - brace expansion does not happen remotely, so one scp per file
#
# Usage:
#   fetch_logs.sh [--instance <name>] [ssh-target] <dest-dir> [YYYY-MM-DD ...]
#
#   The ssh target comes from the instance profile (<NAME>_SSH_TARGET in
#   config.env). Pass one explicitly to hit a different build/branch; it is
#   detected by the "@" a real ssh target always has and a dest-dir never does.
#
#   With no dates, downloads everything in the remote logs directory.
#   With dates, downloads files whose name contains any of them, plus the
#   always-current odoo.log / pg_slow_queries.log / sh_*.log.
set -uo pipefail

# shellcheck source-path=SCRIPTDIR source=lib.sh
. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib.sh"
load_config
warn_if_unconfigured

# Fija en toda instancia Odoo.sh, no depende de la persona ni de la máquina.
REMOTE_LOG_DIR=/home/odoo/logs

split_instance_flag "$@"
set -- "${ARGS[@]+"${ARGS[@]}"}"

if [[ "${1:-}" == *@* ]]; then
  TARGET="$1"; shift
else
  select_instance "$INSTANCE_ARG" || exit $?
  TARGET="$SSH_TARGET"
  echo "==> instancia: $INSTANCE" >&2
fi
DEST="${1:?uso: fetch_logs.sh [--instance <nombre>] [ssh-target] <dest-dir> [YYYY-MM-DD ...]}"
shift
DATES=("$@")

if [ -z "$TARGET" ]; then
  echo "ERROR: falta el ssh-target (no vino como argumento y no hay SSH_TARGET para la instancia en config.env)." >&2
  echo "       Ejemplo: fetch_logs.sh 1234567@<proyecto>.odoo.com $DEST" >&2
  exit 2
fi

mkdir -p "$DEST"

echo "==> listando $TARGET:$REMOTE_LOG_DIR"
FILES=$(ssh -o ConnectTimeout=20 "$TARGET" "ls -1 $REMOTE_LOG_DIR" 2>/dev/null)
if [ -z "$FILES" ]; then
  echo "ERROR: no se pudo listar $REMOTE_LOG_DIR (¿host o credenciales?)" >&2
  exit 1
fi

# Always take the live files; they hold today and are what the report usually refers to.
ALWAYS='^(odoo\.log|pg_slow_queries\.log|sh_.*\.log)$'

select_file() {
  local f="$1"
  [[ "$f" =~ $ALWAYS ]] && return 0
  [ ${#DATES[@]} -eq 0 ] && return 0
  for d in "${DATES[@]}"; do [[ "$f" == *"$d"* ]] && return 0; done
  return 1
}

n=0; failed=0
while IFS= read -r f; do
  [ -z "$f" ] && continue
  select_file "$f" || continue
  echo "==> $f"
  if scp -O -o ConnectTimeout=20 "$TARGET:$REMOTE_LOG_DIR/$f" "$DEST/" 2>&1 | grep -v '^$'; then :; fi
  if [ -s "$DEST/$f" ]; then n=$((n+1)); else echo "    (vacío o falló)"; failed=$((failed+1)); fi
done <<< "$FILES"

echo "==> descomprimiendo (conservando .gz)"
shopt -s nullglob
for g in "$DEST"/*.gz; do gunzip -k -f "$g" && echo "    $(basename "$g")"; done

echo
echo "==> $n archivos en $DEST ($failed fallidos)"
find "$DEST" -maxdepth 1 -type f -exec du -h {} +
cat <<'NOTE'

Recordá: los timestamps de estos logs están en UTC.
NOTE

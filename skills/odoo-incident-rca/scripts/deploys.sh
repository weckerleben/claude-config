#!/usr/bin/env bash
# Cuándo hubo deploys a producción, y cuáles coinciden con reinicios en el log.
#
# Odoo.sh despliega al recibir un push a la rama de producción, así que la hora
# de merge de un PR es el disparador del reinicio. En la práctica el reinicio
# llega entre 15 y 60 segundos después del merge.
#
# Uso:
#   deploys.sh [--instance <nombre>] [repo-dir] <YYYY-MM-DD> [YYYY-MM-DD-fin] [--log <archivo>]
#
#   repo-dir es opcional: si el primer argumento no tiene forma de fecha, se
#   toma como repo-dir; si sí la tiene, se usa el repo de la instancia
#   (<NOMBRE>_REPO_DIR en config.env, o el cwd si es el repo de esa instancia).
#
#   Con --log, además cruza cada deploy con los reinicios de flota del log y
#   muestra la diferencia en segundos. Un delta chico es correlación fuerte.
#
# Todas las horas se muestran en UTC, igual que los logs de Odoo.sh.
set -uo pipefail

# shellcheck source-path=SCRIPTDIR source=lib.sh
. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib.sh"
load_config
warn_if_unconfigured

split_instance_flag "$@"
set -- "${ARGS[@]+"${ARGS[@]}"}"

DATE_RE='^[0-9]{4}-[0-9]{2}-[0-9]{2}$'
if [[ "${1:-}" =~ $DATE_RE ]]; then
  select_instance "$INSTANCE_ARG" || exit $?
  REPO="$REPO_DIR"
  if [ -z "$REPO" ]; then
    echo "ERROR: no hay repo para la instancia '$INSTANCE'. Definí $(_upper "$INSTANCE")_REPO_DIR en config.env, corré desde el repo, o pasá repo-dir." >&2
    exit 2
  fi
else
  REPO="${1:?uso: deploys.sh [repo-dir] <YYYY-MM-DD> [fin] [--log archivo]}"
  shift
fi
FROM="${1:?falta la fecha YYYY-MM-DD}"
shift
TO=""; LOGFILE=""
while [ $# -gt 0 ]; do
  case "$1" in
    --log) LOGFILE="$2"; shift 2 ;;
    *)     TO="$1"; shift ;;
  esac
done
[ -z "$TO" ] && TO=$(TZ=UTC date -j -v+1d -f "%Y-%m-%d" "$FROM" "+%Y-%m-%d" 2>/dev/null \
                  || TZ=UTC date -d "$FROM + 1 day" "+%Y-%m-%d" 2>/dev/null || echo "$FROM")

[ -d "$REPO/.git" ] || { echo "ERROR: $REPO no es un repo git" >&2; exit 1; }
BRANCH=$(git -C "$REPO" symbolic-ref --short refs/remotes/origin/HEAD 2>/dev/null | sed 's|^origin/||')
BRANCH="${BRANCH:-master}"

echo "=============================================================="
echo " Deploys a $BRANCH — $FROM .. $TO   (todo en UTC)"
echo "=============================================================="
echo

DEPLOYS=""

# Preferimos GitHub: da la hora de merge exacta y en UTC, y no depende de que
# el checkout local esté actualizado (suele estar viejo o en otra rama).
if command -v gh >/dev/null && gh auth status >/dev/null 2>&1; then
  echo "--- PRs mergeados (GitHub) ---"
  DEPLOYS=$(cd "$REPO" && gh pr list --state merged --base "$BRANCH" --limit 50 \
    --search "merged:${FROM}..${TO}" \
    --json number,title,mergedAt,author \
    --template '{{range .}}{{.mergedAt}}|#{{.number}}|{{.author.login}}|{{.title}}{{"\n"}}{{end}}' 2>/dev/null)
  if [ -n "$DEPLOYS" ]; then
    echo "$DEPLOYS" | sort | awk -F'|' '{printf "  %s  %-7s %-22s %s\n", $1, $2, $3, substr($4,1,60)}'
  else
    echo "  (ninguno en el rango)"
  fi
else
  echo "  (gh no disponible; usando el historial local — puede estar desactualizado)"
  echo "  Corré primero: git -C $REPO fetch origin $BRANCH"
fi

echo
echo "--- Merges en el historial local (committer date, normalizado a UTC) ---"
TZ=UTC git -C "$REPO" log --first-parent --merges \
  --since="${FROM}T00:00:00Z" --until="${TO}T23:59:59Z" \
  --date=iso-local --format="  %cd  %h  %an :: %s" "origin/$BRANCH" 2>/dev/null \
  || echo "  (sin datos; probá git fetch)"

if [ -n "$LOGFILE" ] && [ -r "$LOGFILE" ]; then
  echo
  echo "--- Reinicios de flota en $(basename "$LOGFILE") ---"
  RESTARTS=$(grep -E "Initiating shutdown" "$LOGFILE" \
    | grep -oE "^[0-9-]+ [0-9]{2}:[0-9]{2}:[0-9]{2}" | uniq -c \
    | awk '$1>=5 {print $2"T"$3}')
  if [ -z "$RESTARTS" ]; then
    echo "  (ninguno)"
  else
    echo "$RESTARTS" | sed 's/T/ /' | sed 's/^/  /'
  fi

  if [ -n "$DEPLOYS" ] && [ -n "$RESTARTS" ]; then
    echo
    echo "--- Correlación deploy → reinicio ---"
    echo "  Un delta de segundos confirma que el deploy causó el reinicio."
    python3 - "$DEPLOYS" "$RESTARTS" <<'PY'
import sys, datetime
def parse(s, fmt): return datetime.datetime.strptime(s, fmt)
deploys = [l.split('|') for l in sys.argv[1].strip().splitlines() if l.strip()]
restarts = [parse(r.strip(), "%Y-%m-%dT%H:%M:%S") for r in sys.argv[2].strip().splitlines() if r.strip()]
for d in sorted(deploys):
    t = parse(d[0].replace('Z', ''), "%Y-%m-%dT%H:%M:%S")
    near = [(abs((r - t).total_seconds()), r) for r in restarts]
    near.sort()
    if near and near[0][0] <= 600:
        delta, r = near[0]
        mark = "<<<" if delta <= 120 else ""
        print(f"  {d[1]:<7} {d[0]}  ->  reinicio {r.strftime('%H:%M:%S')}  (+{int(delta)}s) {mark}")
    else:
        print(f"  {d[1]:<7} {d[0]}  ->  sin reinicio cercano")
PY
  fi
fi

cat <<'NOTE'

Si un fallo de usuario cae dentro de uno de esos reinicios, el deploy es el
disparador: ThreadedServer.stop() espera un segundo a los hilos de request y
después cierra el pool entero, sin mirar si las conexiones están en uso. El
contenido del commit es irrelevante — lo que rompe es el reinicio en sí.
NOTE

#!/usr/bin/env bash
# What happened around a moment in an Odoo.sh log: restarts, deploys, crons,
# worker kills, and whether any of it was a genuine out-of-memory event.
#
# Usage: timeline.sh <log-file> <HH:MM:SS> [window-seconds]   (default 120)
# Times are UTC, matching the log.
set -uo pipefail

LOG="${1:?uso: timeline.sh <log-file> <HH:MM:SS> [ventana-segundos]}"
AT="${2:?falta la hora HH:MM:SS}"
WIN="${3:-120}"

[ -r "$LOG" ] || { echo "ERROR: no puedo leer $LOG" >&2; exit 1; }

win_lines() {  # stdin -> lines whose HH:MM:SS falls within +-WIN of AT
  awk -v at="$AT" -v win="$WIN" '
    function secs(t,  a) { split(t, a, ":"); return a[1]*3600 + a[2]*60 + a[3] }
    BEGIN { target = secs(at) }
    {
      ts = $2; sub(/,.*/, "", ts)
      if (ts ~ /^[0-9][0-9]:[0-9][0-9]:[0-9][0-9]$/) {
        d = secs(ts) - target; if (d < 0) d = -d
        if (d <= win) print
      }
    }' "$LOG"
}

echo "=============================================================="
echo " $LOG  —  ${AT} UTC  ±${WIN}s"
echo "=============================================================="

echo
echo "--- Reinicios de flota (>=5 procesos en el mismo segundo = deploy) ---"
grep -E "Initiating shutdown" "$LOG" | grep -oE "^[0-9-]+ [0-9]{2}:[0-9]{2}:[0-9]{2}" \
  | uniq -c | awk '$1>=5 {print "   "$1" procesos  "$2" "$3}' | head -20
echo "   (reloads SIGHUP, mucho menos disruptivos:)"
grep -c "Initiating server reload" "$LOG" | sed 's/^/   Initiating server reload: /'

echo
echo "--- Contenedor nuevo: pids bajos cargando módulos desde cero ---"
grep -E "modules loaded|Registry loaded" "$LOG" \
  | awk -v at="$AT" -v win="$WIN" '
      function secs(t,  a){split(t,a,":"); return a[1]*3600+a[2]*60+a[3]}
      BEGIN{target=secs(at)}
      { ts=$2; sub(/,.*/,"",ts)
        if (ts ~ /^[0-9][0-9]:[0-9][0-9]:[0-9][0-9]$/) {
          d=secs(ts)-target; if(d<0)d=-d
          if (d<=win) printf "   %s [pid %s] %s\n", ts, $3, substr($0, index($0,$6)) } }' | head -15

echo
echo "--- Errores y kills en la ventana ---"
win_lines | grep -E " (ERROR|CRITICAL) |killed by signal|deactivated due to" \
  | sed -E 's/^([0-9-]+ [0-9:,]+) ([0-9]+) /   \1 [pid \2] /' | cut -c1-170 | head -30

echo
echo "--- Crons en la ventana ---"
win_lines | grep -E "Starting job|Job .* done|cron .* failed" \
  | sed -E 's/^([0-9-]+ ([0-9:]+)),[0-9]+ [0-9]+ [A-Z]+ [^ ]+ [^:]+: /   \2  /' | head -25

echo
echo "--- ¿OOM real? (mensajes propios de Odoo, no la etiqueta de Odoo.sh) ---"
for p in "Server memory limit" "virtual memory limit" "MemoryError" "timeout after"; do
  printf "   %-24s %s\n" "$p:" "$(grep -c "$p" "$LOG")"
done
echo "   killed by signal 9:      $(grep -c 'killed by signal 9' "$LOG")   <-- genérico, NO prueba OOM"
cat <<'NOTE'

   Si los cuatro primeros dan 0, no fue el limitador de Odoo. El mensaje
   "most likely hit a memory limit" lo emite el supervisor de Odoo.sh para
   cualquier SIGKILL, incluido un worker que no alcanzó a salir a tiempo.
NOTE

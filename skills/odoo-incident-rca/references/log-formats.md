# Formatos de log en Odoo.sh

Todos los timestamps son **UTC**.

## Archivos en `/home/odoo/logs`

| Archivo | Contenido |
|---|---|
| `odoo.log` | Día en curso. Se rota a medianoche. |
| `odoo.log.YYYY-MM-DD` | Día cerrado, sin comprimir (normalmente el anterior). |
| `odoo.log.YYYY-MM-DD.gz` | Días anteriores, comprimidos. |
| `pg_slow_queries.log` | Consultas de PostgreSQL por encima del umbral de captura. |
| `sh_editor.log`, `sh_webshell.log` | Actividad del editor web y la shell de Odoo.sh. Rara vez útil para un incidente. |

## Línea estándar de `odoo.log`

```
2026-08-11 18:58:34,843 481 ERROR <base-de-datos> odoo.sql_db: bad query: ...
└── fecha y hora ──────┘ └pid┘ nivel  └─ logger ─┘
```

`<base-de-datos>` es el nombre completo de la instancia (típicamente `<código>-<rama>-<build>`, ej. `3mit-grupocashea-master-7528048`); cambia con cada build.

El **pid** es la pista más útil: todo lo que ese proceso hizo en los minutos previos es el contexto del fallo.

## Línea de performance de werkzeug

```
"POST /web/dataset/call_kw/... HTTP/1.0" 200 - 256 263.996 0.050
                                                   └queries┘ └sql┘ └otro┘
```

Tres campos: **cantidad de consultas**, **segundos en SQL**, **segundos fuera de SQL**.

Si el tiempo SQL es una fracción chica del total, el problema no es la base — es HTTP externo, generación de reportes o Python. Leer este número antes de teorizar ahorra horas: en el incidente de agosto de 2026 una petición de 496 s tenía apenas 43 s de SQL, lo que descartó de entrada toda la línea de investigación sobre índices.

## Ciclo de vida de los crons

```
Starting job `<nombre>`.
Job `<nombre>` done.
Call from cron <nombre> for server action #<id> failed in Job #<n>
odoo.sh: cron '<nombre>' (id=N) was deactivated due to repeated timeouts
```

Contar arranques contra finalizaciones revela degradación progresiva mucho antes de que la plataforma desactive el cron:

```bash
for f in odoo.log*; do
  echo "$f: $(grep -c 'Starting job `X`' "$f") arranques / $(grep -c 'Job `X` done' "$f") completados"
done
```

Odoo.sh impone un techo de wall-clock (~30 min) y desactiva a los reincidentes. Un cron que "se cuelga" suele estar simplemente excediendo ese techo.

## Reinicios: deploy contra reload

| Firma | Qué es |
|---|---|
| Muchos `Initiating shutdown` en el mismo segundo, después pids **bajos** cargando `200 modules` | **Deploy**: contenedor nuevo |
| `Initiating server reload` sobre el **mismo** pid | Reload por SIGHUP (`odoo.phoenix`), mucho menos disruptivo |
| `Worker process (pid=N) was killed by signal 9` | SIGKILL genérico del supervisor. **No** prueba falta de memoria. |

Para confirmar un OOM real hay que encontrar los mensajes propios de Odoo: `Server memory limit`, `virtual memory limit`, `MemoryError`, o el watchdog `timeout after Ns`. Si los cuatro dan cero, no fue el limitador de Odoo.

Los builds de la rama en Odoo.sh mapean 1:1 con los reinicios de flota. Correlacionar la hora del deploy con la del fallo suele cerrar el caso.

## `pg_slow_queries.log`

Bloques separados por **80 guiones**. Cada uno arranca con una cabecera que incluye `approximate duration: N seconds` y sigue con el texto completo de la consulta.

El umbral de captura ronda los **30 segundos**, así que toda consulta del archivo tardó al menos eso — y las distribuciones están truncadas por abajo. Una "meseta" en 30-35 s es artefacto del umbral, no un hecho físico.

Para agregar por forma de consulta, normalizando literales:

```python
import re, collections
txt = open('pg_slow_queries.log', encoding='utf-8', errors='replace').read()
hdr = re.compile(r'approximate duration: (\d+) seconds', re.S)
agg = collections.defaultdict(lambda: {'n': 0, 'tot': 0, 'max': 0, 'ej': ''})
for b in txt.split('-' * 80):
    m = hdr.search(b)
    if not m:
        continue
    d, q = int(m.group(1)), b[m.end():].strip()
    if not q:
        continue
    k = re.sub(r'\s+', ' ', re.sub(r'\b\d+\b', 'N', re.sub(r"'[^']*'", '?', q)))[:150]
    a = agg[k]
    a['n'] += 1; a['tot'] += d; a['max'] = max(a['max'], d)
    a['ej'] = a['ej'] or q[:200].replace('\n', ' ')
for k, v in sorted(agg.items(), key=lambda kv: -kv[1]['tot'])[:15]:
    print(f"{v['n']:>6} {v['tot']:>8}s {v['max']:>5}s  {v['ej'][:90]}")
```

Ordenar por tiempo total acumulado, no por máximo: una consulta de 34 s que corre 20.000 veces pesa mucho más que una de 1.800 s que corre una vez.

# Índice de incidentes

Primera fuente de verdad sobre incidentes ya diagnosticados en esta instancia de Odoo: qué pasó, por qué, y qué se sabe. Lo usan tres lectores, sin duplicar contenido en ningún otro lugar:

- **El skill `odoo-incident-rca`** — antes de investigar de cero (Step 2), busca acá si el síntoma ya se vio.
- **Desarrolladores** — el archivo linkeado en cada fila tiene la cadena causal completa con `file:line`.
- **Analistas funcionales** — el link desde el ticket de Jira trae hasta acá; no hace falta acceso a Notion ni al código.

Es markdown en git, a propósito: los hechos que cambian con el código viven con el código, y no se desincronizan en cuanto alguien mergea un PR.

## Formato de cada fila

| Fecha | Instancia | Ticket(s) | Síntoma | Palabras clave | Causa raíz (una línea) | Estado | Análisis |
|---|---|---|---|---|---|---|---|

- **Fecha** — cuándo se reportó, `YYYY-MM-DD`.
- **Instancia** — nombre del perfil (`v16`, `v19`…), para que un grep en cualquiera de los dos índices diga de qué sistema se habla.
- **Ticket(s)** — Jira, con el ticket original primero si hay duplicados.
- **Síntoma** — lo que alguien reportó, en sus palabras, no en las del código. Es lo que alguien va a buscar.
- **Palabras clave** — clase de excepción, nombres de función/modelo, términos que aparecerían en un traceback futuro parecido. Esto es lo que hace `grep` útil; sin esto el índice es solo un changelog.
- **Causa raíz** — una oración, sin la cadena completa (eso vive en el análisis).
- **Estado** — `🟢 Arreglado (fusionado)` / `🟡 Fix listo, no fusionado` / `🔴 Abierto` / `🔁 Recurrente → ver <fila>` (cuando un "arreglado" reaparece — eso es un hallazgo en sí mismo, no un error del índice).
- **Análisis** — link relativo al archivo completo en esta misma carpeta.

Una fila nueva se agrega, no se reemplaza una existente — salvo para actualizar el Estado a medida que el fix avanza (rama → PR → fusionado). Si un incidente "arreglado" reaparece, la fila nueva referencia a la vieja con `🔁 Recurrente`; no se reescribe la historia.

---

| Fecha | Instancia | Ticket(s) | Síntoma | Palabras clave | Causa raíz | Estado | Análisis |
|---|---|---|---|---|---|---|---|

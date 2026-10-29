# Commit mode detection — cache and algorithm

Reference for the dual commit policy in `~/.claude/CLAUDE.md` (Conventional Commits vs Odoo Git
Guidelines). Moved out of CLAUDE.md so it does not load every turn.

Correr `find` + inspección del manifest en cada `/commit` es lento en repos
grandes (ej. monorepos Odoo con 10+ módulos). El modo detectado se cachea en:

```
~/.claude/.cache/repo-modes.json
```

Formato:
```json
{
  "/abs/path/to/repo": {
    "mode": "odoo | conventional",
    "detected_at": "2026-07-12T00:00:00Z",
    "marker": "manifest:<path> | org:<pattern>"
  }
}
```

Reglas de cache:
- Válido por 30 días desde `detected_at`.
- Invalidación manual: correr cualquiera de `/commit`, `/pr`, `/ship` con la
  flag `--recheck-mode`.
- Purga manual completa: `rm ~/.claude/.cache/repo-modes.json` (se
  regenera solo en el próximo comando). Purga de un repo puntual (misma
  variante atómica same-dir que las escrituras):

  ```bash
  tmpfile=$(mktemp ~/.claude/.cache/repo-modes.json.XXXXXX)
  jq 'del(."/abs/path/to/repo")' ~/.claude/.cache/repo-modes.json >| "$tmpfile" \
    && mv "$tmpfile" ~/.claude/.cache/repo-modes.json
  # >| overrides zsh noclobber; mktemp pre-creates the file so a bare > would fail
  ```

- Writes are atomic via tmpfile + mv to survive concurrent Claude Code
  sessions (e.g. two terminals open on the same repo at once).
- The cache is keyed by absolute repo path, not by branch. If you
  deliberately maintain different commit conventions per branch (rare —
  usually a smell), run `/commit --recheck-mode` when switching branches, or
  manually purge the repo's cache entry.
- Interrupted writes may leave `repo-modes.json.XXXXXX` orphans in
  `~/.claude/.cache/`; occasional `rm -f ~/.claude/.cache/repo-modes.json.*`
  is safe.

## Algoritmo de detección (en cache miss o `--recheck-mode`)

1. `find . -maxdepth 4 -name "__manifest__.py" -not -path "*/node_modules/*" -not -path "*/.venv/*" -not -path "*/venv/*" -not -path "*/.git/*" -not -path "*/dist/*" -not -path "*/build/*" 2>/dev/null`
   (maxdepth 4: workspaces reales tienen manifests a profundidad 4, ej.
   `clients/paraguay/l10n_py_edi/__manifest__.py` en eagle)
2. Para cada match: `grep -l "'depends'" <archivo>` — si matchea, es Odoo
   (evita parsear Python en el caso común).
3. Si el grep es ambiguo (ej. la palabra aparece en un comentario), fallback
   a `python3 -c "import ast; ..."` para parsear el dict real y confirmar la
   clave — nunca como default, solo en caso dudoso.
4. Si no hay manifest en absoluto: chequear `origin` remote contra
   `cashea-*` / `unifica-*` / `OCA-*`.
5. Si nada matchea: modo Conventional.

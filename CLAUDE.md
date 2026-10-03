# Instrucciones globales — William Eckerleben

## Stack principal
- Python/Odoo (XML-RPC, ORM, módulos custom)
- TypeScript/Next.js (App Router, Supabase)
- PostgreSQL (optimización, índices, queries complejas)
- Infraestructura (Docker, CI/CD, Odoo.sh)

## Reglas de compactación
- Después de research → antes de implementar: SIEMPRE compactar
- Después de resolver un bug: compactar antes del próximo feature
- Mid-implementación: NO compactar
- Al cambiar de proyecto en la misma sesión: SIEMPRE compactar

## Modo de trabajo
- Una sesión por proyecto
- Usar /compact con resumen explícito de qué preservar
- TDD obligatorio: tests antes de implementar

## Lo que NO hacer
- No instalar dependencias globales sin preguntar
- No cambiar infraestructura sin confirmación explícita

## UI/UX Gate — frontend al 110% (INNEGOCIABLE)

Aplica a **cualquier** archivo de front: HTML, JSX/TSX, Vue/Svelte/Astro, CSS/SCSS,
componentes, dashboards, artifacts. William no tiene noción de UI/UX y delega el
criterio de diseño en el agente — por eso el default de "meter los datos y listo"
está **prohibido**. Un hook (`frontend-design-gate.js`) recuerda esto al tocar front;
la regla vale igual aunque el hook no dispare.

**Reusar el criterio de diseño de ECC ya instalado — no reinventarlo.** Las skills
`make-interfaces-feel-better`, `frontend-design-direction`, `design-system` y `taste`,
y el loop `gan-design` (generador/evaluador con score), cubren esto. `design-quality.md`
es el checklist base.

**Antes de escribir código de front, obligatorio:**
1. Cargar criterio: invocar la skill `make-interfaces-feel-better` y/o
   `frontend-design-direction`, más `~/.claude/rules/ecc/web/design-quality.md`
   (anti-template, jerarquía, estados). Checklist activo, no referencia opcional.
2. Declarar un **design pass** explícito antes del código: dirección de estilo,
   **jerarquía visual** (qué elemento MANDA y qué se subordina), y — obligatorio —
   el **encaje en contexto**: leer qué hay arriba/abajo/al lado en la misma vista y
   justificar que el elemento nuevo **pertenece** ahí y no compite con lo existente.
   Nada de grillas planas de celdas idénticas; nunca juzgar la pieza aislada.
3. Honrar el sistema existente (tokens, componentes). Específico y consistente
   gana a genérico.

**Después de codear, obligatorio:**
4. Correr el loop de diseño de ECC: skill `gan-design`, o el subagente `design-critic`
   (`subagent_type: "design-critic"`). Su **primer paso es mapear la superficie/vecinos
   y juzgar el encaje**, y recién después criticar ("esto va acá, queda como el culo,
   mejor allá"). Aplicar lo que valga **antes** de cerrar. No se cierra front sin pasar
   por el crítico.

Regla mental: si el resultado no se vería creíble en un screenshot de producto real,
no está terminado.

## Code Quality — Warnings Policy

**ALWAYS resolve warnings, never suppress them silently.**

When running tests, builds, linters, or any execution:
1. If warnings appear in output → treat them as blocking issues, not noise
2. Fix the root cause — do NOT add suppression annotations (e.g. `@SuppressWarnings`, `# noqa`, `// eslint-disable`) unless I explicitly authorize it
3. After fixing, re-run the command to confirm warnings are gone
4. If a warning requires broader refactor, flag it explicitly before proceeding
5. Zero-warning policy applies to: test runs, type checks, linting, build output, runtime logs

## Idioma

- Todo artefacto de código va en inglés, sin excepciones: mensajes de commit,
  títulos/cuerpos de PR, CHANGELOG, release notes, nombres de branch, títulos
  de issues, comentarios de código, docs.
- La conversación conmigo (William) es en español paraguayo.
- Nunca mezclar. Si un proyecto puntual necesita artefactos en español, eso se
  declara en el CLAUDE.md local de ese repo y sobreescribe esta regla — no se
  asume nunca por default.

## Identidad Git

- Fuente de verdad: `~/.gitconfig` (`user.name`, `user.email`). No la
  reconfigures, solo referenciala.
- **Prohibido** agregar `Co-Authored-By: Claude`, cualquier firma del agente,
  emoji de Claude, o "🤖 Generated with Claude Code" — ni en commits, ni en
  cuerpos de PR, ni en release notes, ni en tags anotados. Aplica incluso si
  un template externo ya lo trae por default: se remueve antes de usar el
  template.
- Nunca commitear como Claude. Si el autor efectivo de un commit no coincide
  con la identidad de `~/.gitconfig`, parar y preguntar antes de continuar.

## Commit Convention — política dual por contexto de repo

Regla por defecto: **Conventional Commits v1.0.0**. Excepción a **Odoo Git
Guidelines** si se detecta:

- Un `__manifest__.py` (Python, no JSON) en algún directorio del repo, con
  clave `depends` a nivel top del dict. **Este marcador es autoritativo por
  sí solo** — si está presente, el repo es Odoo, punto. No hace falta
  ninguna otra señal.
- Únicamente si el marcador de archivo **no** está presente todavía (repo
  recién creado, WIP sin manifest aún), usar como *booster* de fallback: el
  remote pertenece a `cashea-*`, `unifica-*`, u `OCA-*`. Esta lista NUNCA
  contradice al marcador de archivo — si hay `__manifest__.py` con `depends`,
  la lista de orgs es irrelevante y ni se consulta.
- La config local de commit-linting del repo (ver sección "Commitlint local")
  siempre gana sobre esta política dual global.

Claude detecta el modo en runtime antes de proponer cualquier mensaje de
commit, PR, tag o release. Nunca mezcla los dos estilos en el mismo repo.

### Cache de detección de modo

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

### Algoritmo de detección (en cache miss o `--recheck-mode`)

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

### Commitlint local sobreescribe la política global

Si el repo tiene `commitlint.config.js`, cualquier `.commitlintrc*`, o una
clave `commitlint` en `package.json`: leer `type-enum`, `scope-enum`, y
`header-max-length` de ahí y **respetarlos por encima** de la política dual
de este archivo, sin preguntar. Solo anunciar en el output qué se está
respetando (ej: "respetando commitlint local: types restringidos a
[feat, fix, chore]"). Esto aplica únicamente en modo Conventional — un repo
Odoo no tiene commitlint por convención de esa comunidad.

### Modo Conventional Commits (default)

Formato: `<type>(<scope>): <subject>`

- `type` — uno de: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `perf`,
  `build`, `ci`, `revert` (salvo que commitlint local restrinja la lista)
- `scope` opcional, sustantivo entre paréntesis (`fix(parser):`)
- `subject`: imperativo, minúscula tras el prefijo, sin punto final, **≤72
  caracteres** (salvo `header-max-length` de commitlint local)
- Breaking change: `!` antes de los dos puntos (`feat(api)!: remove endpoint`)
  o footer `BREAKING CHANGE: <descripción>`
- Body (opcional): explica el QUÉ y el POR QUÉ, wrap a 72 columnas
- Footer: `Refs #N`, `Closes #N`, `BREAKING CHANGE: ...`

Correlación con SemVer:

| type | Bump |
|---|---|
| `feat` | MINOR |
| `fix` | PATCH |
| `!` o `BREAKING CHANGE:` (cualquier type) | MAJOR |
| `docs`, `refactor`, `test`, `chore`, `perf`, `build`, `ci`, `revert` | Sin bump (salvo que también incluyan `!`) |

Ejemplos válidos:
```
feat(auth): add refresh token rotation
fix(parser): prevent crash on empty input
feat(api)!: remove deprecated /v1/users endpoint
chore: bump vite to 6.0
```

Ejemplos inválidos:
```
Fixed the bug.              // mayúscula inicial, no imperativo, punto final
[FIX] auth: token bug        // mezcla con formato Odoo
updated stuff                // sin type, no descriptivo
feat: Added new feature.     // mayúscula, "Added" no es imperativo, punto final
```

### Modo Odoo (repos Odoo detectados)

Fuente: Odoo 19.0 `git_guidelines.rst`. Formato: `[TAG] module: description`

Tags: `FIX` `REF` `ADD` `REM` `REV` `MOV` `REL` `IMP` `MERGE` `CLA` `I18N`
`PERF` `CLN` `LINT`

- Header **≤72 caracteres** (alineado con el validador de CI de
  cashea-odoo-v19; la guía oficial de Odoo dice 50, pero el equipo usa 72)
- Ticket opcional entre corchetes **después** del tag:
  `[FIX][EP-356] module: description`. Nunca el ticket primero
  (`EP-356 ...` no es válido).
- El header debe formar una oración válida al anteponerle "if applied, this
  commit will `<header>`"
- `module` es el nombre técnico del módulo (no el funcional). Si son varios:
  listarlos o usar `various`. Evitar tocar módulos cruzados en un solo commit
  salvo necesidad real.
- Body: prioriza el POR QUÉ sobre el QUÉ. Cerrar con referencias: número de
  tarea, PR/issue de GitHub, ticket OPW.

Ejemplos válidos:
```
[FIX] sale: prevent negative quantity on return
[ADD] account_reconciliation: bank statement matcher
[IMP] stock: faster quant computation on large warehouses
```

Ejemplos inválidos:
```
fix(sale): prevent negative quantity   // formato Conventional en repo Odoo
[FIX] bugfix                            // no es oración, sin contexto real
[fix] sale: ...                         // tag debe ir en mayúscula
```

## Branch Naming

Formato: `<type>/<short-kebab-description>`, opcionalmente
`<type>/<TICKET-ID>-<description>` si el repo usa issue tracker.

Types: `feature` `bugfix` `hotfix` `release` `refactor` `docs` `test` `chore`
`ci`

Regex validador:
```
^(feature|bugfix|hotfix|release|refactor|docs|test|chore|ci)\/[a-z0-9][a-z0-9-\/]*[a-z0-9]$
```

Nunca usar `main`, `master`, `develop`, `HEAD` ni nombres reservados como
nombre de branch de trabajo.

## PR Format

- **Título**: sigue el modo detectado del repo, no siempre Conventional.
  - Modo Conventional → título = `type: description`
  - Modo Odoo → título = `[TAG] module: description` o
    `[TAG][EP-123] module: description` (≤72 chars, misma regla del
    "if applied..."). La convención social del repo pesa más que la
    parseabilidad de GitHub.
- **Body**, homogéneo en ambos modos (es formato de contenido, no convención
  de comunidad): **Context**, **Changes**, **Testing**, **Screenshots** (solo
  si hay cambios de UI), **Notes**.
- Nunca dejar branding de Claude en el body, ni siquiera si viene de un
  template externo.

## Pre-push Gate

Antes de cualquier `git push`, descubrir y correr gates en este orden de
prioridad (el primero que aplique gana, no se combinan):
1. `package.json` con scripts `test`/`build`/`lint` → correr esos.
2. `Makefile` con targets `test`/`build`/`lint` → correr esos.
3. `pyproject.toml` con config de `tox`, `pytest`, `ruff`, o
   `[tool.poetry.scripts]` → deducir e invocar.
4. CI (`.github/workflows/*.yml`) que corra tests en push → leer los comandos
   exactos de ahí y replicarlos localmente.
5. Nada de lo anterior → reportar "no configured gates found, proceeding
   without pre-push checks" y seguir sin bloquear.

Si un gate SÍ está configurado y falla → parar y reportar, no pushear. Nunca
exigir un check que no existe.

## Releases

- Nunca forzar push a branches compartidos. Nunca auto-mergear salvo pedido
  explícito.
- Esta sección **no** manda hacer un release en cada push. Los releases son
  **opt-in**, se disparan explícitamente vía `/ship`.

## Orquestación y ruteo de modelos

El chat es un **orquestador**, no el que codea todo inline. Su default en
trabajo de desarrollo es **delegar** la implementación pesada a subagentes y
quedarse con el planeo, la lectura del reporte y la decisión. Motivo: el
contexto de lectura/implementación del subagente **no ensucia el chat**
(ahorro de tokens), y cada tier corre en un modelo+effort ajustado a su costo.

Un hook (`orchestration-gate.js`) lo recuerda al tocar código; la regla vale
igual aunque el hook no dispare.

### Cuándo delegar (default de dev)

- **Feature nueva** → skill `/orch-add-feature`
- **Fix de bug** → skill `/orch-fix-defect`
- **Cambio de feature existente** → skill `/orch-change-feature`
- **Refactor sin cambiar comportamiento** → skill `/orch-refine-code`
- Reviews/tests puntuales → `Task` directo al subagente del tier.
- **Excepción**: si el cambio es chico/mecánico y delegar cuesta más de lo que
  ahorra, se hace inline. Criterio, no dogma.

### Tiers (modelo + effort, ya seteados en el frontmatter de cada agente)

| Tier | Modelo | Effort | Agentes | Racional |
|---|---|---|---|---|
| Worker | Haiku 4.5 | `medium` | build-error-resolver, e2e-runner | 73.3% SWE-bench, diseñado por Anthropic para subagentes en paralelo; 1/3 del costo de Sonnet |
| Worker-lite | Haiku 4.5 | `low` | doc-updater, refactor-cleaner | mecánico puro |
| Dev | Sonnet 5 | `high` | code/python/typescript/react/database-reviewer, tdd-guide, design-critic, code-architect | 85% SWE-bench a $2/$10, el workhorse |
| Deep | Opus 5.5 | `high` | planner, architect, security-reviewer | iguala a Fable 5.1 a −40% de costo; decisiones raras y caras |
| Apex | Fable 5.1 | `xhigh` | — invocado a mano | frontier top ($10/$50), solo para lo más brutal; nunca default |

El **chat** corre en Sonnet 5 / effort `high` (orquestador barato y capaz).

### Regla de precedencia de effort (no romper)

`modelSettings[modelo].effortLevel` **gana** sobre el `effort:` del frontmatter
del agente. Por eso **NO** se pinea `claude-sonnet-5` en `modelSettings`: así el
chat cae al `effortLevel` top-level (`high`) pero cada subagente Sonnet respeta
su `effort:` propio. Si algún día se pinea un modelo ahí, se clava el effort de
todos los subagentes de ese modelo — tenerlo presente antes de tocar
`modelSettings`.

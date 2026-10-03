---
description: "Stage and commit current changes — detects Conventional Commits vs Odoo mode (cached), respects local commitlint, shows diff, proposes message, waits for confirmation"
argument-hint: "[target description] (blank = all changes) [--recheck-mode]"
disable-model-invocation: true
---

# Commit

**Input**: $ARGUMENTS (parse out `--recheck-mode` as a flag; rest is the
target description)

## Pre-conditions

- Repo must have changes (`git status --short` non-empty). Empty → stop:
  "Nothing to commit."
- Git identity resolvable (`git config user.name` / `user.email`, global or
  local). Missing → stop: "No git identity configured. Check ~/.gitconfig."

---

## Phase 0 — DETECT MODE

Check `~/.claude/.cache/repo-modes.json` for this repo's absolute path.
Use the cached mode if present, `detected_at` is <30 days old, and
`--recheck-mode` was not passed.

**On cache miss or forced recheck:**

1. `find . -maxdepth 4 -name "__manifest__.py" -not -path "*/node_modules/*" -not -path "*/.venv/*" -not -path "*/venv/*" -not -path "*/.git/*" -not -path "*/dist/*" -not -path "*/build/*" 2>/dev/null`
2. For each match: `grep -l "'depends'" <file>`. Any match → mode = Odoo,
   marker = `manifest:<path>`. This marker is authoritative on its own —
   skip the org check entirely if it fires.
3. If no manifest found at all: check `git remote get-url origin` against
   `cashea-*` / `unifica-*` / `OCA-*`. Match → mode = Odoo, marker =
   `org:<pattern>`.
4. If a grep match is ambiguous (word appears but not as a real dict key),
   fall back to `python3 -c "import ast; ..."` to parse the manifest and
   confirm the `depends` key properly.
5. Nothing matches → mode = Conventional.

Write the result to `~/.claude/.cache/repo-modes.json` atomically. Never edit
the cache file in place — this protects against corruption when two Claude
Code sessions touch the same repo concurrently:

```bash
mkdir -p ~/.claude/.cache
[ -f ~/.claude/.cache/repo-modes.json ] || printf '{}' > ~/.claude/.cache/repo-modes.json
tmpfile=$(mktemp ~/.claude/.cache/repo-modes.json.XXXXXX)
jq --arg p "$repo_abs_path" --arg m "$mode" --arg t "$now_iso" --arg k "$marker" \
  '.[$p] = {mode: $m, detected_at: $t, marker: $k}' \
  ~/.claude/.cache/repo-modes.json >| "$tmpfile" && mv "$tmpfile" ~/.claude/.cache/repo-modes.json
# >| overrides zsh noclobber; mktemp pre-creates the file so a bare > would fail
```

**On cache miss only** (first time this repo is seen), also run:
```bash
git log -5 --format="%s"
```
Compare each subject against the Conventional pattern
(`^(feat|fix|docs|refactor|test|chore|perf|build|ci|revert)(\(.+\))?!?:`) and
the Odoo pattern (`^\[[A-Z]+\]`). If the detected mode doesn't match the
dominant style of these 5 commits, warn explicitly before continuing — this
usually means a mixed or mislabeled repo.

State the detected mode (and source: cache / manifest / org / mismatch
warning) to the user.

---

## Phase 0.5 — COMMITLINT LOCAL

Only in Conventional mode: check for `commitlint.config.js`, any
`.commitlintrc*`, or a `commitlint` key in `package.json`. If found, parse
`type-enum`, `scope-enum`, `header-max-length` and use those instead of the
global defaults for Phase 3. Announce in the final output which local rules
were applied.

---

## Phase 1 — ASSESS

```bash
git status --short
git diff
```

Show the full diff, not just the stat.

---

## Phase 2 — INTERPRET & STAGE

Interpret the (non-flag) part of `$ARGUMENTS` to determine what to stage:

| Input | Interpretation | Git Command |
|---|---|---|
| *(blank / empty)* | Stage everything | `git add -A` |
| `staged` | Use whatever is already staged | *(no git add)* |
| `*.ts` or `*.py` etc. | Stage matching glob | `git add '*.ts'` |
| `except tests` | Stage all, then unstage tests | `git add -A && git reset -- '**/*.test.*' '**/*.spec.*' '**/test_*' 2>/dev/null \|\| true` |
| `only new files` | Stage untracked files only | `git ls-files --others --exclude-standard \| xargs git add` |
| natural language (e.g. "the auth changes") | Cross-reference `git status`/`git diff` to find relevant files | `git add <matched files>` |
| specific filenames | Stage those files | `git add <files>` |

```bash
git add <determined files>
git diff --cached --stat
```

Nothing staged → stop: "No files matched your description."

---

## Phase 3 — PROPOSE MESSAGE

**Conventional mode** (or local commitlint override): `<type>(<scope>):
<subject>` — imperative, lowercase after prefix, no trailing period, ≤72
chars (or local `header-max-length`). Types: feat fix docs refactor test
chore perf build ci revert (unless commitlint restricts the list).

**Odoo mode**: `[TAG] module: description` — ≤50 chars, must complete "if
applied, this commit will <header>". Tags: FIX REF ADD REM REV MOV REL IMP
MERGE CLA I18N PERF CLN LINT.

Never mix modes. Never add Co-Authored-By, agent signatures, or emoji.

Show the proposed message and **wait for explicit OK** before committing.

---

## Phase 4 — COMMIT

```bash
git commit -m "<approved message>"
```

Never push from this command.

---

## Phase 5 — OUTPUT

```
Committed: {hash_short}
Mode:      {Conventional|Odoo} (source: {cache|manifest|org|recheck})
Local overrides: {commitlint rules applied, or "none"}
Message:   {message}
Files:     {count} file(s) changed

Next steps:
  - git push       → push to remote
  - /pr            → open a pull request
```

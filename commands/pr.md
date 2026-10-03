---
description: "Create a GitHub PR from current branch with unpushed commits — dual-convention aware (Conventional/Odoo) title, discovers templates, analyzes changes, pushes"
argument-hint: "[base-branch] (default: main) [--draft] [--recheck-mode]"
disable-model-invocation: true
---

# Create Pull Request

**Input**: `$ARGUMENTS` — optional base branch, `--draft`, `--recheck-mode`.

## Pre-conditions

- `gh` CLI installed and authenticated (`gh auth status`). Missing → stop
  with install/login instructions.
- Current branch ≠ base branch. If equal → stop: "Switch to a feature branch
  first."
- Remote configured and reachable (`git remote get-url origin`).
- No existing open PR for this branch (`gh pr list --head <branch>`). If one
  exists → stop and print its URL.

---

## Phase 0 — DETECT MODE

Check `~/.claude/.cache/repo-modes.json` for this repo's absolute path. Use
the cached mode if present, `detected_at` is <30 days old, and
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
the cache file in place — protects against corruption from concurrent Claude
Code sessions:

```bash
mkdir -p ~/.claude/.cache
[ -f ~/.claude/.cache/repo-modes.json ] || printf '{}' > ~/.claude/.cache/repo-modes.json
tmpfile=$(mktemp ~/.claude/.cache/repo-modes.json.XXXXXX)
jq --arg p "$repo_abs_path" --arg m "$mode" --arg t "$now_iso" --arg k "$marker" \
  '.[$p] = {mode: $m, detected_at: $t, marker: $k}' \
  ~/.claude/.cache/repo-modes.json >| "$tmpfile" && mv "$tmpfile" ~/.claude/.cache/repo-modes.json
# >| overrides zsh noclobber; mktemp pre-creates the file so a bare > would fail
```

This governs the **PR title format**:
- Mode Conventional → title = `type: description`
- Mode Odoo → title = `[TAG] module: description` (≤50 chars, "if applied..."
  test) — the repo's social convention outweighs GitHub's inability to parse
  `[TAG]` semantically.

The PR **body** format is homogeneous regardless of mode (see Phase 2).

---

## Phase 1 — VALIDATE

```bash
git branch --show-current
git status --short
git log origin/<base>..HEAD --oneline
```

Warn on uncommitted changes (suggest `/commit`). Stop if no commits ahead of
base.

---

## Phase 2 — DISCOVER

### PR Template

Search for PR template in order:

1. `.github/PULL_REQUEST_TEMPLATE/` directory — if exists, list files and let user choose (or use `default.md`)
2. `.github/PULL_REQUEST_TEMPLATE.md`
3. `.github/pull_request_template.md`
4. `docs/pull_request_template.md`

**If found**: strip any Claude branding, emoji-bot signatures, or
Co-Authored-By boilerplate before using it. Fill remaining sections from the
commit/diff analysis below. Preserve all other template sections — leave
sections as "N/A" if not applicable rather than removing them.

**If not found**, use:

```markdown
## Context

<why this change exists>

## Changes

<bulleted list of changes, grouped by area>

## Testing

<how it was tested, or "Needs testing">

## Screenshots

<only if UI changes — otherwise omit this section entirely>

## Notes

<anything else reviewers should know, or "None">
```

### Commit Analysis

```bash
git log origin/<base>..HEAD --format="%h %s" --reverse
```

Title, per detected mode:
- Conventional: derive from the dominant commit type in the range.
- Odoo: derive tag from the dominant tag in the range; module from the
  dominant module touched (or `various` if spread across modules).

### File Analysis

```bash
git diff origin/<base>..HEAD --stat
git diff origin/<base>..HEAD --name-only
```

Categorize changed files: source, tests, docs, config, migrations.

### Planning Artifacts

Check for related artifacts produced by `/plan-prd`, `/plan`, or the legacy PRP workflow:
- `.claude/prds/` — PRDs this PR implements a milestone of
- `.claude/plans/` — Plans executed by this PR
- `.claude/PRPs/prds/` — legacy PRP PRDs
- `.claude/PRPs/plans/` — legacy PRP implementation plans
- `.claude/PRPs/reports/` — legacy PRP implementation reports

Reference these in the PR body if they exist.

---

## Phase 3 — PUSH

```bash
git push -u origin HEAD
```

If push fails due to divergence:
```bash
git fetch origin
git rebase origin/<base>
git push -u origin HEAD
```

If rebase conflicts occur, stop and inform the user.

---

## Phase 4 — CREATE

```bash
gh pr create \
  --title "<PR title>" \
  --base <base-branch> \
  --body "<PR body>"
  # Add --draft if the --draft flag was parsed from $ARGUMENTS
```

---

## Phase 5 — VERIFY

```bash
gh pr view --json number,url,title,state,baseRefName,headRefName,additions,deletions,changedFiles
gh pr checks --json name,status,conclusion 2>/dev/null || true
```

---

## Phase 6 — OUTPUT

Report to user:

```
PR #<number>: <title>
Mode: {Conventional|Odoo}
URL: <url>
Branch: <head> → <base>
Changes: +<additions> -<deletions> across <changedFiles> files

CI Checks: <status summary or "pending" or "none configured">

Artifacts referenced:
  - <any PRDs/plans linked in PR body>

Next steps:
  - gh pr view <number> --web   → open in browser
  - /code-review <number>       → review the PR
  - gh pr merge <number>        → merge when ready
```

---

## Edge Cases

- **No `gh` CLI**: Stop with: "GitHub CLI (`gh`) is required. Install: <https://cli.github.com/>"
- **Not authenticated**: Stop with: "Run `gh auth login` first."
- **Force push needed**: If remote has diverged and rebase was done, use `git push --force-with-lease` (never `--force`).
- **Multiple PR templates**: If `.github/PULL_REQUEST_TEMPLATE/` has multiple files, list them and ask user to choose.
- **Large PR (>20 files)**: Warn about PR size. Suggest splitting if changes are logically separable.

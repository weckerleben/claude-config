---
description: "Full release ritual: verify gates, decide bump, update version files, update CHANGELOG (Keep a Changelog), commit, tag, push, publish GitHub Release — dual-convention aware"
argument-hint: "[major|minor|patch] (optional override) [--recheck-mode] [--allow-non-default]"
disable-model-invocation: true
---

# Ship a Release

**Input**: `$ARGUMENTS` — optional explicit bump override, `--recheck-mode`,
`--allow-non-default` (suppresses the default-branch pre-condition, nothing
else).

## Pre-conditions

- `origin` remote configured and reachable.
- Current branch must be the repo's default branch as configured on the
  remote (`gh repo view --json defaultBranchRef -q .defaultBranchRef.name`).
  If current branch differs → stop with: "You are shipping from '<current>'
  but the default branch is '<default>'. Pass --allow-non-default if this
  is intentional."
- Working tree clean (`git status --short` empty). Not clean → stop, point
  to `/commit`.
- At least one detectable version file exists (Phase 2 list). None found →
  stop: "No recognizable version file. Supported: package.json,
  manifest.config.ts, Cargo.toml, pyproject.toml, __init__.py,
  __manifest__.py, VERSION, version.txt, setup.py, setup.cfg. Tell me which
  file holds the version."
- `gh` CLI authenticated.

---

## Phase 0 — DETECT MODE

Check `~/.claude/.cache/repo-modes.json` for this repo's absolute path. Use
the cached mode if present, `detected_at` is <30 days old, and
`--recheck-mode` was not passed.

**On cache miss or forced recheck:**

1. `find . -maxdepth 4 -name "__manifest__.py" -not -path "*/node_modules/*" -not -path "*/.venv/*" -not -path "*/venv/*" -not -path "*/.git/*" -not -path "*/dist/*" -not -path "*/build/*" 2>/dev/null`
2. For each match: `grep -l "'depends'" <file>`. Any match → mode = Odoo,
   marker = `manifest:<path>`. Authoritative on its own — skip the org check
   if it fires.
3. If no manifest found at all: check `git remote get-url origin` against
   `cashea-*` / `unifica-*` / `OCA-*`. Match → mode = Odoo, marker =
   `org:<pattern>`.
4. Ambiguous grep match → fall back to `python3 -c "import ast; ..."` to
   confirm the `depends` key.
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

This governs the release commit message style and the version-bump
semantics (Phase 2).

---

## Phase 1 — GATES

Discover and run gates in this priority order (first that applies wins, no
combining):
1. `package.json` scripts `test`/`build`/`lint`.
2. `Makefile` targets `test`/`build`/`lint`.
3. `pyproject.toml` — `tox`, `pytest`, `ruff` config, or
   `[tool.poetry.scripts]`.
4. `.github/workflows/*.yml` that runs tests on push — read and replicate
   the exact commands.
5. None found → report "no configured gates found, proceeding without
   pre-push checks" and continue.

Any configured gate that fails → **stop**, do not proceed.

---

## Phase 2 — DIFF & BUMP DECISION

```bash
git describe --tags --abbrev=0 2>/dev/null || echo "(no previous tag)"
git log <last-tag>..HEAD --oneline
```

**Conventional mode**: infer bump from commits since last tag —
`!`/`BREAKING CHANGE:` → MAJOR, `feat` → MINOR, `fix`-only → PATCH.

**Odoo mode**: Odoo version format is
`<odoo-series>.<module-major>.<module-minor>.<module-patch>` (e.g.
`19.0.1.0.1`).
- The series segment (`19.0`) is **never** bumped by `/ship` — that's an
  Odoo version migration, a separate event.
- `/ship` only offers to bump the last 3 segments, applying normal SemVer
  semantics to that suffix (major/minor/patch of the module, not of Odoo).
- Version file: `__manifest__.py`, key `'version'`.
- No automatic inference from commit tags in Odoo mode — always ask the
  user directly which of the 3 module segments to bump, since Odoo commit
  tags (`[FIX]`/`[ADD]`/etc.) don't carry a SemVer-equivalent signal.

Detect version file candidates (report all found, use the first real match):
`package.json`, `manifest.config.ts`, `Cargo.toml`, `pyproject.toml`,
`__init__.py` (`__version__ = `), `__manifest__.py` (`'version': `), `VERSION`,
`version.txt`, `setup.py`, `setup.cfg`.

**Present the bump + justification + target file(s) to the user and wait for
explicit OK before touching anything.**

---

## Phase 3 — BUMP VERSION FILES

Update the detected version file(s) with the new version. Don't touch
unrelated fields.

---

## Phase 4 — CHANGELOG

Keep a Changelog 1.1.0 format, ISO 8601 dates, sections limited to `Added`,
`Changed`, `Deprecated`, `Removed`, `Fixed`, `Security` (only include ones
with actual entries). Create `CHANGELOG.md` with standard header +
`## [Unreleased]` if missing.

**If `[Unreleased]` already has entries**: move them into the new version's
section, dated today.

**If `[Unreleased]` is empty or absent**: generate the section from
`git log <last-tag>..HEAD`, mapping:

Conventional mode:
- `feat` → Added
- `fix` → Fixed
- `refactor`, `perf`, behavior-changing `chore` → Changed
- `revert` → Changed (annotated as a revert)
- `docs`, `test`, `chore` (non-behavior), `ci`, `build` → omit (noise for
  end users)

Odoo mode:
- `[FIX]` → Fixed
- `[ADD]` → Added
- `[IMP]`, `[REF]`, `[PERF]` → Changed
- `[REM]` → Removed
- `[REV]` → Changed (annotated as a revert)
- Rest (`[CLA]`, `[I18N]`, `[CLN]`, `[LINT]`, `[MERGE]`, `[MOV]`) → omit

**Present the generated draft to the user and wait for confirmation/edits
before writing to CHANGELOG.md.** This is a draft, not an autonomous decision
about what's user-facing.

Update/add comparison links at the bottom of the file.

---

## Phase 5 — COMMIT

**Conventional mode**: `chore(release): vX.Y.Z`

**Odoo mode**:
- If the bump touched a single `__manifest__.py` → `[REL] <that-module>:
  bump to X.Y.Z`
- If it touched multiple modules → `[REL] various: bump modules to X.Y.Z`
  (per Odoo's own convention for multi-module commits)

```bash
git add <version files> CHANGELOG.md
git commit -m "<message above>"
```

---

## Phase 6 — PUSH

```bash
git push origin <default-branch>
```

---

## Phase 7 — TAG

```bash
git tag -s vX.Y.Z --cleanup=verbatim -m "<changelog section for this version, as plain text>"
# -s: sign the tag with the configured SSH signing key — commits are signed,
#   so release tags must not be the unsigned gap in the chain
# --cleanup=verbatim: markdown headers in the tag message would otherwise be
#   stripped by git's default `strip` cleanup mode
git push origin vX.Y.Z
```

---

## Phase 8 — GITHUB RELEASE

Check for a tag-triggered workflow: `.github/workflows/*.yml` with
`on: push: tags:`. If found, grep its content for markers that indicate CI
itself creates the GitHub Release:

- `gh release create`
- `softprops/action-gh-release`
- `actions/create-release`
- `ncipollo/release-action`

**If any marker matches**: CI creates the Release. `/ship` only pushes the
tag (already done in Phase 7) and reports that CI is handling it — no
duplicate `gh release create`.

**If no marker matches** (e.g. the workflow only builds/publishes to a
package registry, like a PyPI trusted-publish workflow): `/ship` creates the
Release itself:

```bash
gh release create vX.Y.Z --title "vX.Y.Z" --notes-file <file-with-changelog-section>
# the notes file is used verbatim; trailing whitespace is preserved to avoid
#   ambiguity when the changelog section ends in a code block
```

Attach build assets **only** if the repo already has an established local
artifact convention in its release history (e.g. `gh release view --json
assets` on the previous tag shows a `<name>-v*.zip` pattern). Never invent a
new packaging convention. If it's ambiguous whether an asset should be
attached, ask before zipping anything.

---

## Phase 9 — OUTPUT

```
Released vX.Y.Z
Mode: {Conventional|Odoo}

Commit: <url>
Tag:    <url>
Release: <url or "handled by CI: <workflow-name>">
```

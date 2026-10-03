# Install and bootstrap

## What is on disk

```
~/.claude/skills/
├── spec-flow/
│   ├── SKILL.md                       the chain, the contract, the sync matrix
│   ├── scripts/repo-profile.sh        resolves the repo's stack, axis, components
│   ├── hooks/spec-trace-guard.js      warns about stale downstream artifacts
│   └── references/
│       ├── repo-profile.md            profile schema, inference, where skills live
│       ├── worked-example.md          Core Ledger BNPL, end to end
│       └── install.md                 this file
├── rfc-author/
│   ├── SKILL.md
│   └── templates/rfc.md
└── adr-author/
    ├── SKILL.md
    ├── templates/adr-madr.md
    ├── templates/adr-y-statement.md
    └── scripts/adr-index.sh
```

Nothing else was modified. `/plan-prd`, `/plan`, `settings.json` and the ECC
install are untouched.

## Bootstrap a repo

```bash
bash ~/.claude/skills/spec-flow/scripts/repo-profile.sh          # see what it infers
mkdir -p docs/rfc docs/adr .claude/prds .claude/plans
$EDITOR .claude/spec-flow.yml                                    # declare what inference got wrong
bash ~/.claude/skills/adr-author/scripts/adr-index.sh
git add docs/ .claude/spec-flow.yml
git commit -m "docs: bootstrap spec-flow chain"
```

`docs/adr/README.md` is generated. Add nothing by hand to it.

The profile is optional — inference covers the common case — but declare it in
any repo with a variant axis or sibling repos, because neither survives guessing.
Schema in `repo-profile.md`.

## Enabling the trace guard (optional, your call)

The hook is written but **not wired** — enabling it changes how every Write and
Edit behaves, so it is a deliberate step. To turn it on, add to
`~/.claude/settings.json` under `hooks`:

```json
"PostToolUse": [
  {
    "matcher": "Write|Edit|MultiEdit",
    "hooks": [
      {
        "type": "command",
        "command": "node /Users/weckerleben/.claude/skills/spec-flow/hooks/spec-trace-guard.js"
      }
    ]
  }
]
```

Levels, via env:

| `SPEC_TRACE_GUARD` | Behavior |
|---|---|
| unset / `feedback` | exit 2 — the message goes back to Claude, which acts on it |
| `warn` | exit 0 — transcript only, Claude is not interrupted |
| `off` | no-op |

Start on `warn` for a week. If the messages turn out to be noise rather than
signal, that is data about the chain, not about the hook — it usually means the
artifacts are not actually cross-referenced.

The hook only fires on `*.prd.md`, `docs/rfc/RFC-NNNN-*.md` and
`docs/adr/ADR-NNNN-*.md`. Every other file exits 0 immediately.

## Sharing

The three skill directories are self-contained — no ECC dependency, no plugin
manifest, no network calls. Copy them into a skills repo or a plugin's
`skills/` directory as they are.

Nothing stack-specific is baked into them any more. The Jira project, the field
ids, the Odoo v16/v19 axis and the component lists all come from each repo's
profile; the skills only carry them as **worked instances**, clearly labelled,
so the mechanics stay readable.

Everything in the skills themselves — MADR 4.0.0, EARS, the non-goals rule, the
options table, the supersede lifecycle, the change-propagation matrix, the
profile schema — is portable as-is.

### Two kinds of skill, two homes

**Domain skills go per repo.** `odoo-incident-rca` in `cashea-odoo/.claude/skills/`,
`odoo-postgres-tuning` in `cashea/.claude/skills/`. They only mean something
there, they should travel with the repo and be reviewed in its PRs. This pattern
already works; keep it.

**Process skills stay one copy.** These three are ~95% identical wherever they
run — only the profile differs. Eight copies means eight silent drifts, because
nobody diffs skill files across repos.

Today the copy lives at `~/.claude/skills/`, which works with zero setup. When
the team needs it, the same three directories move into a plugin repo installed
through a marketplace — the mechanism already in use for ECC — and **nothing
inside them changes**, because by then they read the repo instead of assuming
it. The distribution decision costs nothing to defer; making them
context-driven was the part that did not.

## What was deliberately not built

| Not built | Why |
|---|---|
| A PRD skill | `/plan-prd` is good and already writes the artifact `/plan` consumes. It needed a requirements contract (EARS), not a replacement. |
| An implementation skill | `/plan`, `/prp-implement`, `/orch-*`, `tdd-guide` and `ralphinho-rfc-pipeline` already cover execution. The gap was that the plan did not read ADR constraints — solved by the `constraints_from_adr` field, not by a new skill. |
| Adoption of Spec Kit or OpenSpec | Both **replace** the `/plan-prd → /plan → /prp-implement` chain rather than complementing it, and would orphan the ECC install. That is a process architecture decision; if it is ever taken, it deserves its own ADR. |
| A generic ADR template skill | The format is solved. MADR 4.0.0 is adopted verbatim; what was missing was lifecycle, numbering, the index and the component/variant axis. |
| A copy of the skills per repo | Same logic eight times drifts silently. One copy plus a per-repo profile gives the same behaviour with one thing to maintain. |
| `odoo-workflows` as the shared home | It is named for one stack — the thing being escaped — and today holds only a README and a CODEOWNERS. |

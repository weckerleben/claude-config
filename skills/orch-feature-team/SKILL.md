---
name: orch-feature-team
description: Layered feature pipeline that dispatches parallel implementation lanes (database, backend, frontend) instead of a single implementer, then joins them through a mandatory real-browser E2E pass and a review gate. Use when a feature spans more than one layer, when the user asks for "the whole team", or when frontend work must be verified in a real browser rather than assumed. For single-layer work use orch-add-feature instead.
---

# Orchestrated Feature Team

`orch-pipeline` runs one implementer (`tdd-guide`) across every layer, in series,
and never reaches a browser. This skill replaces its Implement phase with
**parallel per-layer lanes** and adds two phases that the base pipeline omits
entirely: a real-browser E2E pass and a wired-in database review.

Everything else — the size classifier, the two human gates, the security
trigger — is inherited from `orch-pipeline`. Do not re-implement it.

## Agent name resolution

Every agent below the orchestrator ships with the ECC plugin and resolves **only
under the `ecc:` prefix** — `ecc:tdd-guide`, `ecc:database-reviewer`,
`ecc:code-reviewer`, `ecc:security-reviewer`, `ecc:e2e-runner`. The bare names
used elsewhere in ECC prose no longer resolve. `design-critic` is user-level and
is always bare, with no prefix.

## Step 0 — Classify and pick lanes

Run the `orch-pipeline` size classifier first. Then declare which lanes open,
in one line the user can override:

| Lane | Opens when the change touches |
|------|-------------------------------|
| **DB** | schema, migrations, indexes, queries, RLS, Odoo models/ORM |
| **Backend** | API routes, services, business logic, jobs, RPC |
| **Frontend** | any HTML/JSX/TSX/Vue/CSS/component/dashboard |

A `trivial` or `small` tier opens **one** lane and runs the base
`orch-add-feature` instead. Lanes are for `standard` and `large`.

## Phase 1 — Research & Reuse

Per `rules/common/development-workflow.md`: `gh search repos` / `gh search code`
first, then Context7 / vendor docs, then package registries, then Exa. Prefer
porting a proven implementation over net-new code.

## Phase 2 — Plan and cut the contract

Delegate to `planner` (or `architect` / `code-architect` for structural calls).

Before any lane opens, write down two things — this is what makes parallelism
safe rather than a merge disaster:

1. **The interface contract.** The exact types, endpoint shapes, and payloads
   the lanes exchange. Frontend codes against it; backend implements it; DB
   backs it. It does not change mid-flight without reconvening.
2. **Disjoint file ownership.** Each lane gets an explicit file/directory list.
   Two lanes must never own the same file. Anything shared (types, schema
   definitions) is written **once, before the lanes open**, by the orchestrator.

→ **GATE 1.** Present the plan, the contract, and the lane/file split. Do not
write implementation code until the user approves.

## Phase 3 — Parallel lanes

Dispatch the open lanes in a single message so they run concurrently. Each lane
is TDD — tests first, per `rules/common/testing.md` (80% minimum).

### DB lane
1. `tdd-guide` — migration + query tests first, then implementation.
2. `database-reviewer` — **mandatory close-out**, never optional. Indexes,
   N+1, unbounded queries, RLS, migration reversibility.
   *(The base pipeline never calls this agent. That is the gap this lane closes.)*

### Backend lane
1. `tdd-guide` — unit + integration tests first, then implementation.
2. Language reviewer matched to the repo (`python-reviewer`,
   `typescript-reviewer`, `django-reviewer`, `fastapi-reviewer`, …).
3. `silent-failure-hunter` when the diff adds error handling, fallbacks, or
   try/except blocks.

### Frontend lane
Governed by the **UI/UX gate** in the global `CLAUDE.md` — non-negotiable:

1. **Design pass before code.** Load `make-interfaces-feel-better` and/or
   `frontend-design-direction`, plus `rules/ecc/web/design-quality.md`. State
   the style direction, the visual hierarchy (what commands, what subordinates),
   and the **context fit**: read what sits above/below/beside this element in
   the same view and justify that it belongs there. Never judge the piece alone.
2. `tdd-guide` — component tests first (React Testing Library / equivalent).
3. `design-critic` — **mandatory close-out**. Its first move is mapping the
   surface and its neighbours, then critiquing fit. Apply what lands before the
   lane closes. No frontend closes without it.

## Phase 4 — Join

Orchestrator only, no agent:
- Wire the lanes together against the Phase 2 contract.
- Run the full test suite. **Zero-warning policy** (global `CLAUDE.md`): warnings
  are blocking, fix the root cause, never suppress. Re-run to confirm clean.
- Build must be green. On failure: `build-error-resolver` / `/build-fix`.

## Phase 5 — Real browser E2E

**Mandatory whenever the Frontend lane opened.** The base pipeline has no
browser phase at all; assuming the UI works is how it ships broken.

1. `e2e-runner` — generate or update the critical-path journey.
2. Drive the app in an actual browser via the Browser pane
   (`preview_start` → `navigate` → `read_page` / screenshot) or the
   `chrome-devtools` MCP.
3. Verify, with evidence, not assumption:
   - the happy path completes end to end
   - **zero console errors** (`read_console_messages`)
   - no failed network requests (`read_network_requests`)
   - responsive at 375 / 768 / 1440 (`resize_window`)
   - both themes if the app has them
4. Report what was actually observed. A screenshot or a console dump — never
   "it should work".

## Phase 6 — Review

- `code-reviewer` across the joined diff (`/code-review`).
- `security-reviewer` **iff** the diff touches a security trigger: auth/authz,
  user input, database queries, filesystem paths, external API calls, crypto,
  or secrets. Per `rules/common/security.md`.
- CRITICAL and HIGH findings are resolved before Gate 2. No exceptions.

## Phase 7 — Commit

→ **GATE 2.** Present the diff summary and the proposed messages. Do not commit
until the user confirms.

Detect the repo's commit convention per the global `CLAUDE.md` dual policy
(`__manifest__.py` with a top-level `depends` ⇒ Odoo mode `[TAG] module: desc`;
otherwise Conventional; a local commitlint config always wins). Never mix the
two styles in one repo. **Never** add Claude attribution, co-author trailers, or
robot emoji — not in commits, PR bodies, tags, or release notes.

All code artifacts in English. Conversation with William in Paraguayan Spanish.

## Verification

- size tier and open lanes were stated up front
- interface contract and disjoint file ownership were written before lanes opened
- Gate 1 and Gate 2 were both honored
- `database-reviewer` ran iff the DB lane opened
- `design-critic` ran iff the Frontend lane opened
- Phase 5 ran in a real browser with observed evidence iff the Frontend lane opened
- `security-reviewer` ran iff a security trigger was touched
- test suite green, coverage ≥ 80%, zero warnings

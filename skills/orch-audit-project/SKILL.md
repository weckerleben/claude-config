---
name: orch-audit-project
description: Read-only audit of a finished or shipped project. Dispatches parallel review lanes (security, data, correctness, tests, frontend), verifies the app in a real browser, then consolidates every finding into one deduplicated severity-ranked report. Use when the user wants a whole project verified, audited, reviewed before launch, or asks "what breaks in prod?" — not for reviewing a diff (/code-review) and not for building anything (orch-feature-team).
---

# Orchestrated Project Audit

The read-only twin of `orch-feature-team`. That pipeline builds; this one judges
what already exists and writes nothing.

`/code-review` scopes to a diff. `production-audit` is a prose checklist that
delegates to no one. This skill dispatches the actual review agents in parallel
and merges their output into a single ranked report.

## Read-only is enforced, not assumed

Parallel lanes are trivially safe here — no lane writes, so there is no file
contention and no interface contract to negotiate. That safety depends on one
rule being honored:

> **Every lane is REPORT ONLY. No agent edits, fixes, refactors, or creates
> files — including test files. Findings are described, never applied.**

State that constraint verbatim in each agent prompt, because five of these
agents *can* write: `ecc:security-reviewer`, `ecc:database-reviewer`,
`ecc:performance-optimizer`, `ecc:a11y-architect`, `ecc:e2e-runner`. An agent
that "helpfully" fixes something mid-audit contaminates the very artifact under
evaluation. If the user wants fixes, that is a second pass after the report.

Agents resolve under the `ecc:` prefix. `design-critic` is user-level and bare.

## Phase 0 — Recon (orchestrator, no agent)

Before dispatching anything, establish the surface — a lane aimed at the wrong
target wastes the whole pass:

- Stack, frameworks, package manager, entry points.
- Does it have a UI? a database? auth? payments? background jobs? external APIs?
- Test setup and whether the suite currently passes. CI config and its state.
- Size: file count, rough LOC, module boundaries.
- Git state: branch, last release tag, uncommitted work.

Announce which lanes open and why. The user can override before any agent runs.

## Phase 1 — Parallel review lanes

Dispatch every applicable lane **in a single message** so they run concurrently.
Each prompt carries: the REPORT ONLY rule, the recon summary, and the scope.

| Lane | Opens when | Agents |
|------|-----------|--------|
| **Security** | always | `ecc:security-reviewer` |
| **Data** | a database, ORM, or migrations exist | `ecc:database-reviewer` |
| **Correctness** | always | `ecc:code-reviewer` + `ecc:silent-failure-hunter` + the language reviewer for the stack |
| **Tests** | always | `ecc:pr-test-analyzer` |
| **Frontend** | a UI exists | `design-critic` + `ecc:a11y-architect` |
| **Performance** | the user asks, or recon found obvious hot paths | `ecc:performance-optimizer` |

Language reviewer by stack: `ecc:python-reviewer`, `ecc:typescript-reviewer`,
`ecc:react-reviewer`, `ecc:django-reviewer`, `ecc:fastapi-reviewer`,
`ecc:vue-reviewer`, `ecc:go-reviewer`, `ecc:rust-reviewer`.

Two commands complement the lanes and are run by the orchestrator, not an agent:

- `/test-coverage` — actual coverage numbers against the 80% floor.
- `/security-scan` — **only if the project is itself an agent harness.** It
  audits agent/hook/MCP/permission/secret surfaces, not application code. On a
  normal web app it answers the wrong question; skip it and say so.

## Phase 2 — Real browser verification

Runs whenever the Frontend lane opened. A static read of the code cannot tell
you the app is broken at runtime.

1. Start the app (`preview_start`; check `preview_logs` for boot failures).
2. Walk the critical paths in an actual browser.
3. Capture as evidence, not impression:
   - console errors and warnings (`read_console_messages`)
   - failed or slow network requests (`read_network_requests`)
   - 375 / 768 / 1440 (`resize_window`) — overflow, overlap, blocked submits
   - both themes if the app has them
4. If the app will not start, that is a **CRITICAL** finding on its own. Report
   it and continue with static lanes.

## Phase 3 — Consolidate

The lanes overlap on purpose; the merge is where the value is.

1. **Deduplicate.** The same SQL injection will surface in Security *and* Data.
   One finding, noting that two lanes flagged it — convergence raises
   confidence, it does not multiply severity.
2. **Cross-check.** A finding no other lane corroborates and that you cannot
   confirm in the source is marked *unverified*. Do not launder a guess into
   the report by giving it a severity.
3. **Rank** per `rules/common/code-review.md`:

   | Level | Meaning |
   |-------|---------|
   | CRITICAL | security hole or data-loss risk — blocks release |
   | HIGH | real bug or significant quality issue |
   | MEDIUM | maintainability concern |
   | LOW | style or minor suggestion |

4. **Anchor everything.** Every finding cites `file:line` and states a concrete
   failure scenario: the input or state, and the wrong output or crash. A
   finding without a reachable path is an observation, not a defect — label it
   as such.

## Phase 4 — Report

Deliver in this order:

1. **Verdict** — ship / ship with caveats / block, in one sentence.
2. **Counts** by severity.
3. **CRITICAL and HIGH** in full: what, where, failure scenario, suggested fix.
4. **MEDIUM and LOW** condensed to one line each.
5. **What was verified** — lanes that ran, browser evidence observed, coverage
   number. Name what was *not* covered too; an audit that hides its blind spots
   is worse than none.

Offer the report as an Artifact — it is a document the user will hand to others.
Ask before publishing; do not publish automatically.

Then stop. Fixing is a separate pass the user asks for explicitly — and when
they do, route it through `orch-feature-team` or `/orch-fix-defect`, not here.

## Verification

- recon ran and the open lanes were announced before any agent was dispatched
- every lane prompt carried the REPORT ONLY rule verbatim
- the working tree is unchanged: `git status` is identical to before the audit
- `/security-scan` was run only for an agent-harness project
- browser evidence is observed output, never assumption
- duplicate findings were merged; uncorroborated ones marked unverified
- every finding cites file:line and a concrete failure scenario
- blind spots are named in the report

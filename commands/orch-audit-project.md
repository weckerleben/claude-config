---
description: "Read-only audit of a finished project — parallel review lanes (security, data, correctness, tests, frontend), real-browser verification, one consolidated severity-ranked report"
argument-hint: "[path or scope] [--lanes security,data,correctness,tests,frontend,performance] [--no-browser]"
---

# /orch-audit-project

Runs the `orch-audit-project` skill: the read-only twin of `/orch-feature-team`.

Use it to judge a project that already exists. It writes nothing — not even
test files.

**Input**: `$ARGUMENTS` — optional path/scope to narrow the audit, plus flags.

## When to use which

| Situation | Use |
|-----------|-----|
| Verify a whole finished project | **this** |
| Review the current diff or a PR | `/code-review` |
| Build a multi-layer feature | `/orch-feature-team` |
| Fix something this audit found | `/orch-fix-defect` |

## Flags

- `--lanes …` — force the lane set instead of inferring it from recon.
- `--no-browser` — skip Phase 2. Say why; a UI audited without running it is
  a code read, not a verification, and the report must state that.

## What it does

```
Recon: stack, surfaces, tests, CI, git state → announce lanes
  ├── Security     : ecc:security-reviewer
  ├── Data         : ecc:database-reviewer
  ├── Correctness  : ecc:code-reviewer + ecc:silent-failure-hunter + language reviewer
  ├── Tests        : ecc:pr-test-analyzer  (+ /test-coverage)
  ├── Frontend     : design-critic + ecc:a11y-architect
  └── Performance  : ecc:performance-optimizer   (on request)
       └─ Real browser: console, network, 375/768/1440, themes
           └─ Consolidate: dedup, cross-check, rank CRITICAL→LOW, anchor file:line
               └─ Report: verdict, findings, what was verified, blind spots
```

## Hard constraints

- **REPORT ONLY.** Five of these agents can write (`ecc:security-reviewer`,
  `ecc:database-reviewer`, `ecc:performance-optimizer`, `ecc:a11y-architect`,
  `ecc:e2e-runner`). Every lane prompt must carry the no-edit rule verbatim.
- `git status` must be identical before and after. Verify it and say so.
- Fixing is a separate pass the user requests explicitly. Do not drift into it.

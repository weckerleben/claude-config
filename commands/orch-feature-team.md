---
description: "Orchestrate a multi-layer feature with parallel lanes (DB / backend / frontend), mandatory real-browser E2E, database and design review, and two human gates"
argument-hint: "<feature description> [--lanes db,backend,frontend] [--no-e2e]"
---

# /orch-feature-team

Runs the `orch-feature-team` skill: the layered variant of the ECC orchestrator.

Use this instead of `/orch-add-feature` when the work spans more than one layer,
or when frontend changes must be verified in a real browser rather than assumed.

**Input**: `$ARGUMENTS` — the feature description, plus optional flags.

## Flags

- `--lanes db,backend,frontend` — force the lane set instead of inferring it.
- `--no-e2e` — skip Phase 5. Requires an explicit reason stated back to the user;
  it is the one guardrail this pipeline exists to add, so do not skip it quietly.

## What it does

```
Intake + size classify
  └─ Research & Reuse
      └─ Plan + interface contract + disjoint file ownership   → GATE 1
          ├── DB lane        : tdd-guide → database-reviewer
          ├── Backend lane   : tdd-guide → language-reviewer → silent-failure-hunter
          └── Frontend lane  : design pass → tdd-guide → design-critic
                └─ Join: full suite green, zero warnings, build green
                    └─ Phase 5: real browser E2E (console + network + responsive)
                        └─ code-reviewer (+ security-reviewer on trigger)
                            └─ GATE 2 → commit (dual-convention, no Claude branding)
```

## Preconditions

- A git repository. If not, stop and offer `git init`.
- Lanes must own disjoint files. If the plan cannot split them cleanly, say so
  and fall back to serial `/orch-add-feature` rather than racing two lanes on
  the same file.

## Execution

Invoke the `orch-feature-team` skill and follow it end to end. Honor both gates:
never write implementation code before Gate 1 approval, never commit before
Gate 2 confirmation.

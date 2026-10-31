---
name: orch-product-design
description: Single entry point to design or redesign a whole product's UI, UX and brand together - one intake, one shared strategy, then UX structure (orch-ux-design) and visual identity (orch-brand-system) in the right order, joined into high-fidelity screens in Figma, critiqued, validated with real people, and locked into one binding contract that implementation must obey. Handles a new product, an existing app with an identity to evolve, and an existing app that was never designed and gets reinvented from scratch. Use for "disenar la app completa", "UI UX y marca todo junto", "redisenar todo de cero", "que no improvise el diseno al desarrollar". Not for a single concern (use orch-ux-design or orch-brand-system) and not for building features (orch-feature-team).
---

# Orchestrated Product Design

Thin conductor. The method lives in two skills; this one owns only what neither
can: the **single intake**, the **order and the join**, the **combined gates** and
the **one contract**. Do not copy their phases here: invoke them and follow them.

- `orch-ux-design` - what people can do, in what order, where things live.
- `orch-brand-system` - how it looks, sounds and moves; one `brand/DESIGN.md`
  (Google DESIGN.md format) as the single token source; Figma library.

Their method comes from audited upstream playbooks pinned under
`~/.claude/vendor/` (`intent` for UX; `impeccable` playbooks, the DESIGN.md spec
and CLI wrapper, and brand checklists for the visual side). Each folder has an
`UPSTREAM.md` with origin, commit, license and audit verdict; read it before
using a piece. Nothing in `vendor/` is installed as a global skill and no
upstream script or binary is run. Anything missing from there gets the global
"Investigar y auditar antes de construir" treatment before being built.

## Autonomous mode (DEFAULT, William's rule 2026-10-31)

The user supplies **only the app context** (name, what it does, repo path, URL,
users if known). Everything else is decided by the agents: mode, depth, strategy,
top tasks, IA, brand direction, palette, type, icons, motion, copy, contract.
Never ask the user to choose, approve or confirm a design decision.

- Every "GATE" below becomes a **self-gate**: an independent judge (a fresh
  `general-purpose` agent, `design-critic`, or `ecc:a11y-architect`, never the
  agent that produced the work) scores the artifact against the criteria of that
  gate. Pass -> continue. Fail -> fix and re-judge, max 3 rounds, then continue
  with the best version and log the open issue.
- Where a skill says "the user picks / approves / answers", the agent picks the
  option that best fits the strategy and writes the choice and the rejected
  alternatives with reasons in `DECISIONS.md` (repo root, append-only: date, phase,
  decision, why, alternatives, confidence).
- Missing facts are inferred from the repo, the running app (Claude in Chrome)
  and the web; an inference is logged as an assumption, not asked.
- Ask the user ONLY for what no agent can do or obtain: logins/2FA, paid or
  outward-facing actions, real-human validation sessions, and facts that exist
  only in their head and cannot be inferred (then ask once, batched, and proceed
  on the best assumption if unanswered).
- Commit/push stays under the repo's own rules; the design contract is written to
  the project `CLAUDE.md` without waiting for approval, in a branch/path that does
  not touch production when told so (e.g. everything under `/v2`).
- When another chat is implementing, answer its design questions yourself by
  amending the spec first (DESIGN.md / SPEC.md), then replying with the file.

Run the sub-skills' agent work as described there, with the same autonomy rule.

## What AI can and cannot do here (state it once, at Step 0)

It can produce a coherent, accessible, well-argued system and exhaustive flows
and states. It cannot measure real emotional response, market fit or usability
with real users. Emotional and persona claims stay labeled hypotheses and the
run ends with one human validation session (Phase 6). Logos from image models are
exploration only.

## Step 0 - One intake, one mode

Do not interview. Read what the user gave, then fill every gap yourself from the
repo, the live app and the web; log assumptions in `DECISIONS.md`. Decide:
1. The product, users, platforms, languages (inferred, logged).
2. **Mode** (the agent decides: no brand/design artifacts found -> blank-slate;
   real visual history -> brownfield-with-identity; no app -> greenfield):
   - `greenfield` - nothing built. Run both skills as written.
   - `brownfield-with-identity` - an app exists and has real brand/visual
     history worth keeping. `orch-brand-system` brownfield mode (evolve by
     default); `orch-ux-design` brownfield.
   - `brownfield-blank-slate` - an app exists but was never designed (no brand,
     no UI/UX work) and a full redo is allowed. Everything is `replace`; keep only
     the capability inventory and real user workflows.
3. Depth, decided by the agent: **lite** (3 top tasks, 4 brand modules) when the
   app has up to about 10 distinct screens, **full** above that.
4. Repo path, running URL (given or found), Figma account (checked with `whoami`
   before any write; skip Figma and log it if no write access).

Write `design-state.json` at the repo root: `{runId, mode, depth, phase,
gatesPassed[], chosenDirection, topTasks[], figmaFileKey, lastUpdated}`. On every
activation read it first and report where the run stands in two sentences.

## Order

```
0 Intake
1 Shared strategy        -> GATE A
2 Baseline (brownfield)  (once, shared)
3 UX structure           -> GATE B
4 Brand identity         -> GATE C
5 Join: high-fi screens  -> GATE D
6 Critique + human test
7 One contract           -> GATE E
```

### 1 - Shared strategy (once)
Run `brand-discovery` at the chosen depth a single time. Its synthesis feeds both
skills: audience and positioning drive the UX, personality and tone drive the
brand. Tell each skill to reuse it and skip its own strategy phase. Optional
`product-lens` when the user is unsure the product should exist.
**GATE A:** user approves the synthesis.

### 2 - Baseline (brownfield only, once)
One pass instead of two: crawl the running app, screenshots at 375 / 768 / 1440,
capability inventory, heuristic evaluation, accessibility baseline, drift counts
(hardcoded values). It satisfies `orch-brand-system` B1 and `orch-ux-design`
Phase 0 together. Blank-slate: keep the capability inventory, the real workflows
and the "before" evidence; drop any preserve-the-old logic.

### 3 - UX structure
Run `orch-ux-design` Phases 1 to 5 (users and jobs, IA, flows, grayscale
wireframes with the state inventory, interaction rules, microcopy).
**GATE B:** user walks the top tasks on the wireframes and approves structure.
Nothing visual is skinned before this.

### 4 - Brand identity
Run `orch-brand-system` from Phase 2 (feeling brief, three directions, identity
assets, tokens, motion). Feed it the **component inventory** from the UX track so
the design system covers the components the screens actually need. The three
direction previews should use the approved wireframe screens, not invented ones,
so the user judges identity on real structure.
**GATE C:** user picks a direction.

Tracks 3 and 4 touch disjoint folders (`ux/`, `brand/`), so their agent work may
overlap in time after Gate A. The user-facing gates stay sequential.

### 5 - Join: high-fidelity screens
Apply the approved tokens to the approved wireframes. In Figma, follow
`orch-brand-system` Phase 6 (library from the `dtcg` export of `brand/DESIGN.md`, code-first) and
then `figma-generate-design`: one screen per top-task step, **every state from the
state inventory**, both themes, desktop and mobile, bound to variables, no hardcoded
values. Read `figma-use` before every `use_figma` call; calls strictly
sequential; ledger on disk; skip Figma and say why if `whoami` shows no write
access. Build the same screens as a coded HTML preview when Figma is out of reach.
**GATE D:** user approves the hi-fi set.

### 6 - Critique and human validation
Independent passes on the hi-fi, not by the agent that made them: `design-critic`
(surface and neighbors first), `orch-brand-system` Phase 7 (slop-check,
`ecc:a11y-architect`, browser screenshots at three widths, clean console), and
`orch-ux-design` Phase 6 (heuristic evaluation, cognitive walkthrough). Fix
severity 3 and 4.
Then ONE human session, about 5 real people from the audience, covering both
tracks: the usability tasks from `ux/09-test-plan.md` plus the 5-second recall
and preference questions from the brand validation checkpoint. Hand the combined
script to the user. Record `validation: pending|done`; if results contradict the
feeling brief or the task metrics, return to the phase that owns the failure.

### 7 - One contract
1. Merge into a single block in the project `CLAUDE.md`: the Design contract from
   `orch-brand-system` Phase 8 and the UX contract from `orch-ux-design` Phase 8,
   without duplicating lines. Precedence rule: if the spec and an improvisation
   conflict, the spec wins and gaps are escalated to the user.
2. Mechanical enforcement: the token lint check (with a ratchet baseline in
   brownfield) and a per-flow acceptance check in a real browser.
3. Implementation hand-off, ordered by top-task criticality, one flow per unit:
   - greenfield: `orch-feature-team` per flow;
   - brownfield: `orch-change-feature` for screens whose layout or flow changes,
     `orch-refine-code` for pure token adoption with no layout change.
   Business logic is out of scope here; anything that would change it is
   reported, not fixed.
**GATE E:** present the artifact list, validation status and the contract text.
Commit only after confirmation, in the repo's commit convention, no Claude
attribution.

## Verification (the run is done when all are true)

- Mode and depth declared at Step 0; AI limits stated once.
- Gates A to E each passed by an independent judge, in order, logged in `DECISIONS.md`.
- Strategy ran once and fed both tracks; baseline ran once (brownfield).
- UX structure was approved in grayscale before any identity was applied.
- Hi-fi screens cover every state in the state inventory, in both themes and sizes.
- Independent critique ran and no severity 3 or 4 finding is open unexplained.
- `validation:` is stated honestly; a combined human test script was delivered.
- One merged contract is in the project `CLAUDE.md` with a mechanical check.
- Hand-off is ordered and routed; this skill did not rewrite application code.

Conversation with William in Paraguayan Spanish. All artifacts in English except
product microcopy. Free tiers first; flag anything that costs money before using it.

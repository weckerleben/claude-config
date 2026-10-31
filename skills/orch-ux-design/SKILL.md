---
name: orch-ux-design
description: Orchestrates product UX end to end - users and jobs-to-be-done, top tasks, information architecture, user flows, grayscale wireframes with every state, interaction rules, microcopy, heuristic evaluation, accessibility, prototype and a usability test plan - for a NEW product (greenfield) or an EXISTING app that was never designed and must be re-derived and rebuilt (brownfield). Use for "UX", "flujos", "arquitectura de informacion", "wireframes", "pantallas", "usabilidad", "esta app es un desastre de usar", "redisenar como se usa". Not for brand or visual identity (orch-brand-system), not for the whole product at once (orch-product-design), not for implementing screens (orch-feature-team).
---

# Orchestrated UX Design

`orch-brand-system` answers "how does it look and feel". This skill answers "what
can people do, in what order, and where does everything live". Structure comes
before skin: layout, hierarchy and flow are decided in grayscale so color and
type cannot hide a bad structure.

It writes no new theory. It sequences installed skills and agents, adds the gates
between them, and owns the handoff spec the implementation must obey.

## What AI can and cannot do here (state this at Step 0)

- **Can:** derive tasks and flows from a clear brief, enumerate states and edge
  cases a human forgets, run a systematic heuristic evaluation, walk every flow,
  write interaction rules and acceptance criteria, and produce a clickable
  prototype.
- **Cannot:** observe real users. Personas, "pain points" and card-sort results
  produced here are **hypotheses from assumptions**, labeled as such. A small
  test with about 5 real people from the target audience finds most major
  usability problems (common Nielsen guidance, not a guarantee), and that test is
  the Phase 7 checkpoint. Until it is done the spec says `validation: pending`.

## Resources this skill uses

| Need | Tool |
|---|---|
| Why / go-no-go, journey and time-to-value audit | skill `product-lens` |
| Shared strategy (audience, positioning, tone) | skill `brand-discovery` output if it exists |
| Flow diagrams in FigJam | Figma `generate_diagram` after reading `figma-generate-diagram` |
| Wireframes / screens in Figma | `figma-use`, `figma-generate-design` via `get_figma_skill` + `use_figma` |
| Code-level interaction bugs (brownfield) | skill `click-path-audit` |
| Accessibility | skill `accessibility`, agent `ecc:a11y-architect` |
| Visual fit critique of wireframes | agent `design-critic` (user-level, bare name) |
| Live-app crawl and screenshots | Claude in Chrome per the global rule |
| Post-build verification | skill `browser-qa` |
| Parallel exploration | `general-purpose` agents with disjoint output folders |

ECC agents resolve only under the `ecc:` prefix; `design-critic` is bare. Load
deferred tools in ONE `ToolSearch` call.

## Output layout (in the target project repo)

```
ux/
  state.json            # resumable checkpoint
  00-intake.md
  baseline/             # brownfield only: screenshots, route map, findings
  01-users-jobs.md
  02-ia.md              # object model, navigation, sitemap
  03-flows/             # one file per top task + flow diagram
  04-wireframes/        # grayscale HTML or Figma frame links
  05-states.md          # state matrix per screen
  06-interactions.md    # behavior rules per component
  07-microcopy.md
  08-evaluation.md      # heuristic + walkthrough findings with severity
  09-test-plan.md
  SPEC.md               # the binding handoff, index of all of the above
```

## State

Write `ux/state.json` after every phase: `{runId, mode, phase, gatesPassed[],
topTasks[], figmaFileKey, lastUpdated}`. At activation read it first and report
in two sentences where the run stands. Never redo a finished phase.

## Step 0 - Intake, mode, depth

One question at a time, only what is missing:
1. **Mode:** `greenfield` or `brownfield`. In brownfield also: repo path, running
   URL, who uses it today, what hurts, and whether a full rebuild is allowed.
   If the app was never designed and a full redo is allowed, say so: it is the
   **blank-slate** variant (see Phase 0).
2. The product in the user's words; the primary users; the platforms.
3. If `brand/` exists, read its synthesis (audience, tone). If not, run a short
   audience and positioning pass (`brand-discovery` lite) so this skill does not
   invent the audience.
4. Depth: **lite** (top 3 tasks, lite evaluation) or **full** (all tasks, full
   evaluation, usability test plan). Recommend lite for a lab experiment.

## Phase 0 - Baseline (brownfield only)

Record the "before", read-only, then deliberately do NOT let it anchor the new
structure.
1. Crawl the running app with Claude in Chrome: route map, screenshots of every
   distinct screen at 375 / 768 / 1440, saved to `ux/baseline/`.
2. **Capability inventory:** every thing the app lets a person do, from the UI
   and from the code. This is the coverage checklist for the redesign: nothing
   is lost unless it is deliberately removed and recorded.
3. `product-lens` journey audit on the 3 to 5 most important tasks: steps, clicks,
   time-to-value, where people get stuck.
4. Heuristic evaluation (Nielsen's 10) of the current app, each finding severity
   0 to 4. Add `click-path-audit` when state bugs are suspected, and an
   accessibility baseline.
5. Blank-slate variant: if the app was never designed, the baseline mostly proves
   the case for a rebuild. Skip "preserve" thinking; keep only the capability
   inventory and the real workflows existing users depend on.

## Phase 1 - Users, jobs, top tasks

1. Jobs-to-be-done statements ("when I ___, I want to ___, so I can ___") for 1 to
   3 primary user types. No demographic filler.
2. Rank tasks by frequency x criticality. Pick the **top tasks** (3 in lite, up to
   8 in full). Everything else is secondary.
3. A success metric per top task: steps, time, error rate. These become the
   acceptance numbers for Phases 6 and 7.
4. Label every persona and pain point `hypothesis`.

**GATE 1.** Approve users, jobs, top tasks and metrics. Structure built on a wrong
task list is rework.

## Phase 2 - Information architecture

1. **Object model:** the nouns the product is made of and how they relate.
2. **Navigation model:** choose a pattern (tabs, sidebar, hub, wizard, command
   palette...) with the reason, tied to top tasks and platform.
3. Produce **two alternative IAs** and choose by explicit criteria: findability of
   top tasks, clicks to reach each, label clarity, growth room. Record why the
   other lost.
4. Sitemap as a Mermaid diagram (and a FigJam board if Figma is in scope, after
   reading `figma-generate-diagram`).
5. Brownfield: map every capability from Phase 0 to a home in the new IA, or to a
   recorded removal. Derive the IA from tasks first; use the old structure only
   as this coverage check.

## Phase 3 - Flows

For each top task: entry points, happy path, decision points, failure paths, edge
cases (empty, first-time, permission denied, offline, slow, partial data,
double-submit). Diagram each (Mermaid or FigJam). Then the **state matrix**
(`05-states.md`): for every screen, the loading, empty, error, partial, success
and disabled states and what the user sees and can do in each.

## Phase 4 - Grayscale wireframes and interaction rules

1. Low-fidelity, **no color or type decisions**: layout, hierarchy, component
   choice, content priority, responsive behavior (mobile first). Self-contained
   HTML or Figma frames via `figma-use` (read it before every `use_figma` call;
   calls strictly sequential; node-ID ledger on disk).
2. One screen per top-task step, with the state-matrix states, not just the happy
   path.
3. `06-interactions.md`: behavior rules per reusable component, because
   wireframes are not a substitute for interaction rules: trigger, feedback,
   validation timing, confirmation for destructive actions, keyboard path,
   focus order, motion intent.
4. Extract the **component inventory** the screens need. It is the input for the
   design system (`orch-brand-system` Phase 4).
5. `design-critic` on the wireframes: hierarchy and fit with neighbors, not
   styling.

**GATE 2.** Walk the user through each top task click by click on the wireframes.
Approve structure, flows and wireframes before any visual skin or code.

## Phase 5 - Microcopy

Labels, buttons, errors that say what happened and what to do next, empty states
that teach, confirmations, onboarding. Voice comes from the brand synthesis
(`brand-voice` if a profile exists). Ask which languages the product ships in;
write the source copy once and mark strings for translation.

## Phase 6 - Independent evaluation

Do not self-approve. Separate agents, each with only the artifacts:
1. Heuristic evaluation (Nielsen's 10) of the wireframes and flows, severity 0 to
   4, written to `08-evaluation.md`.
2. Cognitive walkthrough of every top task (does the user know what to do, see
   the control, connect it to the goal, understand the feedback).
3. `ecc:a11y-architect`: structure, focus order, targets, reading order, reduced
   motion intent.
4. Dark-pattern and cost-of-error check on irreversible actions.
5. Fix every severity 3 and 4 finding, re-run the affected check, and record
   what was deferred and why.

## Phase 7 - Prototype and validation

1. Clickable prototype of the top tasks (Figma prototype, or a coded HTML
   prototype). The same prototype is what the test uses.
2. `09-test-plan.md`: tasks without leading wording, success criteria from the
   Phase 1 metrics, what to observe, the script for 5 people from the real
   audience. Give it to the user to run; AI cannot replace it.
3. Record `validation: pending|done` in `SPEC.md`. If the test contradicts the
   spec, return to Phase 2 or 4 with the evidence.

## Phase 8 - Handoff spec

1. `SPEC.md`: index of everything, the chosen IA and why, top tasks with their
   metrics, and per flow **acceptance criteria** in EARS form ("When X, the
   system shall Y") that become the ticket's acceptance field.
2. Append the **UX contract** to the project `CLAUDE.md`:

   ```
   ## UX contract (binding)
   - Implement only the screens, states and interactions in ux/SPEC.md.
   - Every screen implements its full state matrix (ux/05-states.md).
   - A behavior or state not in the spec is escalated to the user, not invented.
   - Navigation, labels and copy come from ux/02-ia.md and ux/07-microcopy.md.
   - Each flow is verified in a real browser against its acceptance criteria.
   ```
3. Order the implementation by top-task criticality, one flow per unit of work,
   handed to `orch-feature-team` (greenfield) or `orch-change-feature`
   (brownfield: the screens change behavior). Visual skin comes from
   `orch-brand-system` tokens, applied over these structures.
4. **GATE 3.** Present the artifact list, the validation status and the contract
   text. Commit only after confirmation, in the repo's commit convention. No
   Claude attribution anywhere.

## Verification (the run is done when all are true)

- Mode and depth were declared at Step 0, and the AI limits were stated.
- Gates 1, 2 and 3 were each explicitly approved by the user.
- Top tasks have numeric success metrics; personas are labeled hypotheses.
- Two IAs were compared and the choice is justified; in brownfield, every old
  capability maps to a new home or a recorded removal.
- Every screen has its state matrix; interaction rules exist per component.
- Independent heuristic evaluation, walkthrough and accessibility review ran, and
  no severity 3 or 4 finding is open without a recorded reason.
- A prototype and a usability test plan exist; `validation:` is stated honestly.
- The UX contract is in the project `CLAUDE.md`.

Conversation with William in Paraguayan Spanish. All artifacts in English except
product microcopy, which follows the product's languages. Free tiers first.

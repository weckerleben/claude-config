---
name: orch-brand-system
description: Orchestrates a complete visual identity BEFORE any app code exists - brand strategy, emotional and commercial brief, divergent visual directions, palette, typography, icons, logo exploration, motion language, design tokens, a Figma library, adversarial critique, and a binding design contract the implementation must obey. Use when starting a new app or product from an idea and the user wants colors, icons, animations, brand and a visual guide fixed up front so development does not improvise ("armame la marca", "identidad visual", "guia visual", "design system desde cero", "que no improvise el diseno", "branding de la app"). Not for auditing an existing UI (use ecc:design-system audit) and not for building features (use orch-feature-team).
---

# Orchestrated Brand System

Problem this solves: a written plan does not bind the implementation. When code
gets written, the model fills every visual gap by taste. The fix is a **binding,
machine-readable design contract** (tokens + rules + preview) that exists before
the first component, is committed to the repo, and is enforced by the project
`CLAUDE.md` plus the `design-critic` gate.

This skill is a **conductor**. It writes no new methodology: it sequences skills
and agents that are already installed, adds the gates between them, and owns the
handoff artifact. Everything is proposed, nothing is silently decided: the user
approves at three gates.

## What AI can and cannot do here (state this to the user at Step 0)

- **Can:** structured strategy, divergent exploration, consistent systems, exact
  tokens, contrast math, accessibility, motion specs, Figma library, and an
  adversarial critique pass.
- **Cannot:** measure real emotional response or market fit. Every statement of
  the form "this color evokes trust" is a **hypothesis**, not a fact. Color and
  archetype associations are generic heuristics. The skill therefore labels
  them as hypotheses and ends with a real-human validation checkpoint (Phase 7).
- Logo generation by image models is exploration only. A production logo is
  hand-built as clean vector (SVG or Figma), never shipped as a raster render.

## Resources this skill uses

| Need | Tool |
|---|---|
| Brand interview, archetype, positioning, voice | skill `brand-discovery` (+ `brand-voice`) |
| Competitor scoping and scoring | skills `competitive-platform-analysis` then `benchmark-methodology` |
| Design direction, anti-template taste | skills `frontend-design-direction`, `taste`, `make-interfaces-feel-better` |
| Tokens, DESIGN.md, preview, slop check | skill `design-system` |
| Motion tokens and patterns (React/Next) | skills `motion-foundations`, `motion-patterns`, `motion-advanced` |
| Accessibility | agent `a11y-architect`, skill `accessibility` |
| Critique | agent `design-critic` (user-level, bare name), skill `gan-design` |
| Image exploration | `creative_generate_image` / Figma `generate_image` (load via ToolSearch) |
| Figma | `get_figma_skill` + `use_figma` (see Phase 6) |
| Positioning/copy second opinion | agent `ecc:marketing-agent` |

Agents from ECC resolve only under the `ecc:` prefix (e.g. `ecc:a11y-architect`);
`design-critic` is bare. Load deferred tools in ONE `ToolSearch` call.

## Output layout (in the target project repo)

```
brand/
  state.json               # resumable checkpoint (see State)
  00-intake.md
  modules/                 # brand-discovery output, ends in 90_SYNTHESIS.md
  01-feeling-brief.md
  02-directions/{a,b,c}/   # tokens.draft.json + preview.html each
  03-identity/             # logo/*.svg, icons.md, fonts.md
  design-tokens.json       # SOURCE OF TRUTH
  tokens.css
  DESIGN.md                # rationale per decision
  MOTION.md
  design-preview.html
  figma.md                 # file key, node ledger, sync direction
  BRAND.md                 # index + the contract block
```

## State

Write `brand/state.json` after every phase: `{runId, phase, gatesPassed[],
chosenDirection, figmaFileKey, lastUpdated}`. At activation, read it first and
report in two sentences where the run stands. Long phases span sessions
(`brand-discovery` is multi-session by design); never restart a finished phase.

## Step 0 - Intake and depth

Ask only what is missing, one question at a time:
1. The idea in the user's words (problem, who it is for, what it does).
2. Platforms: web, iOS, Android. This decides the motion stack (the `motion-*`
   skills are React/Next specific; for native, motion is specified in
   `MOTION.md` as tokens and the platform skill implements it) and the icon set.
3. Existing assets (name, logo, colors, a site, references they love or hate).
4. Depth: **lite** (one sitting, discovery compressed to the 4 modules that drive
   visuals: purpose, positioning, audience, personality) or **full** (all
   `brand-discovery` modules plus competitor benchmark). Recommend lite for a
   lab experiment, full for anything with a real launch.

Declare the depth and the output directory in one line the user can override.

## Phase 1 - Strategy

1. Run `brand-discovery` at the chosen depth. Honor its one-question-at-a-time
   discipline; do not answer for the user.
2. Full depth only: `competitive-platform-analysis` then `benchmark-methodology`
   to place the brand in its category and find **visual white space** (what every
   competitor looks the same on).
3. Output: `modules/90_SYNTHESIS.md` (or its lite equivalent).

**GATE 1.** Present the synthesis: positioning sentence, audience, archetype
(primary + secondary), personality, tone. Wait for approval. Visual work built
on an unapproved strategy is the most expensive mistake in this pipeline.

## Phase 2 - Emotional and commercial translation, then divergence

This is the phase that carries "emotional and commercial weight".

1. Write `01-feeling-brief.md`:
   - 3 to 5 **target feelings** and 2 to 3 **anti-feelings** (what it must never
     feel like), each traced to a sentence in the synthesis.
   - **Commercial constraints:** price position, category conventions that must
     be respected to be recognized (e.g. finance needs credibility cues), the
     one conversion moment the visuals must not hurt, and the differentiation
     the white space allows.
   - A **lever map** per feeling: which of color, type, shape, density, imagery,
     and motion carries it, each marked `hypothesis`. Archetypes constrain the
     design space; they do not dictate a palette. Never copy an archetype's
     default colors.
2. **Diverge before converging.** Produce three genuinely different directions
   (A, B, C), in parallel via three `general-purpose` agents with disjoint output
   folders (`02-directions/a|b|c`). Each returns a `tokens.draft.json` and a
   self-contained `preview.html` showing: palette, type pairing, shape/radius
   language, one sample screen, and motion character in one sentence. Run the
   `design-system` AI-slop checks and `taste` on each; discard a direction that
   reads as template (purple-blue default gradient, glass cards without purpose).
3. Show the three previews side by side with the feeling each one bets on and its
   commercial risk.

**GATE 2.** User picks one direction, or a named blend. Record the choice and
the reasons in `state.json`. Do not proceed with "all of them".

## Phase 3 - Identity assets

1. **Palette:** derive from the chosen direction. Contrast is **computed, not
   eyeballed**: every text/background semantic pair must pass WCAG 2.2 AA
   (4.5:1 body, 3:1 large and UI) in both light and dark modes. Use a small
   script and print the table. For chart colors use the `dataviz` skill and its
   validator.
2. **Typography:** free first. Google Fonts or system fonts, a pair maximum plus
   mono if needed. Record the type scale and the licenses in `fonts.md`.
3. **Icons:** pick ONE library (Lucide or Phosphor, free) and pin it in
   `icons.md` with stroke width, size grid, and the rule that custom icons match
   it. Icon fidelity inside Figma uses INSTANCE_SWAP, not a variant per icon.
4. **Logo (exploration, then craft):** generate marks only as exploration with
   image tools; pick a direction; then build the final mark as clean SVG by
   hand (or in Figma) with a monochrome version, a minimum size, and clear-space
   rule. Check the name/mark for obvious conflicts with a web search and say what
   was and was not checked. This is not a trademark clearance.
5. Imagery and illustration rules: one paragraph (what to show, treatment, what
   to avoid).

## Phase 4 - Tokens and design guide

Greenfield note: `design-system` Mode 1 extracts from existing code, and there
is none yet. Here, generate the tokens from the chosen direction, then use
`design-system` for its outputs and its audit.

1. Write `design-tokens.json` (the single source of truth) with: color primitives
   and semantic aliases for light and dark, type scale, spacing scale (4/8
   base), radius, elevation, z-index, breakpoints, motion durations/easings
   (see Phase 5), icon size grid, and state tokens (hover, focus, disabled,
   error).
2. Emit `tokens.css` (custom properties) from it. If the stack is Tailwind,
   also emit the theme extension. Never hand-edit the derived files.
3. Write `DESIGN.md`: rationale per decision, each tied back to a feeling in the
   brief, with the hypothesis label kept.
4. Build `design-preview.html`: self-contained specimen of everything above plus
   2 to 3 representative screens (not isolated swatches), in both themes.

## Phase 5 - Motion

1. Principles first, tied to feelings (e.g. "calm and confident means ease-out,
   no overshoot"). Motion that does not guide attention, communicate state, or
   preserve spatial continuity is removed.
2. Web React/Next: apply `motion-foundations` (tokens, springs, reduced-motion,
   SSR safety), then `motion-patterns` for the signature moments. Express the
   result as tokens inside `design-tokens.json` and as `MOTION.md`.
3. `MOTION.md` lists: durations/easings, the 5 to 8 signature animations with
   trigger, purpose, and reduced-motion fallback, and what is never animated.
4. Native targets: specify the same tokens; the implementation skill for that
   platform consumes them.

## Phase 6 - Figma

Direction of truth: **code-first.** `design-tokens.json` is the source of truth;
Figma is a generated, reconcilable mirror and the review surface for people who
do not read JSON. Do not make Figma the source unless the user explicitly chooses
that, because two writable sources drift.

The Figma skills are exposed as MCP resources. Read them with `get_figma_skill`
(`skill://figma/<name>/SKILL.md`); they are mandatory prerequisites.

1. `whoami` first: confirm the account, plan and seat. If the plan cannot write
   or is rate limited, say so and stop here; deliver Phases 1 to 5 and 7 to 8
   without Figma.
2. Read `figma-create-new-file`, then create the Design file (this is an
   outward-facing write: state what will be created and where before doing it).
3. Read `figma-use` BEFORE every `use_figma` call. Then follow
   `figma-generate-library`: variable collections (Primitives, Color
   Light/Dark, Spacing, Typography), scopes on every variable (never
   `ALL_SCOPES`), `var()` code syntax on web, text/effect styles, then a brand
   board page (logo, palette, type, icons, motion notes) and the components the
   first screens need. Inventory is locked at the start: do not grow it.
4. `use_figma` calls are strictly sequential. Keep the node-ID ledger on disk
   (`brand/figma.md` plus the `/tmp` ledger the skill prescribes); never guess an
   ID.
5. Optional, only if asked: `figma-generate-design` for key screens from the
   preview, and `figma-use-motion` for prototype animation.
6. Record the file key and the reconcile procedure in `figma.md`: when tokens
   change, re-run the library skill's reconciliation scope, never rebuild.

## Phase 7 - Critique and verification

Do not self-approve. Independent passes, in this order:

1. `design-critic` on `design-preview.html`: map the surface and neighbors first,
   then judge fit. Apply what lands.
2. `design-system` audit and slop-check on the preview.
3. `ecc:a11y-architect`: contrast table, focus states, target sizes, reduced
   motion.
4. Open the preview in the browser (Claude in Chrome per the global rule), take
   screenshots at 375 / 768 / 1440 in both themes, and read the console: zero
   errors. Report what was observed.
5. Optional bounded loop: `gan-design` on the preview if the score is weak.
6. **Human validation checkpoint (cannot be skipped, only deferred explicitly).**
   Give the user a 10-minute test to run on 5 real people from the target
   audience: a 5-second recall test of the preview ("what is this and how does
   it feel?"), a preference test among the finalists, and a check that the
   anti-feelings did not appear. Compare their words with the feeling brief. If
   the feelings do not match, return to Phase 2 with the evidence. Until it is
   done, `BRAND.md` says `validation: pending`.

## Phase 8 - Handoff contract

1. Write `BRAND.md`: index of every artifact, the chosen direction and why,
   `validation: pending|done`, and the Figma file link.
2. Append the **Design contract** block to the project `CLAUDE.md`:

   ```
   ## Design contract (binding)
   - All UI uses brand/design-tokens.json via tokens.css. No hardcoded colors,
     fonts, spacing, radii, shadows, durations or easings in components.
   - Icons: <library> only, <stroke> stroke. Fonts: <pair> only.
   - Motion follows brand/MOTION.md; honor prefers-reduced-motion.
   - Any visual decision not covered by brand/ is escalated to the user, not
     improvised. Add it to design-tokens.json first, then use it.
   - Every frontend change passes design-critic against brand/DESIGN.md.
   ```
3. Add an enforcement check: a lint step (script or CI) that fails on hex/rgb
   literals and raw `px` font sizes outside `tokens.css` and the tokens file.
   Without a mechanical check, the contract is advice, and advice is exactly
   what failed before.
4. **GATE 3.** Present the artifact list, the validation status, and the contract
   text. Commit only after confirmation, in the repo's commit convention (detect
   per the global dual policy). No Claude attribution anywhere.

## Verification (the run is done when all are true)

- Depth and platforms were declared at Step 0, and the AI limits were stated.
- Gate 1, Gate 2 and Gate 3 were each explicitly approved by the user.
- Three divergent directions existed before one was chosen.
- Every semantic color pair has a computed AA contrast result in both modes.
- `design-tokens.json` is the only source; `tokens.css` and Figma derive from it.
- Figma: `whoami` was checked, `figma-use` was read before each write, calls were
  sequential, and the ledger is on disk. Or Figma was skipped with the reason.
- `design-critic`, slop-check and `a11y-architect` ran; browser screenshots and a
  clean console were observed, not assumed.
- Emotional claims are labeled hypotheses; `validation:` is recorded honestly.
- The Design contract is in the project `CLAUDE.md` and a mechanical check exists.

Conversation with William in Paraguayan Spanish. All artifacts in English.
Free tiers first; flag anything that would cost money before using it.

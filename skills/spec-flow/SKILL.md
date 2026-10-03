---
name: spec-flow
description: >
  The spine of the PRD → RFC → ADR → Plan chain, across any repo in the vertical.
  Resolves the repo's profile (stack, variant axis, components, tracker fields),
  owns artifact paths, IDs, cross-references and the change-propagation matrix.
  Use when starting a non-trivial change and deciding which documents it actually
  needs; when a PRD, RFC or ADR changes and downstream artifacts must be
  re-checked; when asked "¿esto necesita RFC?", "¿hace falta ADR?", "arranquemos
  con el PRD", "qué documento va primero"; or when wiring a document to a
  ticket's PRD / RFC-ADR / acceptance-criteria fields. Do NOT use to write a
  document — delegate to rfc-author or adr-author.
metadata:
  origin: weck
  owner: William Eckerleben
---

# Spec Flow

Four artifacts, one chain, no gaps. This skill decides **which** documents a
change needs and keeps them consistent. It does not write them.

```
PRD ──────────► RFC ──────────► ADR ──────────► Plan ──────────► Code
what / why      how (proposal)  why this one    task breakdown
/plan-prd       rfc-author      adr-author      /plan
```

Each artifact points **back** at its parent and **forward** at its children. A
decision in an ADR must be traceable to a line in the PRD in three hops or
fewer. If it is not, one of the artifacts is missing a reference.

Nothing here is stack-specific. Everything that varies by repo — the stack, the
components, whether there is a parallel-version axis at all, the tracker fields
— lives in the repo's profile.

## Step 0 — resolve the profile

Always first. Never assume the repo's shape from its name.

```bash
bash ~/.claude/skills/spec-flow/scripts/repo-profile.sh
```

Reads `.claude/spec-flow.yml` when it exists; otherwise infers from the repo's
markers and labels every inferred value. Declared beats inferred.

Three fields change how the rest of this skill behaves:

| Field | Effect |
|---|---|
| `variant_axis` | `none` → the RFC's variant section and the ADR's `variant:` field are **omitted**, not filled with `n/a` |
| `sibling_repos` | a decision here may bind there — the ADR must say so explicitly |
| `tracker.fields` | which ticket fields the documents feed, and whether a local file satisfies them |

Schema, inference rules and the per-repo table: `references/repo-profile.md`.

## Stage gate — what a change actually needs

Run this before writing anything. Most changes do not need four documents.

| Change | PRD | RFC | ADR | Plan |
|---|---|---|---|---|
| Bugfix, no behavior change | no | no | no | inline |
| Behavior change inside one component | no | no | only if it sets a precedent | `/plan` |
| New capability, one component, no new dependency | yes (lean) | no | no | `/plan` |
| Cross-component / cross-service change | yes | yes | yes, per irreversible choice | `/plan` |
| New dependency, new table, new integration, schema change | yes | yes | **yes** | `/plan` |
| Anything that binds a `sibling_repo` | yes | yes | **yes** | `/plan` |
| Something that will be hard to undo in 6 months | — | — | **yes, always** | — |
| P0 production outage | no | no | **after the fact** | no |

**The ADR trigger is reversibility, not size.** A one-line `depends` change in a
manifest that couples two verticals is an ADR. A 900-line report module that
follows the existing pattern is not.

**P0 fast lane.** A production outage takes the tracker's hotfix path.
Documentary debt is settled after the fire is out — the ADR is written
retroactively with `date:` set to the day of the decision, not the day of
writing. Never block a P0 on a document.

## Artifact contract

### Paths

| Artifact | Path | Written by |
|---|---|---|
| PRD | `.claude/prds/{slug}.prd.md` | `/plan-prd` or `/prp-prd` |
| RFC | `{docs.rfc}/RFC-NNNN-{slug}.md` | `rfc-author` |
| ADR | `{docs.adr}/ADR-NNNN-{slug}.md` | `adr-author` |
| ADR index | `{docs.adr}/README.md` | `adr-author` (generated) |
| Plan | `.claude/plans/{slug}.plan.md` | `/plan` |

`docs.rfc` and `docs.adr` come from the profile, defaulting to `docs/rfc` and
`docs/adr`. `NNNN` is zero-padded four digits, monotonic per repo, never reused —
the `adr-tools` convention, kept for RFCs so both corpora read the same way.

### Frontmatter schema

Every artifact carries the links. This is the whole traceability mechanism; do
not rely on prose references.

```yaml
# PRD
---
id: PRD-{slug}
status: draft | approved | superseded
ticket: ODOO-123        # null until it exists
rfcs: [RFC-0004]        # filled by rfc-author
published: <url>        # filled when published to the tracker's doc host
---
```

```yaml
# RFC
---
id: RFC-0004
title: <one line, imperative>
status: draft | in-review | accepted | rejected | superseded
prd: .claude/prds/core-ledger-events.prd.md
adrs: [ADR-0007, ADR-0008]
ticket: ODOO-123
variant: [v16, v19]                # omit the key when variant_axis is none
components: [cashea_allies_balance_report, cashea_account_factoring]
affects_repos: [cashea-odoo-v19]   # from sibling_repos, when it binds them
date: 2026-08-29
---
```

```yaml
# ADR
---
id: ADR-0007
title: <the decision, as a noun phrase>
status: proposed | accepted | rejected | deprecated | superseded
rfc: RFC-0004
supersedes: null
superseded_by: null
variant: [v16, v19]     # omit when variant_axis is none
components: [cashea_allies_balance_report]
affects_repos: []
date: 2026-08-29
deciders: [William Eckerleben]
---
```

```yaml
# Plan
---
rfc: RFC-0004
adrs: [ADR-0007, ADR-0008]
constraints_from_adr: [...]   # copied verbatim
---
```

`components` means whatever this repo's unit is — an Odoo module, a Python
package, a TS workspace, a Terraform stack. The ADR index groups by it, so
"what did we already decide about X" is one query in every repo.

### Language rule

**The artifact's language follows its audience, not the repo.** Defaults live in
the profile's `language:` key; override there, not per document.

| Artifact | Default | Why |
|---|---|---|
| PRD | Spanish | read and approved by PM / funcional |
| RFC | Spanish | approved by TL, and its acceptance section becomes the ticket's acceptance field |
| ADR | English | lives beside code, read by whoever opens the component in two years |
| Plan, code, commits, PRs | English | standing rule — code artifacts are English, no exceptions |

The one place this bites: an ADR quoting a PRD requirement. Quote it in the
original language inside a blockquote; do not translate — a translated
requirement is a second source of truth.

## Tracker binding

The chain is a convention in most repos and **enforced** in some. When the
profile declares `tracker.fields`, the workflow has hard validators and the
documents must feed them.

Worked instance — Jira project `ODOO` (id 12670), the Odoo vertical:

```
Functional Decision --Approve for dev--> Product Review
                     requires PRD                    (tracker.fields.prd)
Product Review --Approve PRD (rol PM)--> Technical Design
Technical Design --Approve design (rol TL)--> To Do
                     requires RFC / ADR              (tracker.fields.rfc_adr)
                     AND Criterios de Aceptación     (tracker.fields.acceptance)
```

Two consequences that hold wherever a tracker is declared:

- The `prd` and `rfc_adr` fields are **url** fields. A repo path does not satisfy
  them — the document must be published and the URL pasted. Report the publish
  step; **never report the gate as satisfied by a local file.**
- The acceptance field is **generated by `rfc-author`**, not hand-written at gate
  time. It is the RFC's acceptance section, verbatim.

When `tracker` is empty the chain still runs — there is just no external
validator, so the stage gate above is the only thing standing between the change
and undocumented work.

## PRD readiness contract

`/plan-prd` produces a good problem statement and a weak requirements section —
it stops at prose. Before an RFC can consume it, the PRD needs requirements that
are **binary**. Upgrade it in one pass; do not start a new PRD.

Requirements go in **EARS** notation:

| Pattern | Form |
|---|---|
| Ubiquitous | THE SYSTEM SHALL `<behavior>` |
| Event-driven | WHEN `<trigger>` THE SYSTEM SHALL `<behavior>` |
| State-driven | WHILE `<state>` THE SYSTEM SHALL `<behavior>` |
| Unwanted | IF `<condition>` THEN THE SYSTEM SHALL `<behavior>` |
| Optional | WHERE `<feature is present>` THE SYSTEM SHALL `<behavior>` |

```
WHEN se recibe un pago que no puede asignarse a una cuota,
THE SYSTEM SHALL registrar E4a contra la transitoria "pagos pendientes de aplicar".
```

Why EARS and not user stories: every clause maps to one assertion in one test. A
narrative requirement maps to a conversation.

A PRD is **RFC-ready** when every requirement is EARS or explicitly `TBD — needs
validation via {method}`, scope has an explicit out-of-scope list, and the
Delivery Milestones table exists. Nothing else is required.

## Change propagation matrix

The part no template ships and the part that actually decays. When something
upstream changes, these are the artifacts that are now suspect.

| What changed | Re-check | Action |
|---|---|---|
| PRD problem or users | every RFC in `rfcs:` | the RFC may be solving the wrong problem — re-read Motivation, do not patch |
| PRD requirement added | RFCs, then the acceptance field | a new requirement needs an acceptance clause or it ships untested |
| PRD requirement removed | RFC, ADRs | an ADR whose only driver was it becomes `deprecated`, not deleted |
| PRD scope cut | RFC non-goals | move the cut item into Non-goals explicitly; silence reads as oversight |
| RFC option chosen changes | every ADR with that `rfc:` | write a **new** ADR that supersedes; never edit an accepted ADR's decision |
| RFC accepted | Plan | `/plan` must read `constraints_from_adr` before task breakdown |
| ADR superseded | Plan, code | grep the `components:` for the old pattern; not done until the code stops contradicting it |
| Code diverges from an accepted ADR | the ADR | either the code is a bug or the ADR is stale — decide explicitly |
| A new variant is added to the axis | RFC, every ADR carrying `variant:` | variant-specific decisions rarely survive the widening; re-examine each |
| `sibling_repos` changes | ADRs with `affects_repos:` | the sibling may now be following a decision nobody told it about |

**Never append a changelog to an artifact.** Spec documents state the current
decision and current reality only. When something changes, rewrite it in place.
The history lives in git, and the discarded options live in the ADR — which is
precisely what the ADR is for, and precisely why the RFC and PRD stay clean.

## Where the rationale goes

The single most important split in this system:

- **PRD and RFC are living documents.** Rewritten in place, always current, no
  rationale paragraphs, no "antes era X ahora es Y", no forensics.
- **The ADR is the append-only ledger.** Immutable once accepted. The only place
  where *why*, *what we rejected* and *what it costs us* are recorded.
  Superseding writes a new file; it never edits the old one.

Without the ADR there is nowhere to put the reasoning, so it leaks back into the
spec and rots it. The ADR is what lets the RFC stay clean.

## Delegation

| Need | Go to |
|---|---|
| Resolve the repo's shape | `scripts/repo-profile.sh` |
| Write / upgrade the PRD | `/plan-prd`, then the EARS contract above |
| Write the RFC | `rfc-author` skill |
| Write or supersede an ADR | `adr-author` skill |
| Break the RFC into tasks | `/plan`, or `ralphinho-rfc-pipeline` for multi-agent DAG execution |
| Implement | `/prp-implement`, `/orch-add-feature`, `tdd-guide` |
| Stack conventions | the repo's own domain skills and its `CLAUDE.md` |
| Index or query existing ADRs | `adr-author` → `scripts/adr-index.sh` |

## Reporting

When this skill runs the stage gate, report exactly this and stop:

```
Repo:    {project} · {stack} · axis {variant_axis} · profile {declared | inferred}
Change:  {one line}
Needs:   PRD {yes/no} · RFC {yes/no} · ADR {yes/no · trigger} · Plan {yes/no}
Binds:   {sibling repos, or —}
Skipped: {artifact} — {reason}
Start:   {the single next command}
```

No preamble, no options menu. If the call is genuinely ambiguous, name the
tension in one sentence and give a recommendation.

---
name: rfc-author
description: >
  Write, review or supersede a technical RFC (design doc) from an approved PRD,
  in any repo of the vertical. Produces RFC-NNNN-slug.md with goals, non-goals,
  options considered, drawbacks, rollback and EARS acceptance criteria ready to
  paste into the ticket's acceptance field. Use when the user says "escribí el RFC", "necesito un
  design doc", "propuesta técnica", "documentá cómo lo vamos a hacer", when a
  ticket is entering Technical Design, or when reviewing someone else's RFC.
  Extracts the irreversible choices and hands them to adr-author. Do NOT use for
  the problem statement (that is /plan-prd) or for recording a settled decision
  (that is adr-author).
metadata:
  origin: weck
  owner: William Eckerleben
---

# RFC Author

An RFC proposes **how**, given a PRD that established **what** and **why**. It is
a document under discussion — it argues, it is allowed to be wrong, and it stops
being editable the moment it is accepted.

Lineage: Oxide's RFD process for the lifecycle, Rust's RFC fields for forced
self-critique, Google's design doc for non-goals, Squarespace's "Yes, if" for the
review norm. What is local is the variant axis and the tracker binding — and
both come from the repo, not from this file.

## Before writing

Read, in this order, and stop if the second one is missing:

1. **The repo profile** — `bash ~/.claude/skills/spec-flow/scripts/repo-profile.sh`.
   It decides whether this RFC has a variant section at all, what a component is
   here, and which sibling repos a decision may bind.
2. The PRD at `.claude/prds/{slug}.prd.md`. **If there is no PRD, stop and say
   so.** An RFC without a PRD is a solution looking for a problem; do not
   reconstruct the problem statement from the request.
3. Existing ADRs — the ADR index at `{docs.adr}/README.md`. A decision already
   recorded is a constraint on this proposal, not an option to re-open. Cite it
   and move on.
4. The code the proposal touches. Concrete file references beat description.

Then ask **one** question set, no more:

> 1. ¿Qué opciones ya descartaste mentalmente y por qué? (van a la tabla, no se pierden)
> 2. ¿Qué NO va a hacer este cambio, aunque alguien lo pida?
> 3. {solo si el perfil declara un eje} ¿Esto aplica a {variants}, o a alguno solo?

Ask question 3 **only when `variant_axis` is not `none`** — in most repos there
is no such axis and asking invents one. Where the axis does exist and the answer
is "no sé", the answer is *all declared variants*: that is the production
reality, and a design that quietly assumes one gets rewritten.

## Numbering

```bash
mkdir -p docs/rfc
next=$(ls docs/rfc 2>/dev/null | grep -oE '^RFC-[0-9]{4}' | grep -oE '[0-9]{4}' | sort -n | tail -1)
printf 'RFC-%04d\n' $(( 10#${next:-0} + 1 ))
```

Highest existing number plus one, zero-padded to four. Never reuse a number,
even for a rejected RFC. A rejected RFC stays in the
tree with `status: rejected`; that it was considered and refused is information.

## Template

The template lives at `templates/rfc.md` in this skill. Copy it verbatim and
fill it. Section order is deliberate — non-goals before the proposal, options
before drawbacks — because writing them in that order is what catches scope
creep before it reaches the design.

Rules that override the template's comfort:

- **Non-goals are mandatory and specific.** "Performance" is not a non-goal.
  "No cambiamos el grano de los postings; sigue siendo por cuota" is. An empty
  non-goals section means the boundary was never drawn and the change will grow.
- **Options considered needs at least two real options,** one of which is
  usually "no hacer nada / seguir con lo actual". An option listed only to be
  dismissed in half a line is not an option, it is decoration — either argue it
  or drop it.
- **Drawbacks is written by the author, about the author's own proposal.** If it
  is empty, the proposal has not been thought about hard enough. Reviewers
  should be adding to that section, not creating it.
- **Every claim with a number cites where the number came from.** A metric
  measured over the convenient dataset instead of the widest available one gets
  rejected on sight. If there is no number, write `TBD — needs measurement via
  {method}`; never estimate a figure into a design doc.
- **No rationale prose outside `Options considered`.** The rest of the document
  states the design as it stands. The "why not the other thing" lives in the
  options table and, once settled, moves to an ADR.

## Variant impact

**Include this section only when the profile declares a `variant_axis`.** When
the axis is `none`, delete the section — do not leave it filled with "n/a", which
trains reviewers to skip sections.

Where an axis exists, it is mandatory and never abbreviated. For each declared
variant, state:

- Does this change apply? (yes / no / different implementation)
- If different: what differs, and is the difference a decision worth its own ADR?
- Which components, in which repo?

Worked instance — the Odoo repos run v16 and v19 **in parallel in production**,
so a design covering one is half a design, and the common v19 item is the
**migration regression**: behavior that worked in v16 and broke in v19. If that
is what the RFC addresses, say so in the summary; it changes what reviewers look
for. In `cashea-iac-live` the same section is environments; in `erp-service`
there is no such section at all.

## Sibling repos

If the profile lists `sibling_repos`, answer explicitly: does this proposal bind
them? A ledger contract decided in one repo usually binds the service that reads
it. Record the answer in `affects_repos:` — including when the answer is no, so
nobody has to re-derive it.

## Acceptance criteria → Jira

The RFC's acceptance section is the source for the ticket's acceptance field
(`tracker.fields.acceptance` in the profile — `customfield_12007` in the Odoo
vertical's Jira, where the `Approve design` transition requires it). Write it
once, here, so nobody re-derives it at gate time.

Use EARS for system behavior and Given/When/Then for user-facing flows. Each
clause must be:

- **binary** — it passes or fails, no judgement call;
- **observable** — from outside the code, by a test or by a person;
- **attributable** — traceable to a PRD requirement, or it is scope creep.

```
WHEN el reporte semanal netea una orden cancelada
THE SYSTEM SHALL no emitir un segundo asiento por E7 para esa orden.
```

Report the block verbatim at the end so it can be pasted without editing.

## Extracting ADRs

Before declaring the RFC done, scan `Options considered` and pull out every row
where the chosen option is **hard to reverse**: a schema shape, a service
boundary, a dependency, a data granularity, an integration contract, a
deprecation.

Each of those is an ADR, not a paragraph in the RFC. List them in the RFC's
`Decisions` section as `ADR-NNNN — pending` and hand them to `adr-author`. The
RFC then references the ADR instead of restating the argument.

An RFC with zero extracted decisions is either genuinely mechanical work — fine,
say so — or the irreversible choice is hiding inside the proposal unexamined.
Check which before moving on.

## Review norm — "Yes, if"

When reviewing an RFC (yours or someone else's), answer **"sí, si…"** rather
than **"no, porque…"**. `no, porque` ends the conversation and pushes the work
into a DM; `sí, si` names the condition under which you would approve, which is
the same information in a form the author can act on.

Review passes over, in order:

1. Does the proposal solve the PRD's problem, or an adjacent one it finds more
   interesting?
2. Are the non-goals real boundaries or throat-clearing?
3. Is the discarded option discarded for a reason that survives being stated out
   loud?
4. Does the rollback plan work at 3am, by someone who did not write this?
5. Do the acceptance criteria fail when the feature is broken?

## Lifecycle

| Status | Meaning | Editable |
|---|---|---|
| `draft` | being written | freely |
| `in-review` | open for comment | yes, in response to comments |
| `accepted` | approved, TL signed off | **no** — supersede instead |
| `rejected` | considered and refused | no; keep the file, the reasoning is the value |
| `superseded` | replaced by a newer RFC | no; add `superseded_by:` |

An accepted RFC that needs to change gets a new RFC that supersedes it. Editing
an accepted RFC destroys the record of what was actually approved, which is the
only reason the document exists.

## Publishing

When the profile declares a tracker, the local file is not the deliverable for
the gate — `tracker.fields.rfc_adr` is a **url**. After writing:

1. Report the local path.
2. Say explicitly that the gate needs a published URL (Notion, or a repo blob
   URL where one exists) and that this is a manual step.
3. Never report the gate as satisfied. A local file satisfies review; it does
   not satisfy the validator.

Repo-first is deliberate: the file lives next to the code it describes and moves
with the branch. Notion is a publishing target, not the source of truth. When
they diverge, the repo wins and Notion gets rewritten in place.

## Output

```
RFC written: docs/rfc/RFC-NNNN-{slug}.md

PRD:        {path}
{eje}:      {variants}          # línea omitida si variant_axis es none
Componentes:{list}
Binds:      {sibling repos | —}
Opciones:   {n} consideradas, {n} descartadas
Decisiones a extraer: {n} → adr-author
Sin resolver: {n}

Criterios de Aceptación (pegar en {tracker.fields.acceptance}):
---
{block verbatim}
---

Siguiente: {adr-author para ADR-NNNN | publicar y pegar URL en el ticket | /plan}
```

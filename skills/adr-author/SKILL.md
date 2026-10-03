---
name: adr-author
description: >
  Record, supersede or index an Architecture Decision Record in MADR 4.0.0
  format, in any repo of the vertical. Owns numbering, the ADR index, supersede
  links, and the component / variant axis so a decision taken in one component
  or repo can be found from another.
  Use when the user says "esto hay que dejarlo documentado", "por qué elegimos
  X", "escribí el ADR", "esta decisión la tomamos hace meses", when an RFC hands
  over an irreversible choice, when superseding an old decision, or when asked
  what was already decided about something. Do NOT use to propose a design
  (rfc-author) or to state requirements (/plan-prd).
metadata:
  origin: weck
  owner: William Eckerleben
---

# ADR Author

An ADR records **one decision, once, forever**. It is dated, immutable after
acceptance, and superseded rather than edited.

Format is **MADR 4.0.0** — adopted whole, not adapted. It is what Nygard's
template became after a decade of community use, and every ADR tool in existence
reads it. Reinventing the format buys nothing; the value this skill adds is
lifecycle and traceability, which no template ships.

## Two tiers

Pick before writing. Most decisions are tier 2 and get written in five minutes.

| Tier | Use when | Template |
|---|---|---|
| **Full MADR** | irreversible, cross-module, or expensive to unwind | `templates/adr-madr.md` |
| **Y-Statement** | real decision, small blast radius, or migrating a decision that today only lives in Slack | `templates/adr-y-statement.md` |

Y-Statement, one sentence:

> In the context of **{use case}**, facing **{concern}**, we decided for
> **{option}**, to achieve **{quality}**, accepting **{downside}**.

A Y-Statement is a legitimate ADR, not a placeholder. Half a page that exists
beats two pages that never got written. It also makes an excellent executive
summary at the top of a full MADR.

**Migrating history.** Decisions that today live in a Slack thread or a
voicenote are worth capturing as Y-Statements with the original date. Set `date:`
to when the decision was actually made, and note the source in `More
Information`. A dated record of a decision made eight months ago is far more
useful than no record at all.

## Numbering and creation

Resolve the repo profile first — it supplies `docs.adr`, what a component is
here, whether there is a variant axis, and which sibling repos a decision may
bind:

```bash
bash ~/.claude/skills/spec-flow/scripts/repo-profile.sh
```

```bash
mkdir -p docs/adr
next=$(ls docs/adr 2>/dev/null | grep -oE '^ADR-[0-9]{4}' | grep -oE '[0-9]{4}' | sort -n | tail -1)
printf 'ADR-%04d\n' $(( 10#${next:-0} + 1 ))
```

Four digits, monotonic, never reused. A rejected ADR keeps its number and stays
in the tree — that a decision was considered and refused is itself a decision.

## Frontmatter — the part that makes the corpus usable

```yaml
---
id: ADR-0007
title: Single ledger account with reclassification in the ERP service
status: accepted        # proposed | accepted | rejected | deprecated | superseded
date: 2026-08-26
deciders: [William Eckerleben]
consulted: [Contabilidad]
informed: []
rfc: RFC-0004           # null if the decision predates or bypasses an RFC
supersedes: null
superseded_by: null
variant: [v16, v19]     # omit the key entirely when variant_axis is none
components: [cashea_allies_balance_report]
affects_repos: []       # sibling repos this decision also binds
tags: [ledger, accounting, bnpl]
---
```

`components`, `variant` and `affects_repos` are the local additions and the
reason this skill exists. Plain MADR cannot answer "what has already been decided
about this component", which is the only question anyone actually asks of an ADR
corpus.

- **`components`** is whatever the repo's unit is — an Odoo module, a Python
  package, a TS workspace under `src/`, a Terraform stack. Never blank.
- **`variant`** is omitted when the profile says `variant_axis: none`. Do not
  write `n/a`; a key that is always `n/a` stops being read.
- **`affects_repos`** is answered explicitly, including when the answer is empty.
  A decision in one repo that silently binds another is the failure this field
  exists to prevent.

## Writing rules

- **The title is the decision, not the topic.** "Single ledger account with
  reclassification in the ERP service", not "Ledger accounts". A reader scanning
  the index must learn the outcome without opening the file.
- **State the decision in the present tense, as a fact.** "We use X." Not "we
  will use" or "it was decided that".
- **Considered options need at least two,** each with honest pros and cons. The
  rejected option written charitably is the most valuable paragraph in the
  document — six months on, someone will propose it again, and this is the only
  thing that stops the discussion from restarting from zero.
- **Consequences include the bad ones.** An ADR with only good consequences is
  marketing. Name what got worse; that is what the next person needs.
- **Confirmation is mandatory** (MADR 4.0.0 field): how do we know the decision
  is actually being followed? A test, a lint rule, a CI check, a code review
  item, or an honest "nothing enforces this — it decays silently". A decision
  nothing enforces erodes, and saying so is more useful than pretending.
- **English** (the profile's `language.adr` default). The ADR sits beside code
  and outlives the conversation. Quote requirements verbatim in their original
  language inside blockquotes; do not translate them.

## Superseding

Never edit an accepted ADR's decision. To change it:

1. Write a new ADR with the next number, `supersedes: ADR-NNNN`.
2. In the old file, change **only** `status: superseded` and
   `superseded_by: ADR-MMMM`. Touch nothing else — the body is the record of
   what was true then.
3. Regenerate the index.
4. Grep the `components` listed in the old ADR for code that still follows it,
   and do the same in every repo in its `affects_repos`. The supersede is not
   done until the code agrees or a follow-up ticket exists.

`deprecated` is different from `superseded`: deprecated means the decision no
longer applies and nothing replaced it (the driver disappeared). The FI 90-day
provision is the shape of this — the operation stopped doing it, so no new
decision was needed.

## Index

`docs/adr/README.md` is generated, never hand-edited. Regenerate after every
write:

```bash
bash ~/.claude/skills/adr-author/scripts/adr-index.sh
```

The index is what keeps the corpus alive. Without it nobody finds the earlier
decision and the same argument gets had again — the single most common failure
mode of ADR adoption, and the reason `adr-log` exists in the wider ecosystem.

## Answering "what did we already decide about X"

Before proposing anything in an RFC or a plan, query the corpus:

```bash
grep -l "components:.*<component>" docs/adr/*.md
grep -ri "<topic>" docs/adr/ --include='*.md' -l
awk '/^status:/ && !/accepted/ {print FILENAME}' docs/adr/ADR-*.md   # non-accepted
```

When the profile lists sibling repos, query theirs too — the binding decision may
live over there:

```bash
for r in <sibling repos>; do grep -l "affects_repos:.*$(basename $PWD)" ../$r/docs/adr/*.md; done
```

Report matches as **constraints**, not suggestions. An accepted ADR is binding
until superseded; if the current work contradicts it, that contradiction is the
thing to surface, not something to route around quietly.

## Output

```
ADR written: docs/adr/ADR-NNNN-{slug}.md

Decision:  {title}
Tier:      {full MADR | Y-Statement}
Status:    {status}
RFC:       {RFC-NNNN | none}
{eje}:     {variants}      # línea omitida si variant_axis es none
Componentes:{list}
Binds:     {sibling repos | —}
Supersedes: {ADR-NNNN | —}
Confirmation: {test | lint | CI | review | nothing enforces this}

Index regenerated: docs/adr/README.md ({n} ADRs, {n} accepted, {n} superseded)
{if supersedes: "Pendiente: revisar {modules} — el código puede seguir el ADR viejo"}
```

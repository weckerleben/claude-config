---
id: ADR-NNNN
title: <the decision as a noun phrase — the outcome, not the topic>
status: proposed          # proposed | accepted | rejected | deprecated | superseded
date: YYYY-MM-DD          # when the decision was MADE, not when it was written
deciders: []
consulted: []
informed: []
rfc: RFC-NNNN             # null if the decision predates or bypasses an RFC
supersedes: null
superseded_by: null
variant: []               # omit this key entirely when variant_axis is none
components: []
affects_repos: []
tags: []
---

# ADR-NNNN — <title>

> In the context of **<use case>**, facing **<concern>**, we decided for
> **<option>**, to achieve **<quality>**, accepting **<downside>**.

## Context and Problem Statement

Two or three sentences. What forced a decision here? What breaks if nothing is
decided? Link the RFC rather than restating its design.

If a requirement drove this, quote it verbatim — do not translate:

> WHEN ... THE SYSTEM SHALL ...

## Decision Drivers

What actually decided it. Ordered by weight, and honest — "el equipo ya conoce
esta herramienta" is a legitimate driver and pretending otherwise makes the
record useless.

- <driver>
- <driver>

## Considered Options

- **Option 1** — <one line>
- **Option 2** — <one line>
- **Option 3** — <one line, often "do nothing / keep the current behavior">

## Decision Outcome

Chosen: **Option N**, because <the deciding argument in one or two sentences>.

### Consequences

**Good**
- <what gets better, concretely>

**Bad**
- <what gets worse, what debt this takes on, what it forecloses>

An empty "Bad" list means the analysis is incomplete, not that the option is
perfect.

### Confirmation

How we know this decision is actually being followed:

- <a test, a lint rule, a CI check, a review checklist item>
- or, honestly: `nothing enforces this — it will decay silently`

## Pros and Cons of the Options

### Option 1 — <name>

- Good, because <…>
- Good, because <…>
- Bad, because <…>
- Cost to reverse: <low | medium | high — and what specifically has to be undone>

### Option 2 — <name>

Write the rejected option charitably. Someone will propose it again; this
paragraph is what keeps that conversation from starting at zero.

- Good, because <…>
- Bad, because <…>
- Cost to reverse: <…>

## Variant impact

<!-- Delete this whole section when the repo profile says variant_axis: none. -->

| <variant> | Applies | Notes |
|---|---|---|
| | yes / no / differently | |

If the decision holds for one variant but not another, that is two decisions —
split them into two ADRs rather than qualifying one.

## Sibling repos

<!-- Only when the profile declares sibling_repos. Answer even when the answer
     is "none" — a repo silently bound by a decision it never saw is the failure
     this section prevents. -->

| Repo | Bound | Follow-up |
|---|---|---|

## More Information

- RFC: `docs/rfc/RFC-NNNN-<slug>.md`
- PRD: `.claude/prds/<slug>.prd.md`
- Code: `path:line`
- Ticket: ODOO-NNN
- Source, if this decision was migrated from elsewhere: <Slack thread, Notion page, meeting date>

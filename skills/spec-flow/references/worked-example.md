# Worked example — Core Ledger BNPL

A real chain, using decisions that were actually taken. Shows the language rule
(PRD/RFC Spanish, ADR English), the trace links, and what each artifact is
allowed to contain.

Repo profile in play — `cashea-odoo`, stack `odoo`, `variant_axis: odoo_version`,
variants `[v16]`, sibling `cashea-odoo-v19 (v19)`. A repo with
`variant_axis: none` produces the same chain minus every `variant:` key and the
variant section; nothing else changes.

---

## 1. PRD — `.claude/prds/core-ledger-eventos.prd.md`

Excerpt. Note the EARS requirements: `/plan-prd` produces the problem statement,
the EARS block is the upgrade `spec-flow` requires before an RFC can consume it.

```markdown
---
id: PRD-core-ledger-eventos
status: approved
ticket: ODOO-412
rfcs: [RFC-0004]
published: https://app.notion.com/p/3a633f1216f780f4a27ec1719523e22d
---

## Problema
El Core Ledger tiene que emitir asientos que espejen CxC, CxP y banco contra
Odoo. Hoy el asiento del reporte FCB sale con 2 líneas (activo subyacente /
pasivo aliado) y no cubre servicio tecnológico, lending fee ni cupones, así que
la conciliación se completa a mano.

## Requisitos

WHEN se paga el down payment de una orden FCB,
THE SYSTEM SHALL emitir E1 con una línea por cuota.

WHEN una cuota activa se cobra,
THE SYSTEM SHALL emitir E4 contra la transitoria de pagos pendientes de aplicar.

IF una orden cancelada ya fue neteada por la compensación semanal,
THEN THE SYSTEM SHALL no emitir un segundo asiento por E7.

## Fuera de alcance
- Subsidios (Cashea envíos) — se resuelve como ajuste de liquidación
- CFB / debt facility y emisión de certificado — post-MVP
- Refinanciamiento y reestructuración — pendiente de relevar con Contabilidad
```

Note what is **not** there: no mention of accounts, no event catalog, no
schema. That is the RFC's job.

---

## 2. RFC — `docs/rfc/RFC-0004-catalogo-eventos-core-ledger.md`

The options table is the part that matters — it is the raw material for the ADRs.

```markdown
---
id: RFC-0004
title: Catálogo de eventos del Core Ledger para el MVP BNPL
status: accepted
prd: .claude/prds/core-ledger-eventos.prd.md
adrs: [ADR-0001, ADR-0002]
ticket: ODOO-412
variant: [v16, v19]
components: [cashea_allies_balance_report, cashea_account_factoring]
affects_repos: [cashea-odoo-v19, erp-service]
---

## No-objetivos
- No cambiamos la granularidad de los postings: sigue siendo **por cuota**,
  exigido por la trazabilidad de liquidación.
- No tocamos la conciliación bancaria. El "dos pasos" que se agrega es sobre el
  eje de asignación, no sobre el bancario.
- No modelamos refinanciamiento ni reestructuración.

## Opciones consideradas — granularidad de event_type para cobros

| # | Opción | A favor | En contra | Costo de revertir |
|---|---|---|---|---|
| 1 | **Un solo event_type de cobro** ✅ | El árbol de 4 dimensiones resuelve cuenta o agrega líneas, no eventos | Obliga al consumidor a leer campos, no solo el tipo | Bajo |
| 2 | 58 event_types (9 NV + 11 VM + 2 EB + 12×3 monto) | Cada combinación es explícita en el nombre | 58 contratos que versionar; cualquier dimensión nueva multiplica | Alto |
| 3 | ~6 con campos condicionales | Punto medio | El criterio para cuándo es campo y cuándo es evento queda sin definir | Medio |

**Por qué la 1**: las 4 dimensiones del árbol resuelven cuenta contable o
agregan líneas al asiento — ninguna cambia la naturaleza del hecho económico.
Ver ADR-0001.

## Criterios de Aceptación

WHEN se cobra una cuota viva,
THE SYSTEM SHALL emitir exactamente un evento E4, con las dimensiones como campos.

WHEN se cobra una cuota ya castigada,
THE SYSTEM SHALL emitir E6 sin tocar la CxC.

## Decisiones
| ADR | Decisión | Estado |
|---|---|---|
| ADR-0001 | Un event_type por cobro, dimensiones como campos | accepted |
| ADR-0002 | Recepción y asignación del pago como dos eventos | accepted |
```

---

## 3. ADR — `docs/adr/ADR-0001-one-event-type-per-collection.md`

English, because it lives beside the code. The rejected option is written
charitably — that paragraph is the whole point.

```markdown
---
id: ADR-0001
title: One event type per collection, dimensions as fields
status: accepted
date: 2026-08-26
deciders: [William Eckerleben]
consulted: [Contabilidad]
rfc: RFC-0004
variant: [v16, v19]
components: [cashea_allies_balance_report]
affects_repos: [cashea-odoo-v19]
tags: [ledger, events, bnpl]
---

> In the context of the Core Ledger event catalog, facing an annex that proposed
> 58 collection event types, we decided for a single event type per collection
> state, to keep the contract surface small, accepting that consumers must read
> fields rather than switch on the event name.

## Context and Problem Statement
The FCB-7 annex enumerated 58 event types for collections (9 NV + 11 VM + 2 EB +
12×3 by amount) and left open whether the answer was 58 or roughly 6 with
conditional fields.

## Decision Drivers
- Every event type is a contract that has to be versioned and consumed.
- The four dimensions in the decision tree resolve to an **account** or to extra
  **lines**, never to a different economic fact.
- A new dimension multiplies the catalog under option 2 and does not under 1.

## Decision Outcome
Chosen: one event type per collection state — **E4** for a live installment,
**E6** for a charged-off one.

### Consequences
**Good**
- Two contracts instead of 58. A new dimension adds a field, not 12 events.
- The distinction that does matter — whether the receivable is still open — is
  the one thing the event name carries.

**Bad**
- A consumer cannot route on the event name alone; it must read `entry_type` and
  the order model. Anything that subscribes selectively pays for this.

### Confirmation
Contract test asserting the published catalog holds exactly the MVP event types.
Any PR adding a collection event type fails it and has to supersede this ADR.

## Pros and Cons of the Options

### Option 2 — 58 explicit event types
- Good, because a subscriber can filter on the name and receive only what it
  needs, with no payload inspection at all.
- Good, because the catalog is self-documenting — the taxonomy is visible.
- Bad, because the dimensions are orthogonal, so the count is a product, not a
  sum; a fifth dimension takes it past 100.
- Cost to reverse: high — every consumer's subscription list has to change.

## Variant impact
| odoo_version | Applies | Notes |
|---|---|---|
| v16 (`cashea-odoo`) | yes | `top_up_move_type` values map onto E4/E6 |
| v19 (`cashea-odoo-v19`) | yes | same contract; the rewrite must not re-expand |

## Sibling repos
| Repo | Bound | Follow-up |
|---|---|---|
| `cashea-odoo-v19` | yes | the migration must not re-expand the catalog |
| `erp-service` | yes | reclassification consumes `entry_type`, not the event name |
```

The `Variant impact` and `Sibling repos` sections exist here because the profile
declares an axis and siblings. In `erp-service` the same ADR would carry neither
— the sections are deleted, not left blank.

---

## 4. Plan — `/plan docs/rfc/RFC-0004-catalogo-eventos-core-ledger.md`

`/plan` reads the RFC and copies ADR constraints verbatim, so the implementer
never has to re-derive them:

```yaml
---
rfc: RFC-0004
adrs: [ADR-0001, ADR-0002]
constraints_from_adr:
  - "ADR-0001: exactly two collection event types (E4 live, E6 charged-off).
     A new dimension is a field, never a new event."
  - "ADR-0002: payment reception (E4a) and assignment (E4) are separate events.
     Do not collapse them."
---
```

---

## What each artifact refused to contain

| Artifact | Kept out | Why |
|---|---|---|
| PRD | accounts, event names, schema | that is design; it changes without the problem changing |
| RFC | the argument against the 58-event option | it is settled — it lives in ADR-0001 forever |
| ADR | the current state of the catalog | the ADR is a snapshot of one decision, not a spec |
| Plan | rationale of any kind | it exists to be executed, not read |

The discipline that keeps this working: **the PRD and RFC are rewritten in place
and always show today's state; the ADR is append-only and shows what was true on
a date.** Every piece of "por qué no la otra opción" goes in the ADR — which is
the only reason the RFC can stay clean.

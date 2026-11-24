---
name: postmortem-finplat
description: Write, review or tighten a blameless postmortem for an incident in the Financial Platform vertical (ex Fintech Ops, Finance, Core Ledger, Odoo, payouts, reports, data pipelines), following the vertical's Incident Management guide and the 8-section "Cashea Standard Post-mortem". Use whenever the user says "armá el postmortem", "post mortem de X", "escribí el postmortem del incidente", "qué pasó con X y dejalo documentado", "necesito el template de postmortem", "revisá este postmortem", or pastes logs, a timeline, an incident.io export or a Slack thread and wants the write-up, even if they never say "postmortem". Also use to decide if an incident needs one (severity and deadline). Do NOT use for the bi-weekly postmortem slides (cashea-postmortem-presentation), for diagnosing a live Odoo incident from logs (odoo-incident-rca), or for RFC/ADR/PRD (rfc-author, adr-author).
---

# Postmortem — Financial Platform

A postmortem exists so the same failure does not happen twice. It is blameless: it looks for the cause in the system (config, design, missing alert, missing process), never in a person. A reader who skims only the Summary and the Follow-ups must still learn what broke, who was hit, and what will change.

Source of truth: Notion → *Vertical: Financial Platform → Incident Management - Finance → 7. Postmortems* and *2. Severidades*. Real examples live in the *Financial Platform Document Hub* (Type = Post Mortem). The section template is in `references/template.md`; read it before drafting.

## 1. Decide if it is needed

| Severity | Postmortem | Deadline |
| --- | --- | --- |
| SEV-1, SEV-2 | Mandatory | ≤ 7 days |
| SEV-3 | Recommended if detection or communication had gaps | ≤ 14 days |
| SEV-4/5 | Not required | — |

It is also due when the same failure pattern happened before, or when partners received wrong financial information. If the severity is unknown, derive it with the matrix in *2. Severidades* (report criticality × partners affected). That page's own thresholds disagree (200 / 50–199 / 0–49 partners in the axis table vs 5+ / 2–4 / 1 in the matrix). Do not pick one silently: state which one you used and flag the inconsistency to the user. When in doubt, take the higher severity.

## 2. Gather before you write

Ask only for what you cannot find yourself. Use the logs, tickets, PRs, Slack threads and incident.io data the user points at (Notion, Jira, Slack and GitHub are reachable; for Odoo.sh runs use `odoo-incident-rca` to anchor the cause in the real logs). You need: first signal and resolution times with timezone, who and what was affected and how many, what was done in order (including failed attempts), the evidence for the cause, and the tickets or PRs involved.

Separate three things in your head, and in the document:
- **Demonstrated**: seen in a log line, query, config or metric you can cite.
- **Inferred**: deduced from a pattern. Say so in a callout and say what would confirm it.
- **Unknown**: not determinable with current telemetry. Write it down and turn it into a Follow-up (for example "enable parameter logging so the trigger is attributable"). An honest "unknown" is worth more than a confident guess.

## 3. Write it

Use the 8 sections of `references/template.md`, in that order. Rules that make the difference:

- **Length.** The prose (Summary, Root Causes, Resolution, Lessons) is 1 to 1½ pages. Tables, timeline, code blocks, queries, log excerpts and the evidence stay complete: reviewers ask for them. Cut prose, never evidence.
- **Summary** is 3–5 sentences: what happened, who was affected, how it was fixed, how it is prevented. No jargon without a gloss.
- **Timeline** is chronological from the first signal to resolution, one timezone stated in the header. Include the dead ends; they teach the most.
- **Root Causes** goes from the technical cause down to the systemic one (a short Five Whys). Answer explicitly: was it generated in DATA, ingested in Odoo, or both? Why was it not detected earlier? Which reports and partners saw the wrong data?
- **Say each thing once.** State a claim's confidence in one place (inline tag or one small table), and do not restate the same fact in the Five Whys, the pipeline questions and a table. Leave a `<por completar>` only where the user must supply data; do not pad with placeholders.
- **Lessons Learned**: what went well, what went badly, one or two sentences each.
- **Follow-ups** is where postmortems usually die. Each action needs a **single owner**, a **tracking ticket** and a **verifiable end state** ("alert X exists and fired in test", not "improve monitoring"). Tag each as Fix, Detection, Improvement or Investigation. An action with owner "TBD" or no ticket is not done: list it separately under "Needs owner" and tell the user.
- **Catalog Validation** for SEV-1/2: the affected service has a correct owner, an updated runbook and an updated dashboard. Tick only what you verified.
- **Appendix**: links to dashboards, tickets, PRs, the incident.

Language: Spanish by default (the Hub's postmortems are Spanish), technical identifiers verbatim. If the user asks for English, use English throughout. For Spanish text meant to be shared, also apply the `sin-slop` skill if it is available.

## 4. Deliver

Show the draft in chat as rendered markdown first. Publishing to Notion is an outward-facing action: create the page only after the user says yes, in the Financial Platform Document Hub *Documents* database (data source `collection://35533f12-16f7-8063-a259-000bec0fda3e`) with properties Type = `Post Mortem`, Squad = the owning squad, Status = `Not started`, and Áreas afectadas if known. Do not send Slack messages or move Jira tickets unless asked.

End your reply with the open points: unverified claims, missing owners or tickets, and any section you left empty on purpose.

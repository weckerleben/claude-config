# Postmortem template (8 sections)

Based on "Cashea Standard Post-mortem" (incident.io) and the Financial Platform guide *7. Postmortems*. Reference: Google SRE, "Postmortem Culture". Duplicate this structure; delete helper text in `<...>`.

Title: `Post mortem — <short title> (<YYYY-MM-DD>)`

| Field | Value |
| --- | --- |
| Date | `<YYYY-MM-DD>` |
| Severity | `<SEV-1..5>` and the matrix cell used |
| Author | `<name>` |
| Impact | `<one line: who/what, how long>` |
| Context | `<ticket, PR, RFC>` |

## 1. Summary
`<3–5 sentences: what happened, who was affected, how it was resolved, how it is prevented.>`

## 2. Timeline (`<timezone>`)
| Time | Event | Actor |
| --- | --- | --- |
| `<HH:mm>` | First signal (alert, user report, dashboard) | |
| `<HH:mm>` | Triage, each mitigation attempt (including failed ones), fix, close | |

## 3. Root Causes
- **Technical cause**: `<file, query, config, log line. Quote the decisive evidence.>`
- **Five Whys**: 1 … 5, ending in a systemic cause (process, design, missing alert).
- **Pipeline questions**: generated in DATA, in Odoo ingestion, or both? Why was it not detected earlier? Did the alarm come from DATA or late through Odoo? Which reports and partners were exposed to the wrong data?
- **Confidence**: mark each claim Demonstrated / Inferred / Unknown. Inferred claims get a callout saying what would confirm them.

## 4. Resolution
`<What stopped the bleeding, what fixed the cause, and how it was verified.>`

## 5. Lessons Learned
- **Went well**: `<…>`
- **Went badly**: `<…>`
- **Could it have been detected earlier? How?**: `<concretize as a Detection follow-up>`

## 6. Follow-ups
| # | Action | Type (Fix / Detection / Improvement / Investigation) | Owner (one) | Ticket | Verifiable end state |
| --- | --- | --- | --- | --- | --- |
| 1 | | | | | |

An action without owner, ticket and verifiable end state goes under **Needs owner**, not in this table.

## 7. Catalog Validation (SEV-1/2)
- [ ] The affected service has the correct owner.
- [ ] The runbook is updated.
- [ ] The dashboard is updated.

## 8. Appendix
`<Links: dashboards, tickets, PRs, incident.io, Slack thread, queries.>`

---
Process after the draft: share with responders, hold a debrief with key participants, assign actions in incident.io, export to Notion, post the link in Slack.

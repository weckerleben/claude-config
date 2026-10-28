# Trace format

One file per trace: `~/.claude/self-improvement/traces/<id>.md`. `id` is the miner's `c-xxxxxxxx` or `live-YYYYMMDD-n` for captures during a session.

```markdown
---
id: c-1a2b3c4d
scope: user            # local | user | skill | project | system
confidence: high       # low | medium | high — how sure the evidence supports a general rule
status: pending        # pending | applied | rejected | routed
promotion_condition: repeated   # explicit | repeated | evidence | none
target_surfaces: [~/.claude/CLAUDE.md]
sessions: [8a6fba05.jsonl, 1c2d3e4f.jsonl, 9f8e7d6c.jsonl]
---

## His words (verbatim)
> No estás en el proyecto correcto me parece. Verificá siempre eso primero

## What I had just done
<the assistant output he reacted to, quoted or tightly summarized from `prior_assistant`>

## Why (only if he stated it)
<his reason, or "not stated">

## Proposed rule
<one imperative sentence, same meaning as the quote, nothing added>
```

Rules for the file:
- "His words" is copied from the candidate's `text`, unedited.
- "Proposed rule" may not contain a condition, exception or reason that is not in the evidence.
- When a trace is applied, set `status: applied` and add the entry id from `applied-changes.md`.

## review-queue.md

```markdown
# Review queue
- [~] c-1a2b3c4d — verify the project before acting (1 session; needs 2 more or explicit approval)
```

## applied-changes.md

```markdown
## 2026-10-28 — ~/.claude/CLAUDE.md
Traces: c-1a2b3c4d, c-5e6f7a8b
Before: <old text or "absent">
After: <new text>
```

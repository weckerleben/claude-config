# Audit mode: is my CLAUDE.md earning its place?

Goal: fewer, sharper instructions. Every always-loaded line costs tokens on every turn and dilutes the lines that matter. Subtract before you add.

Nothing is edited without William's "sí" per item (hard rule 1). Output is a list of cards.

## 0. Inventory
List what is loaded or can load: `~/.claude/CLAUDE.md`, the project CLAUDE.md, `~/.claude/rules/**`, skill descriptions, hooks in `settings.json`, memory index. Report size per file (characters ÷ 3 ≈ tokens, HTML comments stripped). Flag always-loaded files that are large.

## 1. Removal pass (do this first)
For each rule, ask whether it earns its place:
- **Default behavior**: the model already does it without being told.
- **Duplicate**: same rule elsewhere. Prove it with a grep and cite `file:line`. Zero matches means the rule is not duplicated: move it, do not delete it.
- **Stale**: refers to a tool, project or decision that no longer exists (check the path or command).
- **Contradiction**: two files say opposite things. Surface both lines.
- **Enforced elsewhere**: a hook already blocks or reminds; the prose is redundant.
- **`review_after` due**: an entry in `applied-changes.md` whose date passed. Check whether the rule is still wanted and whether it held (see step 3).

## 2. Violation check
For each rule that matters, look for transcript evidence it was ignored: he corrected something that was already written down. Run the miner and compare candidates against the rule text. Quote both turns (his correction and what the assistant had done). No quotes, no finding.

Route each violated rule:
1. Ambiguous wording → reword the existing line.
2. Violated twice or more despite clear wording → a structural barrier (hook, commit-msg check, setting). Capital letters are not a fix.
3. Wrong home (applies to one project or file type) → move to that CLAUDE.md or a `paths:`-scoped rule.

## 3. Drift check of earlier changes
For each entry in `applied-changes.md`: **Verified** (still present and followed), **Drifted** (present but violated since), **Missing** (gone from the file). Report counts and the drifted ones.

## 4. Present
One card per proposed change: what, why, evidence (file:line or quotes), the proposed diff. Removals first, then rewrites, then additions. Also run `scripts/skill_usage.py` and add a card per never-used skill (proposal only; a reversible move to `~/.claude/self-improvement/pruned/<date>/`, never a delete).

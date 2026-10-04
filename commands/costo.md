---
description: Show this session's cost and tokens (with the safety margin), or the latest sessions with --all
argument-hint: "[--all] [--limit N] [--session <id>] [--json]"
allowed-tools: Bash(node:*)
disable-model-invocation: true
---

# Session cost

!`node "$HOME/.claude/scripts/weck/cost-report.js" $ARGUMENTS`

Show the report above exactly as printed, in a code block, and add nothing else.
The amounts already include the safety margin configured in
`scripts/weck/pricing.json`; do not recompute or round them.

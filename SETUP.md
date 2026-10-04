# Setup on a new machine

Requirements: `git`, `node` 18+, `python3`, the `claude` CLI and `gh`.

1. Log in with the personal GitHub account (HTTPS):

   ```bash
   gh auth login --hostname github.com --git-protocol https --web
   ```

2. Clone this repo as `~/.claude`. If `~/.claude` already exists, move it away first.

   ```bash
   git clone https://github.com/weckerleben/claude-config.git ~/.claude
   ```

3. Run the bootstrap:

   ```bash
   ~/.claude/bootstrap.sh
   ```

   Use `--dry-run` to preview and `--skip-cashea` on machines without access to
   the `cashea-bnpl` organization.

4. Restart Claude Code.

## What the bootstrap does

- Clones ECC into `~/dev/ecc` and checks out the pinned `ECC_REF`.
- Installs the `ecc@ecc` plugin from that local clone (not from the GitHub marketplace).
- Installs ECC rules into `~/.claude/rules/ecc`.
- Registers the Cashea marketplace and its plugins.
- Sets the repo's local git identity and the `gh` credential helper.

## Updating ECC

Bump `ECC_REF` in `bootstrap.sh`, commit, and re-run the bootstrap on each machine.

## Disabled ECC hooks

`env.ECC_DISABLED_HOOKS` in `settings.json` turns off the tmux reminders, the
git push reminder and the gateguard fact-force hook.

## Statusline, session cost and compact advisor

Code lives in `scripts/weck/` and is wired in `settings.json` (`statusLine` and a
`UserPromptSubmit` hook). ECC's own `pre:edit-write:suggest-compact` and
`stop:cost-tracker` hooks are disabled through `ECC_DISABLED_HOOKS` because these replace them.

- **Cost**: computed from the session transcripts (main + subagents), counting each
  API message once, with cache reads and 5m/1h cache writes priced separately.
  Rates live in `scripts/weck/pricing.json` (source and fetch date inside). The shown
  amount is multiplied by `margin` (default 1.2). Override per shell with `WECK_COST_MARGIN`.
- **Unknown model**: priced at the most expensive tier and marked with `?`.
- **Compact advisor**: advises at 150k tokens, again every +100k, urgent at 300k
  (`compact` block in `pricing.json`). It hands the model a ready-to-paste
  `/compact <instructions>` command.
- **Updating rates**: edit `pricing.json` from https://platform.claude.com/docs/en/about-claude/pricing
  and bump `fetchedAt`. Cached totals are rebuilt automatically when the table changes.
- **Tests**: `node --test scripts/weck/tests/*.test.js`

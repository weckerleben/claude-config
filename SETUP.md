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

#!/usr/bin/env bash
# Bootstrap a fresh machine after cloning this repo into ~/.claude.
#
# Installs ECC from a pinned local clone (plugin + rules), registers the
# Cashea plugin marketplace and wires the repo's git identity.
# Idempotent: safe to re-run, also to move to a new ECC_REF.
#
# Usage: ./bootstrap.sh [--dry-run] [--skip-cashea]
#   ECC_DIR   where ECC is cloned        (default: ~/dev/ecc)
#   ECC_REF   ECC commit/tag to install  (default: pinned below)
set -euo pipefail

ECC_REPO="https://github.com/affaan-m/ecc.git"
ECC_REF="${ECC_REF:-ef648e0}"
ECC_DIR="${ECC_DIR:-$HOME/dev/ecc}"
CLAUDE_DIR="${CLAUDE_DIR:-$HOME/.claude}"
GIT_NAME="${GIT_NAME:-William Eckerleben}"
GIT_EMAIL="${GIT_EMAIL:-wgre2000@gmail.com}"

DRY_RUN=0
SKIP_CASHEA=0
for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=1 ;;
    --skip-cashea) SKIP_CASHEA=1 ;;
    -h|--help) sed -n '2,12p' "$0"; exit 0 ;;
    *) echo "unknown option: $arg" >&2; exit 2 ;;
  esac
done

step() { printf '\n==> %s\n' "$*"; }
warn() { printf 'WARN: %s\n' "$*" >&2; }
die()  { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
run()  { if [ "$DRY_RUN" = 1 ]; then printf '[dry-run] %s\n' "$*"; else "$@"; fi; }

step "Checking prerequisites"
for bin in git node npm claude python3; do
  command -v "$bin" >/dev/null 2>&1 || die "missing required command: $bin"
done
node_major="$(node -p 'process.versions.node.split(".")[0]')"
[ "$node_major" -ge 18 ] || die "Node 18+ required (found $(node -v))"
[ "$(cd "$CLAUDE_DIR" && pwd -P)" = "$(cd "$HOME/.claude" && pwd -P)" ] \
  || warn "CLAUDE_DIR is not ~/.claude; plugin commands still target ~/.claude"

step "Syncing ECC at $ECC_DIR (ref $ECC_REF)"
if [ -d "$ECC_DIR/.git" ]; then
  if [ "$(git -C "$ECC_DIR" rev-parse --is-shallow-repository)" = "true" ]; then
    run git -C "$ECC_DIR" fetch --unshallow --tags origin
  else
    run git -C "$ECC_DIR" fetch --tags origin
  fi
else
  run mkdir -p "$(dirname "$ECC_DIR")"
  run git clone "$ECC_REPO" "$ECC_DIR"
fi
run git -C "$ECC_DIR" checkout --detach "$ECC_REF"

step "Installing ECC plugin from the local clone"
if claude plugin marketplace list 2>/dev/null | grep -qE '(^|[[:space:]])ecc([[:space:]]|$)'; then
  run claude plugin marketplace update ecc
else
  run claude plugin marketplace add "$ECC_DIR"
fi
if claude plugin list 2>/dev/null | grep -q 'ecc@ecc'; then
  run claude plugin update ecc@ecc || warn "plugin update reported a problem (already current?)"
else
  run claude plugin install ecc@ecc
fi
if [ "$DRY_RUN" = 0 ]; then
  echo '{"hooks_enabled":"true","hook_profile":"standard"}' | claude plugin configure ecc@ecc --values-stdin
else
  echo '[dry-run] claude plugin configure ecc@ecc (hooks_enabled=true, hook_profile=standard)'
fi

step "Installing ECC rules (plugins do not ship rules)"
run "$ECC_DIR/install.sh" --target claude --modules rules-core --no-hooks

if [ "$SKIP_CASHEA" = 0 ]; then
  step "Registering Cashea marketplace (needs access to cashea-bnpl on GitHub)"
  if run claude plugin marketplace add cashea-bnpl/cashea-skills; then
    for plugin in cashea-engineering cashea-marketplace cashea-hub cashea-web; do
      run claude plugin install "$plugin@cashea-skills" || warn "could not install $plugin"
    done
  else
    warn "Cashea marketplace unavailable; log in with the Cashea gh account and re-run, or use --skip-cashea"
  fi
  run claude plugin install frontend-design@claude-plugins-official || warn "could not install frontend-design"
fi

step "Configuring this repo's git identity and credentials"
if [ -d "$CLAUDE_DIR/.git" ]; then
  [ -n "$(git -C "$CLAUDE_DIR" config --local user.name || true)" ]  || run git -C "$CLAUDE_DIR" config user.name "$GIT_NAME"
  [ -n "$(git -C "$CLAUDE_DIR" config --local user.email || true)" ] || run git -C "$CLAUDE_DIR" config user.email "$GIT_EMAIL"
  run git -C "$CLAUDE_DIR" config credential.helper '!gh auth git-credential'
else
  warn "$CLAUDE_DIR is not a git repo; skipped identity setup"
fi

if [ "$DRY_RUN" = 0 ]; then
  step "Verifying"
  claude plugin list 2>/dev/null | grep -A3 'ecc@ecc' || warn "ecc@ecc not listed"
  ls "$CLAUDE_DIR"/plugins/cache/ecc/ecc/*/hooks/hooks.json >/dev/null 2>&1 \
    || warn "ECC plugin hooks.json not found in plugin cache"
  [ -d "$CLAUDE_DIR/rules/ecc/common" ] || warn "ECC rules missing"
fi

printf '\nDone. Restart Claude Code to load the plugin hooks.\n'

#!/usr/bin/env bash
# repo-profile — resolve the spec-flow profile for a repository.
#
# Reads .claude/spec-flow.yml if it exists. Otherwise infers a profile from the
# repo's own markers and prints it, so the chain works in a repo nobody has
# configured. Inferred values are marked; declared values are authoritative.
#
# Usage: repo-profile.sh [repo-dir]     (default: git root of cwd)
set -uo pipefail

DIR="${1:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
cd "$DIR" || { echo "no such directory: $DIR" >&2; exit 1; }

PROFILE=".claude/spec-flow.yml"
if [ -f "$PROFILE" ]; then
  echo "# source: $DIR/$PROFILE (declared)"
  cat "$PROFILE"
  exit 0
fi

name=$(basename "$DIR")
remote=$(git remote get-url origin 2>/dev/null | sed 's#.*[:/]\([^/]*/[^/]*\)$#\1#; s/\.git$//')
branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null)

has() { find . -maxdepth 3 -name "$1" -not -path "./node_modules/*" -not -path "./.venv/*" \
        -not -path "./.git/*" 2>/dev/null | head -1; }

stack="unknown"; axis="none"; variants=""; components=""

if [ -n "$(has __manifest__.py)" ]; then
  stack="odoo"
  axis="odoo_version"
  # Repo name suffix is the most reliable signal; manifest versions are mostly '1.0'.
  case "$name" in
    *v19*|*19) variants="v19" ;;
    *v16*|*16) variants="v16" ;;
    *) variants=$(grep -ho "'version': *'\([0-9]\{2\}\)\.0" */__manifest__.py 2>/dev/null \
                  | grep -o "[0-9]\{2\}\.0" | sort | uniq -c | sort -rn | head -1 \
                  | awk '{print "v" substr($2,1,2)}') ;;
  esac
  [ -n "$variants" ] || variants="UNKNOWN — declare it"
  components=$(for d in */__manifest__.py; do [ -e "$d" ] && dirname "$d"; done | sort | head -200)

elif [ -f package.json ]; then
  stack="node-service"
  components=$(ls -d src/*/ 2>/dev/null | sed 's#/$##' | head -50)

elif [ -f pyproject.toml ] || [ -f requirements.txt ]; then
  stack="python-service"
  [ -d alembic ] && stack="python-service (with migrations)"
  components=$(find . -maxdepth 2 -name "__init__.py" -not -path "./.venv/*" -not -path "./tests/*" \
               2>/dev/null | xargs -n1 dirname 2>/dev/null | sed 's#^\./##' | sort -u | head -50)

elif [ -n "$(has '*.tf')" ]; then
  stack="terraform"
  axis="environment"
  variants=$(ls -d */ 2>/dev/null | sed 's#/$##' | grep -E '^(dev|qa|stg|staging|prod|production)$' | tr '\n' ' ')
  components=$(ls -d */ 2>/dev/null | sed 's#/$##' | head -50)
fi

[ -n "$components" ] || components="(none detected)"

cat <<YAML
# source: inferred from repo markers — nothing declared.
# Write .claude/spec-flow.yml to make any of this authoritative.
project: $name
repo: ${remote:-unknown}
branch: ${branch:-unknown}
stack: $stack                      # inferred
variant_axis: $axis                # inferred
variants: [$(echo "$variants" | tr -s ' ' | sed 's/ /, /g; s/, $//')]
sibling_repos: []                  # repos that must move together — declare, cannot be inferred
docs:
  rfc: docs/rfc
  adr: docs/adr
tracker: {}                        # declare: project key + field ids
language: {prd: es, rfc: es, adr: en}
components:                        # inferred, $(echo "$components" | grep -c . ) found
YAML
echo "$components" | sed 's/^/  - /'

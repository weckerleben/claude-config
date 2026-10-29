#!/usr/bin/env node
'use strict';

/**
 * PR-to-main gate (PreToolUse, Bash).
 *
 * In Odoo repos a PR to `main` is only opened once the Jira ticket is in
 * `A PRODUCCION`. A hook cannot read Jira, so it turns the rule into a
 * confirmation prompt (`ask`) every time `gh pr create` would target main,
 * which is also the default base when `--base` is omitted.
 */

const fs = require('node:fs');
const { execFileSync } = require('node:child_process');

const ODOO_REMOTE_RE = /cashea-odoo/i;
const PR_CREATE_RE = /\bgh\s+pr\s+create\b/;
const BASE_RE = /(?:--base[=\s]+|-B\s*)(\S+)/;

const REASON =
  'PR a `main` en un repo Odoo: solo se abre con el ticket en `A PRODUCCION`. ' +
  'Verificá el estado del ticket en Jira antes de aprobar. Si todavía no llegó ahí, ' +
  'la rama se queda en branch, commit y push, sin PR.';

function evaluatePrMainGate(command, remoteUrl) {
  if (!PR_CREATE_RE.test(command || '')) return null;
  if (!ODOO_REMOTE_RE.test(remoteUrl || '')) return null;
  const base = (command.match(BASE_RE)?.[1] || 'main').replace(/^['"]|['"]$/g, '');
  if (base !== 'main') return null;
  return { decision: 'ask', reason: REASON };
}

function originUrl(cwd) {
  try {
    return execFileSync('git', ['remote', 'get-url', 'origin'], {
      cwd,
      encoding: 'utf8',
      stdio: ['ignore', 'pipe', 'ignore'],
    }).trim();
  } catch {
    return '';
  }
}

function readStdin() {
  try {
    return fs.readFileSync(0, 'utf8');
  } catch {
    return '';
  }
}

function main() {
  let input = {};
  try {
    input = JSON.parse(readStdin() || '{}');
  } catch {
    process.exit(0); // never break the tool call on a parse error
  }
  const command = input.tool_input?.command || '';
  if (!PR_CREATE_RE.test(command)) process.exit(0);

  const result = evaluatePrMainGate(command, originUrl(input.cwd || process.cwd()));
  if (!result) process.exit(0);
  process.stdout.write(
    JSON.stringify({
      hookSpecificOutput: {
        hookEventName: 'PreToolUse',
        permissionDecision: result.decision,
        permissionDecisionReason: result.reason,
      },
    })
  );
}

if (require.main === module) main();

module.exports = { evaluatePrMainGate };

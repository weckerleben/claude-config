#!/usr/bin/env node
'use strict';

/**
 * PR-to-main gate (PreToolUse, Bash).
 *
 * In Odoo repos a PR to the production branch (`main` in v19, `master` in v16)
 * is only opened once the Jira ticket is in `A PRODUCCION`. A hook cannot read
 * Jira, so it denies `gh pr create` and tells Claude to check the ticket itself.
 * Once checked, Claude re-runs the command prefixed with
 * `CASHEA_TICKET_VERIFIED=<KEY>`, which is the only way through. The default
 * base when `--base` is omitted is the production branch, so it is covered too.
 */

const fs = require('node:fs');
const { execFileSync } = require('node:child_process');

const ODOO_REMOTE_RE = /cashea-odoo/i;
const PR_CREATE_RE = /\bgh\s+pr\s+create\b/;
const BASE_RE = /(?:--base[=\s]+|-B\s*)(\S+)/;
const PRODUCTION_BASES = new Set(['main', 'master']);
const VERIFIED_RE = /\bCASHEA_TICKET_VERIFIED=[A-Za-z]+-\d+\b/;

const REASON = [
  'PR a la rama de producción en un repo Odoo: solo se abre con el ticket en `A PRODUCCION`.',
  'Antes de reintentar, leé el ticket con `getJiraIssue` (la clave está en la rama o en el título del PR)',
  'y mirá su estado.',
  'Si NO está en `A PRODUCCION`: no abras el PR; la rama se queda en commit y push, y avisale a William.',
  'Si SÍ está: reintentá el mismo comando con el prefijo `CASHEA_TICKET_VERIFIED=<CLAVE>`,',
  'por ejemplo `CASHEA_TICKET_VERIFIED=EP-123 gh pr create ...`. No pongas el prefijo sin haber leído el estado.',
].join(' ');

function evaluatePrMainGate(command, remoteUrl) {
  if (!PR_CREATE_RE.test(command || '')) return null;
  if (!ODOO_REMOTE_RE.test(remoteUrl || '')) return null;
  const base = (command.match(BASE_RE)?.[1] || 'main').replace(/^['"]|['"]$/g, '');
  if (!PRODUCTION_BASES.has(base)) return null;
  if (VERIFIED_RE.test(command)) return null;
  return { decision: 'deny', reason: REASON };
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

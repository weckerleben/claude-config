#!/usr/bin/env node
'use strict';

/**
 * Ticket-key reminder (UserPromptSubmit).
 *
 * When a prompt mentions an `EP-123` / `ODOO-123` key, remind once per key per
 * session that working a ticket means moving it to In Progress first. Advisory
 * only; the rule itself lives in ~/.claude/CLAUDE.md.
 */

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const KEY_RE = /\b(?:EP|ODOO)-\d+\b/gi;

function findTicketKeys(prompt) {
  const keys = (prompt || '').match(KEY_RE) || [];
  return [...new Set(keys.map((k) => k.toUpperCase()))];
}

function buildTicketReminder(keys) {
  return [
    `Ticket detectado: ${keys.join(', ')}.`,
    'Si William pide trabajarlo, pasarlo a In Progress ANTES de escribir código o crear la rama',
    '(getTransitionsForJiraIssue + transitionJiraIssue), sin pedir permiso. Si ya está en In Progress',
    'o más adelante, no se retrocede.',
  ].join('\n');
}

function markerPath(sessionId) {
  return path.join(os.tmpdir(), `claude-ticket-reminder-${sessionId || 'nosession'}.json`);
}

function loadSeen(file) {
  try {
    return new Set(JSON.parse(fs.readFileSync(file, 'utf8')));
  } catch {
    return new Set();
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
    process.exit(0);
  }
  const keys = findTicketKeys(input.prompt);
  if (!keys.length) process.exit(0);

  const file = markerPath(input.session_id);
  const seen = loadSeen(file);
  const fresh = keys.filter((k) => !seen.has(k));
  if (!fresh.length) process.exit(0);

  try {
    fs.writeFileSync(file, JSON.stringify([...seen, ...fresh]));
  } catch {
    /* best-effort; still remind */
  }
  process.stdout.write(
    JSON.stringify({
      hookSpecificOutput: {
        hookEventName: 'UserPromptSubmit',
        additionalContext: buildTicketReminder(fresh),
      },
    })
  );
}

if (require.main === module) main();

module.exports = { findTicketKeys, buildTicketReminder };

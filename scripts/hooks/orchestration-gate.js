#!/usr/bin/env node
/**
 * Orchestration gate (PreToolUse).
 *
 * Fires the first time Claude is about to Write/Edit an implementation file in
 * a session and injects a non-blocking reminder: the chat is an ORCHESTRATOR,
 * heavy implementation should be delegated to the tiered subagents instead of
 * being done inline in the main thread. Advisory only — never blocks the edit.
 *
 * Rationale: subagent file-reading/implementation stays out of the main chat
 * context (token win), and each tier runs on a cost-matched model+effort.
 * Once per session (per-session tmp marker) to avoid noise.
 */
const fs = require('fs');
const os = require('os');
const path = require('path');

// Implementation surfaces (not docs/config/markdown — those don't need delegation).
const CODE_RE =
  /\.(py|ts|tsx|js|jsx|mjs|cjs|go|rs|java|kt|rb|php|swift|c|cc|cpp|h|hpp|vue|svelte|astro|sql|xml)$/i;

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

  const filePath = input.tool_input?.file_path || input.tool_input?.notebook_path || '';
  if (!filePath || !CODE_RE.test(filePath)) process.exit(0);

  // Once per session.
  const sessionId = input.session_id || 'nosession';
  const marker = path.join(os.tmpdir(), `claude-orchestration-gate-${sessionId}`);
  if (fs.existsSync(marker)) process.exit(0);
  try {
    fs.writeFileSync(marker, String(Date.now()));
  } catch {
    /* best-effort; still inject */
  }

  const gate = [
    '🧭 ORCHESTRATION GATE — el chat es ORQUESTADOR, no el que codea pesado inline.',
    'Estás por editar código directo en el thread principal. Antes de seguir, evaluá',
    'si esto debería ir a un subagente (su contexto no ensucia el chat = ahorro de tokens).',
    '',
    'Ruteo por tier (modelo + effort ya configurados en cada agente):',
    '  • Worker  → Haiku 4.5   : build-error-resolver, e2e-runner, doc-updater, refactor-cleaner',
    '  • Dev     → Sonnet 5    : code/python/typescript/react/database-reviewer, tdd-guide,',
    '                            design-critic, code-architect',
    '  • Deep    → Opus 5.5    : planner, architect, security-reviewer',
    '  • Apex    → Fable 5.1   : opt-in a mano, solo para lo más brutal ($10/$50)',
    '',
    'Cómo delegar:',
    '  • Feature nueva   → skill /orch-add-feature',
    '  • Fix de bug      → skill /orch-fix-defect',
    '  • Cambio de feat  → skill /orch-change-feature',
    '  • Refactor        → skill /orch-refine-code',
    '  • O Task directo al subagente del tier que corresponda.',
    '',
    'Si el edit es chico/mecánico y delegar cuesta más de lo que ahorra, seguí inline.',
    'Es un recordatorio, no un bloqueo — vos decidís.',
  ].join('\n');

  process.stdout.write(
    JSON.stringify({
      hookSpecificOutput: {
        hookEventName: 'PreToolUse',
        additionalContext: gate,
      },
    })
  );
  process.exit(0);
}

main();

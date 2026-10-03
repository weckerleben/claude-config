#!/usr/bin/env node
/**
 * Frontend UI/UX gate (PreToolUse).
 *
 * Fires when Claude is about to Write/Edit a frontend file and injects a
 * non-blocking reminder that forces a real design pass instead of "dump the
 * data and move on". Advisory only: never blocks the edit.
 *
 * To avoid noise, the full gate is injected once per session (marked by a
 * per-session tmp file) — the first time frontend code is touched.
 */
const fs = require('fs');
const os = require('os');
const path = require('path');

const FRONTEND_RE = /\.(jsx|tsx|vue|svelte|astro|css|scss|sass|less|html?|mdx)$/i;

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

  const filePath =
    input.tool_input?.file_path ||
    input.tool_input?.notebook_path ||
    '';
  if (!filePath || !FRONTEND_RE.test(filePath)) process.exit(0);

  // Once per session: skip if we've already injected the gate this session.
  const sessionId = input.session_id || 'nosession';
  const marker = path.join(os.tmpdir(), `claude-fe-design-gate-${sessionId}`);
  if (fs.existsSync(marker)) process.exit(0);
  try {
    fs.writeFileSync(marker, String(Date.now()));
  } catch {
    /* best-effort; still inject */
  }

  const gate = [
    '🎨 FRONTEND GATE — UI/UX es prioridad #1 al 110% en este archivo de front.',
    'Reusá las skills ECC ya instaladas; no reinventes criterio de diseño.',
    '',
    'ANTES de escribir código:',
    '  1. Cargá el criterio de diseño de ECC: invocá la skill make-interfaces-feel-better',
    '     y/o frontend-design-direction, más ~/.claude/rules/ecc/web/design-quality.md',
    '     (anti-template, jerarquía, estados). No es opcional.',
    '  2. DESIGN PASS explícito: dirección de estilo, jerarquía visual (qué elemento',
    '     MANDA y qué se subordina), y — CLAVE — el ENCAJE EN CONTEXTO: leé qué hay',
    '     arriba/abajo/al lado en la misma vista y justificá que el elemento nuevo',
    '     PERTENECE ahí y no compite con lo existente. Nunca critiques la pieza aislada.',
    '  3. Honrá el sistema existente (tokens, componentes). Específico > genérico.',
    '',
    'DESPUÉS de codear:',
    '  4. Corré el loop de diseño de ECC: skill gan-design (generador/evaluador con',
    '     score) o el subagente design-critic (subagent_type: "design-critic"). Su',
    '     PRIMER paso es mapear la superficie/vecinos y juzgar el encaje, y recién',
    '     después criticar. Aplicá lo que valga ANTES de cerrar.',
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

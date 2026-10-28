#!/usr/bin/env node
/**
 * Feature team gate (UserPromptSubmit).
 *
 * Skill auto-invocation is probabilistic — the model reads a description and
 * decides. This hook makes the layered pipeline deterministic instead: when a
 * prompt asks to BUILD something that spans more than one layer, it injects the
 * routing rule before the model starts improvising a plan.
 *
 * Advisory only: never blocks. Injected once per session, like the frontend gate.
 */
const fs = require('fs');
const os = require('os');
const path = require('path');

// Action verbs — the prompt must ask to build, not to explain.
// \b is defined over \w, which excludes accented vowels — "agregá" and "creá"
// would never close a boundary. Use explicit letter-class lookarounds instead.
const L = '\\wáéíóúüñÁÉÍÓÚÜÑ';
const B = (body) => new RegExp(`(?<![${L}])(?:${body})(?![${L}])`, 'i');

const BUILD_RE = B(
  'implement\\w*|implement[aá]\\w*|add|build|creat\\w*|make|ship|wire|scaffold|refactor|migrat\\w*|' +
    'agreg[aá]\\w*|a[ñn]ad\\w*|hac[eé]\\w*|cre[aá]\\w*|constru[ií]\\w*|arm[aá]\\w*|' +
    'desarroll[aá]\\w*|pon[eé]\\w*|met[eé]\\w*|mont[aá]\\w*'
);

// Pure-question openers — explaining is not building.
const QUESTION_RE = new RegExp(
  `^\\s*(?:¿|(?:c[oó]mo|qu[eé]|por\\s?qu[eé]|cu[aá]l|d[oó]nde|cu[aá]ndo|how|what|why|which|where|when|` +
    `explic\\w*|explain|mostr[aá]\\w*|revis[aá]\\w*|audit\\w*)(?![${L}]))`,
  'i'
);

// Audit intent: an audit verb plus a whole-project scope word. Checked BEFORE
// QUESTION_RE, since "revisá"/"auditá" would otherwise be filtered as questions.
const AUDIT_VERB = B(
  'audit\\w*|audit[aá]\\w*|revis[aá]\\w*|revisar|verific[aá]\\w*|verificar|' +
    'review|assess|evalu[aá]\\w*|evaluate'
);
const AUDIT_SCOPE = B(
  'proyecto|repo|repositorio|codebase|c[oó]digo\\s+entero|todo\\s+el\\s+\\w+|' +
    'entero|entera|completo|completa|whole|entire|full|app|aplicaci[oó]n|sistema|system|' +
    'producci[oó]n|production|prod|launch|lanzamiento'
);

const LAYERS = {
  DB: B(
    'tablas?|migrac\\w*|migration|schema|esquema|[ií]ndices?|index|quer(?:y|ies)|consulta|' +
      'modelo|model|postgres|sql|supabase|orm|rls|seed'
  ),
  Backend: B(
    'endpoint|api|ruta|route|servicio|service|backend|rpc|xml-?rpc|controller|' +
      'webhook|job|cron|queue|auth|login|middleware'
  ),
  Frontend: B(
    'pantalla|vista|view|ui|ux|dashboard|tablero|componente|component|front|p[aá]gina|page|' +
      'formulario|form|modal|bot[oó]n|button|css|tsx|jsx|vue|gr[aá]fico|chart'
  ),
};

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
    process.exit(0); // never break the turn on a parse error
  }

  const prompt = String(input.prompt || '');
  if (!prompt.trim()) process.exit(0);
  const isAudit = AUDIT_VERB.test(prompt) && AUDIT_SCOPE.test(prompt);
  if (!isAudit) {
    if (QUESTION_RE.test(prompt)) process.exit(0);
    if (!BUILD_RE.test(prompt)) process.exit(0);
  }

  const hits = Object.keys(LAYERS).filter((k) => LAYERS[k].test(prompt));
  // Build path needs 2+ layers to justify lanes. An audit covers the whole
  // project by definition, so layer count is irrelevant there.
  if (!isAudit && hits.length < 2) process.exit(0);

  const sessionId = input.session_id || 'nosession';
  const kind = isAudit ? 'audit' : 'build';
  const marker = path.join(os.tmpdir(), `claude-feature-team-gate-${kind}-${sessionId}`);
  if (fs.existsSync(marker)) process.exit(0);
  try {
    fs.writeFileSync(marker, String(Date.now()));
  } catch {
    /* best-effort; still inject */
  }

  const auditGate = [
    '🔍 AUDIT GATE — esto es verificar un proyecto existente, no construir.',
    '',
    '  → invocá la skill orch-audit-project (o el comando /orch-audit-project).',
    '',
    'NO uses orch-feature-team acá: pide plan, contrato de interfaz y reparto de',
    'archivos entre lanes — ceremonia vacía sobre código que ya existe.',
    'NO uses /code-review salvo que el alcance sea un diff o un PR puntual.',
    '',
    'Lo que ese pipeline garantiza:',
    '  · Recon primero: stack, superficies, tests, CI, git state → anunciar lanes',
    '  · Lanes paralelas read-only: Security / Data / Correctness / Tests / Frontend',
    '  · REPORT ONLY textual en cada prompt — 5 de esos agentes PUEDEN escribir',
    '    (ecc:security-reviewer, ecc:database-reviewer, ecc:performance-optimizer,',
    '     ecc:a11y-architect, ecc:e2e-runner). Que "arreglen" contamina la auditoría.',
    '  · git status idéntico antes y después: verificalo y decilo',
    '  · Browser real: consola, red, 375/768/1440, ambos temas',
    '  · Consolidación: dedup, cross-check, CRITICAL→LOW, file:line + escenario de falla',
    '  · Informe que nombra sus propios puntos ciegos',
    '',
    'Arreglar es un pase APARTE que el usuario pide explícito. No derives ahí solo.',
  ].join('\n');

  const buildGate = [
    `🏗️  FEATURE TEAM GATE — este pedido toca ${hits.length} capas: ${hits.join(' + ')}.`,
    '',
    'NO improvises un plan monolítico. Usá el pipeline por capas:',
    '  → invocá la skill orch-feature-team (o el comando /orch-feature-team).',
    '',
    'Lo que ese pipeline garantiza y una implementación suelta se saltea:',
    '  · contrato de interfaz + file-ownership DISJUNTO declarados ANTES de abrir lanes',
    '  · lanes paralelas: DB / Backend / Frontend, cada una con TDD (tests primero)',
    '  · cierre obligatorio ecc:database-reviewer en la lane DB',
    '  · cierre obligatorio design-critic en la lane Frontend (además del design pass)',
    '  · E2E en browser REAL con evidencia: consola limpia, red sin fallos, 375/768/1440',
    '  · ecc:code-reviewer + ecc:security-reviewer si toca auth/input/queries/secrets',
    '  · GATE 1 (plan) y GATE 2 (commit): no escribís código ni commiteás sin aprobación',
    '',
    'Si el plan no puede partir los archivos limpio entre lanes, decilo y caé a',
    '/orch-add-feature serial — nunca corras dos lanes sobre el mismo archivo.',
    '',
    'Agentes: prefijo ecc:* (ecc:tdd-guide, ecc:code-reviewer…). design-critic va sin prefijo.',
  ].join('\n');

  const gate = isAudit ? auditGate : buildGate;

  process.stdout.write(
    JSON.stringify({
      hookSpecificOutput: {
        hookEventName: 'UserPromptSubmit',
        additionalContext: gate,
      },
    })
  );
  process.exit(0);
}

main();

'use strict';

const fs = require('fs');
const path = require('path');
const { resolveRates, MILLION } = require('./cost');
const { aggregateSession } = require('./transcript');
const { contextWindowSize } = require('./config');
const { formatTokens, formatUSD } = require('./format');

/** Claude Code names a project folder after its cwd with non-alphanumerics as '-'. */
const projectKey = (cwd) => String(cwd).replace(/[^a-zA-Z0-9]/g, '-');

function newestTranscript(dir) {
  let best = null;
  let names;
  try {
    names = fs.readdirSync(dir);
  } catch {
    return null;
  }
  for (const name of names) {
    if (!name.endsWith('.jsonl')) continue;
    const file = path.join(dir, name);
    try {
      const mtime = fs.statSync(file).mtimeMs;
      if (!best || mtime > best.mtime) best = { path: file, mtime };
    } catch {
      /* file vanished while scanning */
    }
  }
  return best;
}

function allProjectDirs(projectsDir) {
  try {
    return fs.readdirSync(projectsDir).map((name) => path.join(projectsDir, name));
  } catch {
    return [];
  }
}

function findLatestTranscript({ projectsDir, cwd }) {
  const own = newestTranscript(path.join(projectsDir, projectKey(cwd)));
  if (own) return own.path;

  const newest = allProjectDirs(projectsDir)
    .map(newestTranscript)
    .filter(Boolean)
    .reduce((best, candidate) => (!best || candidate.mtime > best.mtime ? candidate : best), null);
  return newest ? newest.path : null;
}

/** Locate a session by id (any project) or accept a direct transcript path. */
function findSession({ projectsDir, session }) {
  if (session.endsWith('.jsonl') && fs.existsSync(session)) return session;
  for (const dir of allProjectDirs(projectsDir)) {
    const candidate = path.join(dir, `${session}.jsonl`);
    if (fs.existsSync(candidate)) return candidate;
  }
  return null;
}

function listSessions({ projectsDir, limit, pricing, stateDir }) {
  const files = [];
  for (const dir of allProjectDirs(projectsDir)) {
    let names = [];
    try {
      names = fs.readdirSync(dir).filter((n) => n.endsWith('.jsonl'));
    } catch {
      continue;
    }
    for (const name of names) {
      const file = path.join(dir, name);
      try {
        files.push({ file, mtime: fs.statSync(file).mtimeMs });
      } catch {
        /* file vanished while scanning */
      }
    }
  }
  return files
    .sort((a, b) => b.mtime - a.mtime)
    .slice(0, limit)
    .map(({ file, mtime }) => {
      const agg = aggregateSession({ transcriptPath: file, stateDir, pricing });
      return { id: path.basename(file, '.jsonl'), mtime, totals: agg.total, agentsUSD: agg.agents.usd, agentCount: agg.agentCount };
    });
}

const marginLabel = (margin) => `+${Math.round((margin - 1) * 100)}%`;

function renderReport({ id, session, pricing, margin }) {
  const { total, agents, main, context } = session;
  const lines = [
    `Session ${id.slice(0, 8)}  (${main.messages + agents.messages} API messages, each counted once)`,
    `Cost      ~${formatUSD(total.usd * margin)}  (raw ${formatUSD(total.usd)}, ${marginLabel(margin)} safety margin)`,
    `          main ~${formatUSD(main.usd * margin)}` +
      (session.agentCount > 0 ? `  ·  agents ~${formatUSD(agents.usd * margin)} (${session.agentCount})` : ''),
    `Tokens    in ${formatTokens(total.input)} · out ${formatTokens(total.output)} · ` +
      `cache read ${formatTokens(total.cacheRead)} · cache write ${formatTokens(total.cacheWrite)}`
  ];

  if (context) {
    const window = contextWindowSize(undefined, context.tokens);
    const { rates } = resolveRates(context.model, pricing);
    const perTurn = (context.tokens * rates.cacheRead * margin) / MILLION;
    lines.push(
      `Context   ${formatTokens(context.tokens)} tokens (${Math.round((context.tokens / window) * 100)}% of ${formatTokens(window)}) · ` +
        `each turn re-reads it ≈ ~${formatUSD(perTurn)} per turn`
    );
  }
  lines.push(`Rates     ${pricing.source} (fetched ${pricing.fetchedAt})`);
  if (total.unknownMessages > 0) {
    lines.push(`WARNING   ${total.unknownMessages} message(s) used an unknown model, priced at the most expensive tier`);
  }
  return `${lines.join('\n')}\n`;
}

function renderTable(rows, margin) {
  const header = `${'session'.padEnd(10)} ${'cost'.padStart(10)} ${'agents'.padStart(10)} ${'msgs'.padStart(6)}`;
  const body = rows.map(
    (r) =>
      `${r.id.slice(0, 10).padEnd(10)} ${`~${formatUSD(r.totals.usd * margin)}`.padStart(10)} ` +
      `${`~${formatUSD(r.agentsUSD * margin)}`.padStart(10)} ${String(r.totals.messages).padStart(6)}`
  );
  return `${[header, ...body].join('\n')}\n`;
}

module.exports = { projectKey, findLatestTranscript, findSession, listSessions, renderReport, renderTable };

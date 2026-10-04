#!/usr/bin/env node
/**
 * On-demand cost report.
 *
 *   node cost-report.js                 latest session of the current project
 *   node cost-report.js --session <id>  a specific session (id or transcript path)
 *   node cost-report.js --all [--limit N]  the N most recent sessions (default 10)
 *   node cost-report.js --json          machine-readable output
 *   node cost-report.js --cwd <dir>     pick the project from <dir> instead of $PWD
 */

'use strict';

const os = require('os');
const path = require('path');
const { loadPricing } = require('./lib/cost');
const { aggregateSession } = require('./lib/transcript');
const { resolveMargin } = require('./lib/config');
const { findLatestTranscript, findSession, listSessions, renderReport, renderTable } = require('./lib/report');

function parseArgs(argv) {
  const args = { all: false, json: false, limit: 10, cwd: process.cwd(), session: process.env.CLAUDE_SESSION_ID || '' };
  for (let i = 0; i < argv.length; i++) {
    const flag = argv[i];
    if (flag === '--all') args.all = true;
    else if (flag === '--json') args.json = true;
    else if (flag === '--limit') args.limit = Number(argv[++i]) || args.limit;
    else if (flag === '--cwd') args.cwd = argv[++i] || args.cwd;
    else if (flag === '--session') args.session = argv[++i] || '';
  }
  return args;
}

function main() {
  const args = parseArgs(process.argv.slice(2));
  const env = process.env;
  const projectsDir = env.WECK_PROJECTS_DIR || path.join(os.homedir(), '.claude', 'projects');
  const stateDir = env.WECK_STATE_DIR || os.tmpdir();
  const pricing = loadPricing();
  const margin = resolveMargin(pricing, env);

  if (args.all) {
    const rows = listSessions({ projectsDir, limit: args.limit, pricing, stateDir });
    process.stdout.write(args.json ? `${JSON.stringify(rows)}\n` : renderTable(rows, margin));
    return;
  }

  const transcriptPath = args.session
    ? findSession({ projectsDir, session: args.session })
    : findLatestTranscript({ projectsDir, cwd: args.cwd });
  if (!transcriptPath) {
    process.stdout.write('No session found. Pass --session <id> or run it from a project that has sessions.\n');
    return;
  }

  const id = path.basename(transcriptPath, '.jsonl');
  const session = aggregateSession({ transcriptPath, stateDir, pricing });
  if (args.json) {
    process.stdout.write(`${JSON.stringify({ id, margin, shownUSD: session.total.usd * margin, rawUSD: session.total.usd, ...session })}\n`);
    return;
  }
  process.stdout.write(renderReport({ id, session, pricing, margin }));
}

main();

#!/usr/bin/env node
/**
 * Claude Code statusLine command.
 *
 *   line 1: model · dir · branch   context bar  pct  tokens/window  [COMPACTAR]
 *   line 2: ~$session (+margin)  in/out tokens  cache read/write  agents  per-turn cost
 *
 * Cost is computed from the session transcripts (main + subagents) with the
 * table in pricing.json and multiplied by a safety margin on purpose.
 */

'use strict';

const os = require('os');
const { loadPricing, resolveRates, MILLION } = require('./lib/cost');
const { aggregateSession } = require('./lib/transcript');
const { evaluateAdvice } = require('./lib/compact-advice');
const { currentBranch } = require('./lib/git');
const { readStdinJson } = require('./lib/stdin');
const f = require('./lib/format');

const STANDARD_WINDOW = 200_000;
const LARGE_WINDOW = 1_000_000;

function resolveMargin(pricing, env) {
  const override = Number(env.WECK_COST_MARGIN);
  return Number.isFinite(override) && override > 0 ? override : pricing.margin;
}

function contextWindow(input, tokens) {
  const reported = input.context_window && input.context_window.context_window_size;
  if (Number.isFinite(reported) && reported > 0) return reported;
  return tokens > STANDARD_WINDOW ? LARGE_WINDOW : STANDARD_WINDOW;
}

function shortDir(dir) {
  const home = os.homedir();
  return dir && dir.startsWith(home) ? `~${dir.slice(home.length)}` : dir || '';
}

function buildLines(input, env) {
  const pricing = loadPricing();
  const margin = resolveMargin(pricing, env);
  const modelName = (input.model && (input.model.display_name || input.model.id)) || 'Claude';
  const dir = (input.workspace && input.workspace.current_dir) || input.cwd || '';

  const session = input.transcript_path
    ? aggregateSession({ transcriptPath: input.transcript_path, stateDir: env.WECK_STATE_DIR || os.tmpdir(), pricing })
    : null;
  const tokens = session && session.context ? session.context.tokens : 0;
  const window = contextWindow(input, tokens);
  const reportedPct = input.context_window && input.context_window.used_percentage;
  const pct = Number.isFinite(reportedPct) ? reportedPct : (tokens / window) * 100;

  const advice = evaluateAdvice({ tokens, lastBucket: -1, cfg: pricing.compact });
  const flag = advice.advise
    ? `  ${advice.urgent ? f.RED : f.YELLOW}${f.BOLD}COMPACTAR${f.RESET}`
    : '';
  const branch = currentBranch(dir);
  const line1 =
    `${f.DIM}${modelName}${f.RESET} · ${shortDir(dir)}${branch ? ` · ${branch}` : ''}  ` +
    `${f.contextBar(pct)} ${Math.round(pct)}%  ${f.formatTokens(tokens)}/${f.formatTokens(window)}${flag}`;

  const total = session ? session.total : { usd: 0, input: 0, output: 0, cacheRead: 0, cacheWrite: 0, unknownMessages: 0 };
  const shown = total.usd * margin;
  const marginLabel = margin === 1 ? '' : ` ${f.DIM}(+${Math.round((margin - 1) * 100)}%)${f.RESET}`;
  const unknown = total.unknownMessages > 0 ? '?' : '';
  const cost = `${f.usdColor(shown, pricing.thresholdsUSD)}${f.BOLD}~${f.formatUSD(shown)}${unknown}${f.RESET}${marginLabel}`;

  const parts = [
    cost,
    `in ${f.formatTokens(total.input)} out ${f.formatTokens(total.output)}`,
    `cache r ${f.formatTokens(total.cacheRead)} w ${f.formatTokens(total.cacheWrite)}`
  ];
  if (session && session.agentCount > 0) {
    parts.push(`agentes ~${f.formatUSD(session.agents.usd * margin)} (${session.agentCount})`);
  }
  if (tokens > 0) {
    const { rates } = resolveRates(session.context.model, pricing);
    parts.push(`turno ~${f.formatUSD((tokens * rates.cacheRead * margin) / MILLION)}`);
  }

  return [line1, parts.join(`  ${f.DIM}·${f.RESET}  `)];
}

async function main() {
  const input = await readStdinJson();
  try {
    process.stdout.write(`${buildLines(input, process.env).join('\n')}\n`);
  } catch {
    const name = (input.model && (input.model.display_name || input.model.id)) || 'Claude';
    process.stdout.write(`${name}\n`);
  }
}

main();

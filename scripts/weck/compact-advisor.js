#!/usr/bin/env node
/**
 * UserPromptSubmit hook: when the session context passes the advise threshold,
 * inject text that makes the model tell the user to compact and hand over a
 * ready-to-paste `/compact <instructions>` command. Fires once per context
 * bucket, never blocks.
 */

'use strict';

const fs = require('fs');
const os = require('os');
const path = require('path');
const { loadPricing, resolveRates, MILLION } = require('./lib/cost');
const { aggregateSession } = require('./lib/transcript');
const { evaluateAdvice, buildCompactCommand, buildAdvisorContext } = require('./lib/compact-advice');
const { currentBranch } = require('./lib/git');
const { resolveMargin } = require('./lib/config');
const { evaluateCostNotice, buildCostNotice } = require('./lib/cost-notice');
const { readStdinJson } = require('./lib/stdin');

function readState(file) {
  try {
    const saved = JSON.parse(fs.readFileSync(file, 'utf8'));
    return {
      bucket: Number.isInteger(saved.bucket) ? saved.bucket : -1,
      costBucket: Number.isInteger(saved.costBucket) ? saved.costBucket : 0
    };
  } catch {
    return { bucket: -1, costBucket: 0 };
  }
}

function writeState(file, state) {
  try {
    fs.writeFileSync(file, JSON.stringify(state));
  } catch {
    /* advisory only */
  }
}

function compactAdvice({ session, verdict, input, pricing, margin }) {
  const { tokens, model } = session.context;
  const { rates } = resolveRates(model, pricing);
  const command = buildCompactCommand({
    cwd: input.cwd,
    branch: currentBranch(input.cwd),
    modifiedFiles: session.modifiedFiles
  });
  return buildAdvisorContext({
    tokens,
    urgent: verdict.urgent,
    perTurnUSD: (tokens * rates.cacheRead * margin) / MILLION,
    command
  });
}

function advise(input, env) {
  if (!input.transcript_path) return null;

  const pricing = loadPricing();
  const margin = resolveMargin(pricing, env);
  const stateDir = env.WECK_STATE_DIR || os.tmpdir();
  const sessionId = input.session_id || path.basename(input.transcript_path, '.jsonl');
  const stateFile = path.join(stateDir, `weck-compact-${sessionId}.json`);
  const saved = readState(stateFile);

  const session = aggregateSession({ transcriptPath: input.transcript_path, stateDir, pricing });
  const messages = [];

  const spend = evaluateCostNotice({
    usd: session.total.usd * margin,
    lastBucket: saved.costBucket,
    everyUSD: pricing.costNotice && pricing.costNotice.everyUSD
  });
  if (spend.notify) {
    messages.push(
      buildCostNotice({
        shownUSD: session.total.usd * margin,
        marginPct: Math.round((margin - 1) * 100),
        totals: session.total,
        agentsUSD: session.agents.usd * margin,
        agentCount: session.agentCount
      })
    );
  }

  let bucket = saved.bucket;
  if (session.context) {
    const verdict = evaluateAdvice({ tokens: session.context.tokens, lastBucket: saved.bucket, cfg: pricing.compact });
    bucket = verdict.nextBucket;
    if (verdict.advise) messages.push(compactAdvice({ session, verdict, input, pricing, margin }));
  }

  writeState(stateFile, { bucket, costBucket: spend.nextBucket });
  return messages.length > 0 ? messages.join('\n\n') : null;
}

async function main() {
  const input = await readStdinJson();
  try {
    const context = advise(input, process.env);
    if (context) {
      process.stdout.write(
        JSON.stringify({ hookSpecificOutput: { hookEventName: 'UserPromptSubmit', additionalContext: context } })
      );
    }
  } catch (error) {
    process.stderr.write(`[weck-compact-advisor] skipped: ${error.message}\n`);
  }
  process.exit(0);
}

main();

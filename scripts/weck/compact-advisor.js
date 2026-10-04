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
const { readStdinJson } = require('./lib/stdin');

function readBucket(file) {
  try {
    const value = JSON.parse(fs.readFileSync(file, 'utf8')).bucket;
    return Number.isInteger(value) ? value : -1;
  } catch {
    return -1;
  }
}

function writeBucket(file, bucket) {
  try {
    fs.writeFileSync(file, JSON.stringify({ bucket }));
  } catch {
    /* advisory only */
  }
}

function resolveMargin(pricing, env) {
  const override = Number(env.WECK_COST_MARGIN);
  return Number.isFinite(override) && override > 0 ? override : pricing.margin;
}

function advise(input, env) {
  if (!input.transcript_path) return null;

  const pricing = loadPricing();
  const stateDir = env.WECK_STATE_DIR || os.tmpdir();
  const sessionId = input.session_id || path.basename(input.transcript_path, '.jsonl');
  const bucketFile = path.join(stateDir, `weck-compact-${sessionId}.json`);

  const session = aggregateSession({ transcriptPath: input.transcript_path, stateDir, pricing });
  if (!session.context) return null;

  const { tokens, model } = session.context;
  const verdict = evaluateAdvice({ tokens, lastBucket: readBucket(bucketFile), cfg: pricing.compact });
  writeBucket(bucketFile, verdict.nextBucket);
  if (!verdict.advise) return null;

  const { rates } = resolveRates(model, pricing);
  const perTurnUSD = (tokens * rates.cacheRead * resolveMargin(pricing, env)) / MILLION;
  const command = buildCompactCommand({
    cwd: input.cwd,
    branch: currentBranch(input.cwd),
    modifiedFiles: session.modifiedFiles
  });
  return buildAdvisorContext({ tokens, urgent: verdict.urgent, perTurnUSD, command });
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

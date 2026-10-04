'use strict';

const { formatTokens, formatUSD } = require('./format');

/**
 * Decide whether to announce spend. Buckets are steps of `everyUSD` of the
 * shown (margin-included) amount; `lastBucket` is the last one announced.
 */
function evaluateCostNotice({ usd, lastBucket, everyUSD }) {
  if (!Number.isFinite(everyUSD) || everyUSD <= 0 || !Number.isFinite(usd)) {
    return { notify: false, nextBucket: lastBucket };
  }
  const bucket = Math.floor(usd / everyUSD);
  return { notify: bucket > lastBucket, nextBucket: bucket };
}

/** Text injected into the model's context so it relays the spend to the user. */
function buildCostNotice({ shownUSD, marginPct, totals, agentsUSD, agentCount }) {
  const agents = agentsUSD > 0 ? `, agents ~${formatUSD(agentsUSD)} (${agentCount})` : '';
  return (
    `[Cost notice] Session spend is ~${formatUSD(shownUSD)} (+${marginPct}% safety margin): ` +
    `in ${formatTokens(totals.input)} / out ${formatTokens(totals.output)} tokens, ` +
    `cache read ${formatTokens(totals.cacheRead)} / write ${formatTokens(totals.cacheWrite)}${agents}. ` +
    'Tell the user in ONE short line in Spanish.'
  );
}

module.exports = { evaluateCostNotice, buildCostNotice };

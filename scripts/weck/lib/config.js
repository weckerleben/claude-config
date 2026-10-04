'use strict';

const STANDARD_WINDOW = 200_000;
const LARGE_WINDOW = 1_000_000;

/** Safety margin applied to every shown amount: env override, else pricing.json. */
function resolveMargin(pricing, env) {
  const override = Number(env.WECK_COST_MARGIN);
  return Number.isFinite(override) && override > 0 ? override : pricing.margin;
}

/** Context window in tokens: the size Claude Code reports, else inferred from usage. */
function contextWindowSize(reported, tokens) {
  if (Number.isFinite(reported) && reported > 0) return reported;
  return tokens > STANDARD_WINDOW ? LARGE_WINDOW : STANDARD_WINDOW;
}

module.exports = { resolveMargin, contextWindowSize };

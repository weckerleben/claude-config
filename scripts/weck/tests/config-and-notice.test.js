'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { resolveMargin, contextWindowSize } = require('../lib/config');
const { evaluateCostNotice, buildCostNotice } = require('../lib/cost-notice');

const pricing = { margin: 1.2 };

test('resolveMargin uses the pricing default and honors a valid env override', () => {
  assert.equal(resolveMargin(pricing, {}), 1.2);
  assert.equal(resolveMargin(pricing, { WECK_COST_MARGIN: '1.5' }), 1.5);
});

test('resolveMargin ignores invalid overrides', () => {
  assert.equal(resolveMargin(pricing, { WECK_COST_MARGIN: 'abc' }), 1.2);
  assert.equal(resolveMargin(pricing, { WECK_COST_MARGIN: '0' }), 1.2);
  assert.equal(resolveMargin(pricing, { WECK_COST_MARGIN: '-2' }), 1.2);
});

test('contextWindowSize prefers the reported size, then infers from usage', () => {
  assert.equal(contextWindowSize(1_000_000, 10), 1_000_000);
  assert.equal(contextWindowSize(undefined, 50_000), 200_000);
  assert.equal(contextWindowSize(undefined, 250_000), 1_000_000);
  assert.equal(contextWindowSize(0, 250_000), 1_000_000);
});

test('no cost notice below the first step', () => {
  const r = evaluateCostNotice({ usd: 4.9, lastBucket: 0, everyUSD: 5 });
  assert.equal(r.notify, false);
  assert.equal(r.nextBucket, 0);
});

test('cost notice fires when crossing a step and not again within it', () => {
  const first = evaluateCostNotice({ usd: 5.1, lastBucket: 0, everyUSD: 5 });
  assert.equal(first.notify, true);
  assert.equal(first.nextBucket, 1);
  const again = evaluateCostNotice({ usd: 7, lastBucket: 1, everyUSD: 5 });
  assert.equal(again.notify, false);
  const next = evaluateCostNotice({ usd: 10.2, lastBucket: 1, everyUSD: 5 });
  assert.equal(next.notify, true);
  assert.equal(next.nextBucket, 2);
});

test('cost notice can be disabled with a zero step', () => {
  assert.equal(evaluateCostNotice({ usd: 500, lastBucket: 0, everyUSD: 0 }).notify, false);
});

test('cost notice text carries amount, margin, tokens and agents', () => {
  const text = buildCostNotice({
    shownUSD: 12.345,
    marginPct: 20,
    totals: { input: 168, output: 107000, cacheRead: 17_000_000, cacheWrite: 401000 },
    agentsUSD: 3.2,
    agentCount: 2
  });
  assert.ok(text.includes('~$12.35'));
  assert.ok(text.includes('+20%'));
  assert.ok(text.includes('out 107k'));
  assert.ok(text.includes('cache read 17M'));
  assert.ok(text.includes('agents ~$3.20'));
  assert.ok(/Spanish/.test(text));
});

test('cost notice omits the agents part when there are none', () => {
  const text = buildCostNotice({
    shownUSD: 6,
    marginPct: 20,
    totals: { input: 1, output: 1, cacheRead: 1, cacheWrite: 1 },
    agentsUSD: 0,
    agentCount: 0
  });
  assert.ok(!text.includes('agents'));
});

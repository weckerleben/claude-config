'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { loadPricing, normalizeModel, usageCostUSD } = require('../lib/cost');

const pricing = loadPricing();
const close = (actual, expected) => assert.ok(Math.abs(actual - expected) < 1e-9, `${actual} !== ${expected}`);

test('normalizeModel maps real model ids to pricing keys', () => {
  assert.equal(normalizeModel('claude-sonnet-5-5'), 'sonnet-5-5');
  assert.equal(normalizeModel('claude-sonnet-5-5[1m]'), 'sonnet-5-5');
  assert.equal(normalizeModel('claude-haiku-4-5-20251001'), 'haiku-4-5');
  assert.equal(normalizeModel('claude-opus-4-1-20250805'), 'opus-4-1');
  assert.equal(normalizeModel('claude-3-5-haiku-20241022'), 'haiku-3-5');
  assert.equal(normalizeModel('claude-fable-5-1'), 'fable-5-1');
  assert.equal(normalizeModel('claude-opus-5'), 'opus-5');
});

test('normalizeModel returns null for ids it cannot place', () => {
  assert.equal(normalizeModel('opus'), null);
  assert.equal(normalizeModel(''), null);
  assert.equal(normalizeModel(undefined), null);
  assert.equal(normalizeModel('<synthetic>'), null);
});

test('plain input and output follow the published Opus 5 worked example', () => {
  const r = usageCostUSD({ input_tokens: 50000, output_tokens: 15000 }, 'claude-opus-5', pricing);
  close(r.usd, 0.25 + 0.375);
  assert.equal(r.known, true);
});

test('cache reads use the cache-hit price (Opus 5 worked example)', () => {
  const r = usageCostUSD(
    { input_tokens: 10000, cache_read_input_tokens: 40000, output_tokens: 15000 },
    'claude-opus-5',
    pricing
  );
  close(r.usd, 0.05 + 0.02 + 0.375);
});

test('5m and 1h cache writes are priced separately', () => {
  const r = usageCostUSD(
    {
      input_tokens: 1000,
      output_tokens: 2000,
      cache_read_input_tokens: 1_000_000,
      cache_creation_input_tokens: 300000,
      cache_creation: { ephemeral_5m_input_tokens: 100000, ephemeral_1h_input_tokens: 200000 }
    },
    'claude-sonnet-5-5',
    pricing
  );
  close(r.usd, 0.002 + 0.02 + 0.25 + 0.8 + 0.2);
  assert.equal(r.tokens.cacheWrite, 300000);
  assert.equal(r.tokens.cacheRead, 1_000_000);
});

test('cache creation without a breakdown is billed as 5m writes', () => {
  const r = usageCostUSD({ cache_creation_input_tokens: 1_000_000 }, 'claude-sonnet-5-5', pricing);
  close(r.usd, 2.5);
});

test('any cache creation not covered by the breakdown is billed as 5m writes', () => {
  const r = usageCostUSD(
    {
      cache_creation_input_tokens: 1_000_000,
      cache_creation: { ephemeral_5m_input_tokens: 0, ephemeral_1h_input_tokens: 400000 }
    },
    'claude-sonnet-5-5',
    pricing
  );
  close(r.usd, 400000 * 4 / 1e6 + 600000 * 2.5 / 1e6);
});

test('Opus 5.5 cache hits cost 0.05x of base input, not 0.1x', () => {
  const r = usageCostUSD({ cache_read_input_tokens: 1_000_000 }, 'claude-opus-5-5', pricing);
  close(r.usd, 0.2);
});

test('Fable 5.1 cache hits cost 0.025x of base input', () => {
  const r = usageCostUSD({ cache_read_input_tokens: 1_000_000 }, 'claude-fable-5-1', pricing);
  close(r.usd, 0.25);
});

test('fast mode uses premium rates and scales cache read with them', () => {
  const r = usageCostUSD(
    { input_tokens: 1_000_000, output_tokens: 1_000_000, cache_read_input_tokens: 1_000_000, speed: 'fast' },
    'claude-opus-5-5',
    pricing
  );
  close(r.usd, 8 + 40 + 0.4);
});

test('fast mode on a model without a fast tier falls back to standard rates', () => {
  const r = usageCostUSD({ input_tokens: 1_000_000, speed: 'fast' }, 'claude-sonnet-5-5', pricing);
  close(r.usd, 2);
});

test('US-only inference applies the 1.1x multiplier to everything', () => {
  const r = usageCostUSD({ input_tokens: 1_000_000, inference_geo: 'us' }, 'claude-sonnet-5-5', pricing);
  close(r.usd, 2.2);
});

test('web search requests add a per-request charge', () => {
  const r = usageCostUSD({ server_tool_use: { web_search_requests: 3 } }, 'claude-sonnet-5-5', pricing);
  close(r.usd, 0.03);
});

test('an unknown model is priced at the fallback tier and flagged, never underestimated', () => {
  const r = usageCostUSD({ input_tokens: 1_000_000 }, 'claude-zeta-9', pricing);
  close(r.usd, 10);
  assert.equal(r.known, false);
});

test('missing or garbage usage fields count as zero', () => {
  const r = usageCostUSD({ input_tokens: 'x', output_tokens: -5, cache_read_input_tokens: null }, 'claude-sonnet-5-5', pricing);
  close(r.usd, 0);
});

test('results are frozen so callers cannot mutate shared totals', () => {
  const r = usageCostUSD({ input_tokens: 1 }, 'claude-sonnet-5-5', pricing);
  assert.ok(Object.isFrozen(r));
});

'use strict';

const fs = require('fs');
const path = require('path');

const DEFAULT_PRICING_PATH = path.join(__dirname, '..', 'pricing.json');
const MILLION = 1_000_000;
const MODERN_ID = /^claude-(fable|mythos|opus|sonnet|haiku)-(\d+)(?:-(\d+))?$/;
const LEGACY_ID = /^claude-(\d+)(?:-(\d+))?-(opus|sonnet|haiku)$/;

function loadPricing(file = DEFAULT_PRICING_PATH) {
  return JSON.parse(fs.readFileSync(file, 'utf8'));
}

/**
 * Map a model id from a transcript to a key of pricing.models.
 * Returns null when the id cannot be placed.
 */
function normalizeModel(id) {
  if (typeof id !== 'string') return null;
  const cleaned = id
    .toLowerCase()
    .replace(/\[[^\]]*\]$/, '')
    .replace(/-\d{8}$/, '');

  const modern = cleaned.match(MODERN_ID);
  if (modern) {
    const [, family, major, minor] = modern;
    return minor ? `${family}-${major}-${minor}` : `${family}-${major}`;
  }

  const legacy = cleaned.match(LEGACY_ID);
  if (legacy) {
    const [, major, minor, family] = legacy;
    return minor ? `${family}-${major}-${minor}` : `${family}-${major}`;
  }

  return null;
}

/**
 * Resolve the price row for a model id.
 * Unknown models fall back to the most expensive tier so cost is never understated.
 */
function resolveRates(model, pricing) {
  const key = normalizeModel(model);
  const known = key !== null && Object.hasOwn(pricing.models, key);
  const modelKey = known ? key : pricing.fallbackModel;
  return Object.freeze({ key: modelKey, known, rates: pricing.models[modelKey] });
}

const count = (value) => (typeof value === 'number' && Number.isFinite(value) && value > 0 ? value : 0);

function cacheWriteSplit(usage) {
  const total = count(usage.cache_creation_input_tokens);
  const detail = usage.cache_creation || {};
  const w1h = count(detail.ephemeral_1h_input_tokens);
  const w5m = count(detail.ephemeral_5m_input_tokens);
  const uncovered = Math.max(0, total - w5m - w1h);
  return { w5m: w5m + uncovered, w1h };
}

/**
 * Raw (margin-free) USD cost of one API message's usage block.
 */
function usageCostUSD(usage, model, pricing) {
  const u = usage || {};
  const { key, known, rates } = resolveRates(model, pricing);

  const fast = u.speed === 'fast' && rates.fast ? rates.fast : null;
  const scale = fast ? fast.input / rates.input : 1;
  const inputRate = fast ? fast.input : rates.input;
  const outputRate = fast ? fast.output : rates.output;

  const input = count(u.input_tokens);
  const output = count(u.output_tokens);
  const cacheRead = count(u.cache_read_input_tokens);
  const { w5m, w1h } = cacheWriteSplit(u);
  const web = count(u.server_tool_use && u.server_tool_use.web_search_requests);

  const tokenUSD =
    (input * inputRate +
      output * outputRate +
      cacheRead * rates.cacheRead * scale +
      w5m * rates.cacheWrite5m * scale +
      w1h * rates.cacheWrite1h * scale) /
    MILLION;
  const geo = u.inference_geo === 'us' ? pricing.usGeoMultiplier : 1;
  const usd = tokenUSD * geo + web * pricing.webSearchPerRequest;

  return Object.freeze({
    usd,
    known,
    modelKey: key,
    web,
    tokens: Object.freeze({ input, output, cacheRead, cacheWrite: w5m + w1h })
  });
}

module.exports = { loadPricing, normalizeModel, resolveRates, usageCostUSD, MILLION };

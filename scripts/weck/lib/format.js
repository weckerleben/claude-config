'use strict';

const RESET = '\x1b[0m';
const DIM = '\x1b[2m';
const BOLD = '\x1b[1m';
const GREEN = '\x1b[32m';
const YELLOW = '\x1b[33m';
const ORANGE = '\x1b[38;5;208m';
const RED = '\x1b[1;31m';

function formatTokens(n) {
  const value = Number.isFinite(n) && n > 0 ? n : 0;
  if (value < 1000) return String(Math.round(value));

  const thousands = value / 1000;
  const kRounded = thousands < 10 ? Number(thousands.toFixed(1)) : Math.round(thousands);
  if (kRounded < 1000) return `${kRounded}k`;

  const millions = value / 1_000_000;
  return `${millions < 10 ? Number(millions.toFixed(1)) : Math.round(millions)}M`;
}

function formatUSD(v) {
  const value = Number.isFinite(v) && v > 0 ? v : 0;
  return value >= 100 ? `$${Math.round(value)}` : `$${value.toFixed(2)}`;
}

function pctColor(pct) {
  if (pct < 50) return GREEN;
  if (pct < 70) return YELLOW;
  if (pct < 85) return ORANGE;
  return RED;
}

function contextBar(pct, width = 10) {
  const clamped = Math.max(0, Math.min(100, Number.isFinite(pct) ? pct : 0));
  const filled = Math.floor((clamped / 100) * width);
  return `${pctColor(clamped)}${'█'.repeat(filled)}${'░'.repeat(width - filled)}${RESET}`;
}

function usdColor(usd, thresholds) {
  if (usd > thresholds.alarm) return RED;
  if (usd > thresholds.high) return ORANGE;
  if (usd > thresholds.warn) return YELLOW;
  return GREEN;
}

module.exports = { formatTokens, formatUSD, contextBar, usdColor, pctColor, RESET, DIM, BOLD, YELLOW, RED, ORANGE };

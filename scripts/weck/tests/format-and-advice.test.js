'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { loadPricing } = require('../lib/cost');
const { formatTokens, formatUSD, contextBar, usdColor } = require('../lib/format');
const { evaluateAdvice, buildCompactCommand, buildAdvisorContext } = require('../lib/compact-advice');

const pricing = loadPricing();
const cfg = pricing.compact;

test('formatTokens abbreviates with k and M', () => {
  assert.equal(formatTokens(0), '0');
  assert.equal(formatTokens(999), '999');
  assert.equal(formatTokens(1234), '1.2k');
  assert.equal(formatTokens(262221), '262k');
  assert.equal(formatTokens(8_200_000), '8.2M');
});

test('formatUSD keeps cents for small amounts and drops them for large ones', () => {
  assert.equal(formatUSD(0.5), '$0.50');
  assert.equal(formatUSD(12.345), '$12.35');
  assert.equal(formatUSD(123.4), '$123');
});

test('contextBar fills proportionally and clamps', () => {
  const plain = (s) => s.replace(/\x1b\[[0-9;]*m/g, '');
  assert.equal(plain(contextBar(0, 10)), '░░░░░░░░░░');
  assert.equal(plain(contextBar(50, 10)), '█████░░░░░');
  assert.equal(plain(contextBar(250, 10)), '██████████');
  assert.equal(plain(contextBar(-5, 10)), '░░░░░░░░░░');
});

test('usdColor escalates with the configured thresholds', () => {
  const t = pricing.thresholdsUSD;
  const colors = [0.1, t.warn + 0.01, t.high + 0.01, t.alarm + 0.01].map((v) => usdColor(v, t));
  assert.equal(new Set(colors).size, 4);
});

test('no advice below the threshold and the bucket state resets', () => {
  const r = evaluateAdvice({ tokens: 100000, lastBucket: 3, cfg });
  assert.equal(r.advise, false);
  assert.equal(r.nextBucket, -1);
});

test('advice fires once at the threshold and not again within the same bucket', () => {
  const first = evaluateAdvice({ tokens: 150000, lastBucket: -1, cfg });
  assert.equal(first.advise, true);
  assert.equal(first.nextBucket, 0);
  const again = evaluateAdvice({ tokens: 180000, lastBucket: 0, cfg });
  assert.equal(again.advise, false);
  assert.equal(again.nextBucket, 0);
});

test('advice fires again after the context grows by another interval', () => {
  const r = evaluateAdvice({ tokens: 150000 + cfg.repeatEveryTokens, lastBucket: 0, cfg });
  assert.equal(r.advise, true);
  assert.equal(r.nextBucket, 1);
});

test('advice is urgent past the urgent threshold', () => {
  assert.equal(evaluateAdvice({ tokens: 310000, lastBucket: -1, cfg }).urgent, true);
  assert.equal(evaluateAdvice({ tokens: 200000, lastBucket: -1, cfg }).urgent, false);
});

test('compact command is a single pasteable line that carries session facts', () => {
  const cmd = buildCompactCommand({
    cwd: '/Users/me/dev/cashea',
    branch: 'feature/x',
    modifiedFiles: ['/a/one.js', '/a/two.js']
  });
  assert.ok(cmd.startsWith('/compact '));
  assert.ok(!cmd.includes('\n'));
  assert.ok(cmd.includes('/a/one.js') && cmd.includes('/a/two.js'));
  assert.ok(cmd.includes('feature/x'));
  assert.ok(cmd.length < 1500);
});

test('compact command caps the file list and stays within length', () => {
  const files = Array.from({ length: 200 }, (_, i) => `/very/long/path/to/module/number/${i}/file.js`);
  const cmd = buildCompactCommand({ cwd: '/x', branch: '', modifiedFiles: files });
  assert.ok(cmd.length < 1500);
  assert.ok(cmd.includes('file.js'));
});

test('advisor context tells the model to relay the command and mentions per-turn cost', () => {
  const text = buildAdvisorContext({
    tokens: 262000,
    urgent: false,
    perTurnUSD: 0.063,
    command: '/compact keep things'
  });
  assert.ok(text.includes('/compact keep things'));
  assert.ok(text.includes('262k'));
  assert.ok(text.includes('$0.06'));
  assert.ok(/Spanish/.test(text));
});

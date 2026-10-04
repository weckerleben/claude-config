'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { loadPricing } = require('../lib/cost');
const { scanFile, emptyFileState, aggregateSession } = require('../lib/transcript');

const pricing = loadPricing();
const close = (actual, expected) => assert.ok(Math.abs(actual - expected) < 1e-9, `${actual} !== ${expected}`);

const tmp = () => fs.mkdtempSync(path.join(os.tmpdir(), 'weck-test-'));

const usage = (over = {}) => ({
  input_tokens: 10,
  output_tokens: 100,
  cache_read_input_tokens: 1000,
  cache_creation_input_tokens: 500,
  cache_creation: { ephemeral_5m_input_tokens: 0, ephemeral_1h_input_tokens: 500 },
  ...over
});

const assistant = (id, over = {}, content = [{ type: 'text', text: 'hi' }]) =>
  JSON.stringify({
    type: 'assistant',
    requestId: `req_${id}`,
    message: { id, model: 'claude-sonnet-5-5', usage: usage(over), content }
  });

const write = (file, lines, { trailingNewline = true } = {}) =>
  fs.writeFileSync(file, lines.join('\n') + (trailingNewline ? '\n' : ''));

// Sonnet 5.5, usage above: 10*2 + 100*10 + 1000*0.2 + 500*4 = per-million sums
const ONE_MESSAGE_USD = (10 * 2 + 100 * 10 + 1000 * 0.2 + 500 * 4) / 1e6;

test('records that repeat the same message id are counted once', () => {
  const dir = tmp();
  const file = path.join(dir, 's.jsonl');
  write(file, [assistant('m1'), assistant('m1'), assistant('m1'), assistant('m2')]);
  const state = scanFile(file, emptyFileState(), pricing);
  assert.equal(state.totals.messages, 2);
  close(state.totals.usd, ONE_MESSAGE_USD * 2);
  assert.equal(state.totals.output, 200);
});

test('non-assistant records and synthetic messages are ignored', () => {
  const dir = tmp();
  const file = path.join(dir, 's.jsonl');
  const synthetic = JSON.stringify({
    type: 'assistant',
    message: { id: 'x', model: '<synthetic>', usage: usage() }
  });
  write(file, [JSON.stringify({ type: 'user', message: { content: 'hola' } }), synthetic, 'not json', assistant('m1')]);
  const state = scanFile(file, emptyFileState(), pricing);
  assert.equal(state.totals.messages, 1);
});

test('incremental scanning matches a full scan and skips partial lines', () => {
  const dir = tmp();
  const file = path.join(dir, 's.jsonl');
  const lines = [assistant('m1'), assistant('m1'), assistant('m2'), assistant('m3')];

  write(file, lines.slice(0, 2));
  fs.appendFileSync(file, lines[2].slice(0, 40)); // incomplete line, no newline yet
  const first = scanFile(file, emptyFileState(), pricing);
  assert.equal(first.totals.messages, 1);

  fs.writeFileSync(file, lines.slice(0, 4).join('\n') + '\n');
  const second = scanFile(file, first, pricing);
  const full = scanFile(file, emptyFileState(), pricing);
  assert.deepEqual(second.totals, full.totals);
});

test('a truncated or rewritten file resets the running totals', () => {
  const dir = tmp();
  const file = path.join(dir, 's.jsonl');
  write(file, [assistant('m1'), assistant('m2'), assistant('m3')]);
  const before = scanFile(file, emptyFileState(), pricing);
  write(file, [assistant('n1')]);
  const after = scanFile(file, before, pricing);
  assert.equal(after.totals.messages, 1);
});

test('context size comes from the most recent assistant message', () => {
  const dir = tmp();
  const file = path.join(dir, 's.jsonl');
  write(file, [
    assistant('m1', { cache_read_input_tokens: 5000 }),
    assistant('m2', { input_tokens: 7, cache_read_input_tokens: 90000, cache_creation_input_tokens: 3000, cache_creation: undefined })
  ]);
  const state = scanFile(file, emptyFileState(), pricing);
  assert.equal(state.context.tokens, 7 + 90000 + 3000);
  assert.equal(state.context.model, 'claude-sonnet-5-5');
});

test('modified files are collected from edit tool calls, most recent last, deduplicated', () => {
  const dir = tmp();
  const file = path.join(dir, 's.jsonl');
  const tool = (name, file_path) => [{ type: 'tool_use', name, input: { file_path } }];
  write(file, [
    assistant('m1', {}, tool('Write', '/p/a.js')),
    assistant('m2', {}, tool('Edit', '/p/b.js')),
    assistant('m3', {}, tool('Read', '/p/never.js')),
    assistant('m4', {}, tool('Edit', '/p/a.js'))
  ]);
  const state = scanFile(file, emptyFileState(), pricing);
  assert.deepEqual(state.files, ['/p/b.js', '/p/a.js']);
});

test('aggregateSession adds subagent transcripts and reports them separately', () => {
  const dir = tmp();
  const main = path.join(dir, 'sess1.jsonl');
  write(main, [assistant('m1')]);
  const subDir = path.join(dir, 'sess1', 'subagents');
  fs.mkdirSync(subDir, { recursive: true });
  write(path.join(subDir, 'agent-a.jsonl'), [assistant('a1'), assistant('a1'), assistant('a2')]);
  write(path.join(subDir, 'agent-b.jsonl'), [assistant('b1')]);

  const agg = aggregateSession({ transcriptPath: main, stateDir: tmp(), pricing });
  close(agg.main.usd, ONE_MESSAGE_USD);
  close(agg.agents.usd, ONE_MESSAGE_USD * 3);
  close(agg.total.usd, ONE_MESSAGE_USD * 4);
  assert.equal(agg.agentCount, 2);
});

test('aggregateSession persists state and a second call returns identical totals', () => {
  const dir = tmp();
  const stateDir = tmp();
  const main = path.join(dir, 'sess2.jsonl');
  write(main, [assistant('m1'), assistant('m2')]);
  const a = aggregateSession({ transcriptPath: main, stateDir, pricing });
  fs.appendFileSync(main, assistant('m3') + '\n');
  const b = aggregateSession({ transcriptPath: main, stateDir, pricing });
  close(a.total.usd, ONE_MESSAGE_USD * 2);
  close(b.total.usd, ONE_MESSAGE_USD * 3);
});

test('changing the pricing table invalidates cached totals', () => {
  const dir = tmp();
  const stateDir = tmp();
  const main = path.join(dir, 'sess3.jsonl');
  write(main, [assistant('m1')]);
  const a = aggregateSession({ transcriptPath: main, stateDir, pricing });
  const cheaper = JSON.parse(JSON.stringify(pricing));
  cheaper.models['sonnet-5-5'].output = 0;
  const b = aggregateSession({ transcriptPath: main, stateDir, pricing: cheaper });
  assert.ok(b.total.usd < a.total.usd);
});

test('a missing transcript yields zeroed totals instead of throwing', () => {
  const agg = aggregateSession({ transcriptPath: path.join(tmp(), 'nope.jsonl'), stateDir: tmp(), pricing });
  assert.equal(agg.total.usd, 0);
  assert.equal(agg.context, null);
});

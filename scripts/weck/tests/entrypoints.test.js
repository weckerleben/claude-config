'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { spawnSync } = require('child_process');
const fs = require('fs');
const os = require('os');
const path = require('path');

const STATUSLINE = path.join(__dirname, '..', 'statusline.js');
const ADVISOR = path.join(__dirname, '..', 'compact-advisor.js');
const strip = (s) => s.replace(/\x1b\[[0-9;]*m/g, '');

const assistant = (id, cacheRead) =>
  JSON.stringify({
    type: 'assistant',
    message: {
      id,
      model: 'claude-sonnet-5-5',
      usage: { input_tokens: 5, output_tokens: 1000, cache_read_input_tokens: cacheRead, cache_creation_input_tokens: 2000 },
      content: [{ type: 'tool_use', name: 'Edit', input: { file_path: '/repo/src/app.js' } }]
    }
  });

function fixture(cacheRead) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'weck-entry-'));
  const transcript = path.join(dir, 'abc-session.jsonl');
  fs.writeFileSync(transcript, `${assistant('m1', cacheRead)}\n${assistant('m1', cacheRead)}\n`);
  return { dir, transcript };
}

const run = (script, input, env = {}) =>
  spawnSync('node', [script], {
    input: JSON.stringify(input),
    encoding: 'utf8',
    env: { ...process.env, WECK_STATE_DIR: env.stateDir, ...env.extra }
  });

test('statusline prints context, cost with margin, and token breakdown on two lines', () => {
  const { dir, transcript } = fixture(40000);
  const out = run(STATUSLINE, {
    model: { id: 'claude-sonnet-5-5', display_name: 'Sonnet 5.5' },
    workspace: { current_dir: dir },
    transcript_path: transcript
  }, { stateDir: dir });
  assert.equal(out.status, 0);
  const lines = strip(out.stdout).trimEnd().split('\n');
  assert.equal(lines.length, 2);
  assert.ok(lines[0].includes('Sonnet 5.5'));
  assert.ok(/\d+%/.test(lines[0]));
  assert.ok(lines[1].includes('~$'));
  assert.ok(lines[1].includes('+20%'));
  assert.ok(/in \d/.test(lines[1]) && /out \d/.test(lines[1]) && /cache r/.test(lines[1]));
  assert.ok(!lines[0].includes('COMPACTAR'));
});

test('statusline flags COMPACTAR once context passes the advise threshold', () => {
  const { dir, transcript } = fixture(200000);
  const out = run(STATUSLINE, {
    model: { id: 'claude-sonnet-5-5', display_name: 'Sonnet 5.5' },
    workspace: { current_dir: dir },
    transcript_path: transcript
  }, { stateDir: dir });
  assert.ok(strip(out.stdout).includes('COMPACTAR'));
});

test('statusline survives empty stdin and a missing transcript', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'weck-entry-'));
  const empty = spawnSync('node', [STATUSLINE], { input: '', encoding: 'utf8' });
  assert.equal(empty.status, 0);
  const missing = run(STATUSLINE, { model: { display_name: 'X' }, transcript_path: path.join(dir, 'nope.jsonl') }, { stateDir: dir });
  assert.equal(missing.status, 0);
});

test('advisor stays silent below the threshold', () => {
  const { dir, transcript } = fixture(40000);
  const out = run(ADVISOR, { session_id: 'abc-session', transcript_path: transcript, cwd: '/repo' }, { stateDir: dir });
  assert.equal(out.status, 0);
  assert.equal(out.stdout.trim(), '');
});

test('advisor emits a ready-to-paste /compact command once, then stays quiet', () => {
  const { dir, transcript } = fixture(200000);
  const input = { session_id: 'abc-session', transcript_path: transcript, cwd: '/repo', hook_event_name: 'UserPromptSubmit' };
  const first = run(ADVISOR, input, { stateDir: dir });
  const payload = JSON.parse(first.stdout);
  assert.equal(payload.hookSpecificOutput.hookEventName, 'UserPromptSubmit');
  assert.ok(payload.hookSpecificOutput.additionalContext.includes('/compact Preserve:'));
  assert.ok(payload.hookSpecificOutput.additionalContext.includes('src/app.js'));
  const second = run(ADVISOR, input, { stateDir: dir });
  assert.equal(second.stdout.trim(), '');
});

test('advisor never fails the hook on bad input', () => {
  const out = spawnSync('node', [ADVISOR], { input: 'not json', encoding: 'utf8' });
  assert.equal(out.status, 0);
});

function expensiveFixture({ cacheRead = 1000, output = 1_000_000 } = {}) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'weck-entry-'));
  const transcript = path.join(dir, 'cost-session.jsonl');
  const record = JSON.stringify({
    type: 'assistant',
    message: {
      id: 'big',
      model: 'claude-sonnet-5-5',
      usage: { input_tokens: 5, output_tokens: output, cache_read_input_tokens: cacheRead, cache_creation_input_tokens: 0 },
      content: []
    }
  });
  fs.writeFileSync(transcript, `${record}\n`);
  return { dir, transcript };
}

test('advisor emits a cost notice when spend crosses a step, even with a small context', () => {
  const { dir, transcript } = expensiveFixture(); // ~$10 raw -> ~$12 with margin
  const input = { session_id: 'cost-session', transcript_path: transcript, cwd: '/repo' };
  const first = run(ADVISOR, input, { stateDir: dir });
  const context = JSON.parse(first.stdout).hookSpecificOutput.additionalContext;
  assert.ok(context.includes('[Cost notice]'));
  assert.ok(context.includes('~$12.00'));
  assert.ok(!context.includes('[Compact advisor]'));
  assert.equal(run(ADVISOR, input, { stateDir: dir }).stdout.trim(), '');
});

test('advisor joins cost notice and compact advice in one payload', () => {
  const { dir, transcript } = expensiveFixture({ cacheRead: 200000 });
  const input = { session_id: 'cost-session', transcript_path: transcript, cwd: '/repo' };
  const context = JSON.parse(run(ADVISOR, input, { stateDir: dir }).stdout).hookSpecificOutput.additionalContext;
  assert.ok(context.includes('[Cost notice]') && context.includes('[Compact advisor]'));
});

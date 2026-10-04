'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { spawnSync } = require('child_process');
const { loadPricing } = require('../lib/cost');
const { projectKey, findLatestTranscript, listSessions, renderReport, renderTable } = require('../lib/report');

const pricing = loadPricing();
const CLI = path.join(__dirname, '..', 'cost-report.js');
const tmp = () => fs.mkdtempSync(path.join(os.tmpdir(), 'weck-report-'));

const line = (id, cacheRead = 1000) =>
  JSON.stringify({
    type: 'assistant',
    message: {
      id,
      model: 'claude-sonnet-5-5',
      usage: { input_tokens: 10, output_tokens: 100, cache_read_input_tokens: cacheRead, cache_creation_input_tokens: 0 },
      content: []
    }
  });

function seed(projectsDir, project, session, mtimeSec, lines = [line('m1')]) {
  const dir = path.join(projectsDir, project);
  fs.mkdirSync(dir, { recursive: true });
  const file = path.join(dir, `${session}.jsonl`);
  fs.writeFileSync(file, `${lines.join('\n')}\n`);
  fs.utimesSync(file, mtimeSec, mtimeSec);
  return file;
}

test('projectKey mirrors how Claude Code names project folders', () => {
  assert.equal(projectKey('/Users/me/dev/cashea'), '-Users-me-dev-cashea');
  assert.equal(projectKey('/Users/me/.claude'), '-Users-me--claude');
});

test('findLatestTranscript prefers the newest session of the current project', () => {
  const projects = tmp();
  seed(projects, '-Users-me-dev-app', 'old', 1000);
  const newest = seed(projects, '-Users-me-dev-app', 'new', 2000);
  seed(projects, '-Users-me-other', 'other', 3000);
  assert.equal(findLatestTranscript({ projectsDir: projects, cwd: '/Users/me/dev/app' }), newest);
});

test('findLatestTranscript falls back to the newest session anywhere', () => {
  const projects = tmp();
  seed(projects, '-a', 's1', 1000);
  const newest = seed(projects, '-b', 's2', 2000);
  assert.equal(findLatestTranscript({ projectsDir: projects, cwd: '/nowhere' }), newest);
});

test('findLatestTranscript returns null when there is nothing', () => {
  assert.equal(findLatestTranscript({ projectsDir: tmp(), cwd: '/x' }), null);
});

test('listSessions returns the newest sessions first with their costs', () => {
  const projects = tmp();
  seed(projects, '-a', 'older', 1000, [line('a1')]);
  seed(projects, '-a', 'newer', 2000, [line('b1'), line('b2')]);
  const rows = listSessions({ projectsDir: projects, limit: 5, pricing, stateDir: tmp() });
  assert.deepEqual(rows.map((r) => r.id), ['newer', 'older']);
  assert.equal(rows[0].totals.messages, 2);
  assert.ok(rows[0].totals.usd > rows[1].totals.usd);
});

test('listSessions honors the limit', () => {
  const projects = tmp();
  for (let i = 0; i < 4; i++) seed(projects, '-a', `s${i}`, 1000 + i);
  assert.equal(listSessions({ projectsDir: projects, limit: 2, pricing, stateDir: tmp() }).length, 2);
});

test('renderReport shows raw and margin amounts, tokens, context and per-turn cost', () => {
  const totals = { input: 168, output: 107000, cacheRead: 17_000_000, cacheWrite: 401000, usd: 1, web: 0, messages: 79, unknownMessages: 0 };
  const text = renderReport({
    id: 'abc12345-rest',
    session: {
      main: totals,
      agents: { ...totals, usd: 0.5, messages: 10 },
      total: { ...totals, usd: 1.5 },
      agentCount: 2,
      context: { tokens: 343000, model: 'claude-sonnet-5-5' },
      modifiedFiles: []
    },
    pricing,
    margin: 1.2
  });
  assert.ok(text.includes('abc12345'));
  assert.ok(text.includes('~$1.80'));
  assert.ok(text.includes('raw $1.50'));
  assert.ok(text.includes('+20%'));
  assert.ok(text.includes('out 107k'));
  assert.ok(text.includes('343k'));
  assert.ok(text.includes('agents ~$0.60'));
  assert.ok(/per turn|turno/i.test(text));
  assert.ok(!/\x1b\[/.test(text));
});

test('renderReport warns about unknown models', () => {
  const totals = { input: 1, output: 1, cacheRead: 1, cacheWrite: 1, usd: 1, web: 0, messages: 1, unknownMessages: 1 };
  const text = renderReport({
    id: 'x',
    session: { main: totals, agents: { ...totals, usd: 0, messages: 0, unknownMessages: 0 }, total: totals, agentCount: 0, context: null, modifiedFiles: [] },
    pricing,
    margin: 1.2
  });
  assert.ok(/unknown model/i.test(text));
});

test('renderTable lists one row per session', () => {
  const projects = tmp();
  seed(projects, '-a', 's1', 1000);
  seed(projects, '-a', 's2', 2000);
  const rows = listSessions({ projectsDir: projects, limit: 5, pricing, stateDir: tmp() });
  const text = renderTable(rows, 1.2);
  assert.ok(text.includes('s1') && text.includes('s2'));
  assert.equal(text.trimEnd().split('\n').length, 3);
});

test('cost-report CLI prints the latest session and supports --all and --json', () => {
  const projects = tmp();
  seed(projects, '-Users-me-proj', 'sess-aaaa', 2000, [line('m1'), line('m2')]);
  const env = { ...process.env, WECK_PROJECTS_DIR: projects, WECK_STATE_DIR: tmp() };

  const plain = spawnSync('node', [CLI, '--cwd', '/Users/me/proj'], { encoding: 'utf8', env });
  assert.equal(plain.status, 0);
  assert.ok(plain.stdout.includes('sess-aaa'));
  assert.ok(plain.stdout.includes('~$'));

  const all = spawnSync('node', [CLI, '--all'], { encoding: 'utf8', env });
  assert.equal(all.status, 0);
  assert.ok(all.stdout.includes('sess-aaaa'));

  const json = spawnSync('node', [CLI, '--json', '--cwd', '/Users/me/proj'], { encoding: 'utf8', env });
  const parsed = JSON.parse(json.stdout);
  assert.equal(parsed.id, 'sess-aaaa');
  assert.ok(parsed.shownUSD > 0);
});

test('cost-report CLI explains itself when no sessions exist', () => {
  const env = { ...process.env, WECK_PROJECTS_DIR: tmp(), WECK_STATE_DIR: tmp() };
  const out = spawnSync('node', [CLI], { encoding: 'utf8', env });
  assert.equal(out.status, 0);
  assert.ok(/no session/i.test(out.stdout));
});

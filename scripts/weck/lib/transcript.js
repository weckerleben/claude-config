'use strict';

const crypto = require('crypto');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { usageCostUSD } = require('./cost');

const EDIT_TOOLS = new Set(['Edit', 'Write', 'MultiEdit', 'NotebookEdit']);
const RECENT_WINDOW = 300;
const FILES_KEEP = 40;
const NEWLINE = 0x0a;

const emptyTotals = () => ({
  input: 0,
  output: 0,
  cacheRead: 0,
  cacheWrite: 0,
  usd: 0,
  web: 0,
  messages: 0,
  unknownMessages: 0
});

const emptyFileState = () => ({
  offset: 0,
  totals: emptyTotals(),
  recent: {},
  order: [],
  context: null,
  files: []
});

function combine(a, b, sign = 1) {
  return {
    input: a.input + sign * b.input,
    output: a.output + sign * b.output,
    cacheRead: a.cacheRead + sign * b.cacheRead,
    cacheWrite: a.cacheWrite + sign * b.cacheWrite,
    usd: a.usd + sign * b.usd,
    web: a.web + sign * b.web,
    messages: a.messages + sign * b.messages,
    unknownMessages: a.unknownMessages + sign * b.unknownMessages
  };
}

const sumTotals = (list) => list.reduce((acc, t) => combine(acc, t), emptyTotals());

function contributionOf(message, pricing) {
  const cost = usageCostUSD(message.usage, message.model, pricing);
  return {
    input: cost.tokens.input,
    output: cost.tokens.output,
    cacheRead: cost.tokens.cacheRead,
    cacheWrite: cost.tokens.cacheWrite,
    usd: cost.usd,
    web: cost.web,
    messages: 1,
    unknownMessages: cost.known ? 0 : 1
  };
}

function touchedFile(block) {
  if (!block || block.type !== 'tool_use' || !EDIT_TOOLS.has(block.name) || !block.input) return null;
  const file = block.input.file_path || block.input.notebook_path;
  return typeof file === 'string' ? file : null;
}

function parseLine(line) {
  try {
    return JSON.parse(line);
  } catch {
    return null;
  }
}

function readTail(filePath, offset, size) {
  const fd = fs.openSync(filePath, 'r');
  try {
    const buffer = Buffer.alloc(size - offset);
    fs.readSync(fd, buffer, 0, buffer.length, offset);
    return buffer;
  } finally {
    fs.closeSync(fd);
  }
}

function applyRecord(state, record, pricing) {
  const message = record && record.message;
  if (!record || record.type !== 'assistant' || !message) return state;

  let { totals, recent, order, context, files } = state;

  if (message.usage && message.model !== '<synthetic>') {
    const id = message.id || record.requestId || record.uuid;
    const contribution = contributionOf(message, pricing);
    const previous = recent[id];
    totals = previous ? combine(totals, previous, -1) : totals;
    totals = combine(totals, contribution);
    recent = { ...recent, [id]: contribution };
    order = previous ? order : [...order, id];

    while (order.length > RECENT_WINDOW) {
      const { [order[0]]: _evicted, ...rest } = recent;
      recent = rest;
      order = order.slice(1);
    }

    const tokens = contribution.input + contribution.cacheRead + contribution.cacheWrite;
    context = tokens > 0 ? { tokens, model: message.model } : context;
  }

  if (Array.isArray(message.content)) {
    for (const block of message.content) {
      const file = touchedFile(block);
      if (file) files = [...files.filter((f) => f !== file), file].slice(-FILES_KEEP);
    }
  }

  return { ...state, totals, recent, order, context, files };
}

/**
 * Incrementally scan a transcript from the saved offset. Only complete lines
 * are consumed; messages repeated across content blocks are counted once.
 */
function scanFile(filePath, state, pricing) {
  let size;
  try {
    size = fs.statSync(filePath).size;
  } catch {
    return emptyFileState();
  }

  const base = size < state.offset ? emptyFileState() : state;
  if (size === base.offset) return base;

  const buffer = readTail(filePath, base.offset, size);
  const lastNewline = buffer.lastIndexOf(NEWLINE);
  if (lastNewline === -1) return base;

  const lines = buffer.subarray(0, lastNewline + 1).toString('utf8').split('\n');
  let next = { ...base, offset: base.offset + lastNewline + 1 };
  for (const line of lines) {
    if (line.trim()) next = applyRecord(next, parseLine(line), pricing);
  }
  return next;
}

const pricingStamp = (pricing) =>
  crypto
    .createHash('sha1')
    .update(JSON.stringify([pricing.models, pricing.webSearchPerRequest, pricing.usGeoMultiplier, pricing.fallbackModel]))
    .digest('hex');

function readJson(file) {
  try {
    return JSON.parse(fs.readFileSync(file, 'utf8'));
  } catch {
    return null;
  }
}

function writeJsonAtomic(file, value) {
  const tmp = `${file}.${process.pid}.tmp`;
  try {
    fs.writeFileSync(tmp, JSON.stringify(value));
    fs.renameSync(tmp, file);
  } catch {
    try {
      fs.rmSync(tmp, { force: true });
    } catch {
      /* best effort */
    }
  }
}

function listSubagentTranscripts(transcriptPath) {
  const sessionId = path.basename(transcriptPath, '.jsonl');
  const dir = path.join(path.dirname(transcriptPath), sessionId, 'subagents');
  try {
    return fs
      .readdirSync(dir)
      .filter((name) => name.endsWith('.jsonl'))
      .sort()
      .map((name) => path.join(dir, name));
  } catch {
    return [];
  }
}

/**
 * Cost and token totals for a whole session: the main transcript plus every
 * subagent transcript. State is cached in `stateDir` so refreshes stay cheap.
 */
function aggregateSession({ transcriptPath, stateDir = os.tmpdir(), pricing }) {
  const sessionId = path.basename(transcriptPath, '.jsonl');
  const stamp = pricingStamp(pricing);
  const stateFile = path.join(stateDir, `weck-cost-${sessionId}.json`);
  const saved = readJson(stateFile);
  const previous = saved && saved.stamp === stamp ? saved.files : {};

  const subagentPaths = listSubagentTranscripts(transcriptPath);
  const files = {};
  for (const file of [transcriptPath, ...subagentPaths]) {
    files[file] = scanFile(file, previous[file] || emptyFileState(), pricing);
  }
  writeJsonAtomic(stateFile, { stamp, files });

  const main = files[transcriptPath];
  const agentStates = subagentPaths.map((p) => files[p]);
  const agents = sumTotals(agentStates.map((s) => s.totals));

  return {
    main: main.totals,
    agents,
    total: combine(main.totals, agents),
    agentCount: agentStates.filter((s) => s.totals.messages > 0).length,
    context: main.context,
    modifiedFiles: main.files
  };
}

module.exports = { scanFile, emptyFileState, aggregateSession };

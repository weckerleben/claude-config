#!/usr/bin/env node
/**
 * spec-trace-guard — PostToolUse hook for the PRD → RFC → ADR → Plan chain.
 *
 * When a spec artifact is written or edited, name the downstream artifacts that
 * are now suspect. Does not block; it reports what needs re-checking, because
 * the failure mode this chain has is not a missing document, it is a document
 * that silently stopped matching its parent.
 *
 * Enforcement level via env SPEC_TRACE_GUARD:
 *   feedback (default) — exit 2, message goes back to Claude so it acts on it
 *   warn               — exit 0, message shown in the transcript only
 *   off                — no-op
 */
'use strict';
const fs = require('fs');
const path = require('path');

const LEVEL = process.env.SPEC_TRACE_GUARD || 'feedback';
if (LEVEL === 'off') process.exit(0);

let raw = '';
process.stdin.on('data', (c) => (raw += c));
process.stdin.on('end', () => {
  let input;
  try { input = JSON.parse(raw); } catch { process.exit(0); }

  const file = input?.tool_input?.file_path;
  if (!file) process.exit(0);

  const kind = classify(file);
  if (!kind) process.exit(0);

  const root = repoRoot(path.dirname(path.resolve(file)));
  const id = readId(file);
  const notes = downstream(kind, id, file, root);
  if (!notes.length) process.exit(0);

  const out = [
    `[spec-trace] ${kind.toUpperCase()} edited: ${path.basename(file)}${id ? ` (${id})` : ''}`,
    ...notes.map((n) => `  · ${n}`),
    '  · Rewrite in place — never append a changelog to a spec document.',
  ].join('\n');

  if (LEVEL === 'warn') { console.log(out); process.exit(0); }
  console.error(out);
  process.exit(2);
});

function classify(f) {
  const p = f.replace(/\\/g, '/');
  if (/\.prd\.md$/.test(p)) return 'prd';
  if (/\/RFC-\d{4}-[^/]*\.md$/.test(p)) return 'rfc';
  if (/\/ADR-\d{4}-[^/]*\.md$/.test(p)) return 'adr';
  return null;
}

const SKIP = new Set(['node_modules', '.git', '.venv', 'venv', 'dist', 'build', '.ruff_cache', '.pytest_cache']);

/** Find every directory holding RFC-NNNN-*.md / ADR-NNNN-*.md, wherever the repo keeps them. */
function findCorpus(root) {
  const rfcs = [], adrs = [];
  const walk = (dir, depth) => {
    if (depth > 4) return;
    let entries;
    try { entries = fs.readdirSync(dir, { withFileTypes: true }); } catch { return; }
    for (const e of entries) {
      const full = path.join(dir, e.name);
      if (e.isDirectory()) { if (!SKIP.has(e.name)) walk(full, depth + 1); continue; }
      if (/^RFC-\d{4}-.*\.md$/.test(e.name)) rfcs.push(full);
      else if (/^ADR-\d{4}-.*\.md$/.test(e.name)) adrs.push(full);
    }
  };
  walk(root, 0);
  return { rfcs, adrs };
}

function repoRoot(dir) {
  let cur = dir;
  for (let i = 0; i < 12; i++) {
    if (fs.existsSync(path.join(cur, '.git')) || fs.existsSync(path.join(cur, '.claude'))) return cur;
    const up = path.dirname(cur);
    if (up === cur) break;
    cur = up;
  }
  return dir;
}

function readId(f) {
  try {
    const head = fs.readFileSync(f, 'utf8').slice(0, 2000);
    return (head.match(/^id:\s*([A-Z]+-[\w.-]+)/m) || [])[1] || null;
  } catch { return null; }
}

function listMd(dir) {
  try { return fs.readdirSync(dir).filter((f) => f.endsWith('.md')).map((f) => path.join(dir, f)); }
  catch { return []; }
}

/** Files whose frontmatter references `id`. */
function referencing(files, id) {
  if (!id) return [];
  return files.filter((f) => {
    try { return fs.readFileSync(f, 'utf8').slice(0, 3000).includes(id); }
    catch { return false; }
  }).map((f) => path.basename(f));
}

function downstream(kind, id, file, root) {
  const { rfcs, adrs } = findCorpus(root);
  const plans = listMd(path.join(root, '.claude', 'plans'));
  const notes = [];

  if (kind === 'prd') {
    const hits = referencing(rfcs, path.basename(file)).concat(referencing(rfcs, id));
    notes.push(hits.length
      ? `RFCs to re-read (Motivation and Non-goals, not a patch): ${[...new Set(hits)].join(', ')}`
      : 'No RFC references this PRD yet — if the change is cross-module, one is missing.');
    notes.push('If a requirement was added: it needs an acceptance clause, or it ships untested (customfield_12007).');
    notes.push('If a requirement was removed: any ADR whose only driver was it becomes `deprecated`, not deleted.');
  }

  if (kind === 'rfc') {
    const hitAdr = referencing(adrs, id);
    const hitPlan = referencing(plans, id);
    if (hitAdr.length) notes.push(`ADRs bound to this RFC: ${hitAdr.join(', ')} — a changed choice needs a NEW ADR that supersedes, never an edit.`);
    if (hitPlan.length) notes.push(`Plans derived from it: ${hitPlan.join(', ')} — re-check tasks against the new design.`);
    notes.push('Accepted RFC? Then it is immutable — supersede with a new RFC instead of editing.');
    notes.push('Acceptance criteria changed? Update the ticket acceptance field (tracker.fields.acceptance); a local file does not satisfy the gate.');
  }

  if (kind === 'adr') {
    const hitPlan = referencing(plans, id);
    if (hitPlan.length) notes.push(`Plans citing it: ${hitPlan.join(', ')} — constraints_from_adr may be stale.`);
    let head = '';
    try { head = fs.readFileSync(file, 'utf8').slice(0, 2000); } catch {}
    const comps = ((head.match(/^components:\s*\[(.*)\]/m) || head.match(/^modules:\s*\[(.*)\]/m) || [])[1] || '').trim();
    const binds = ((head.match(/^affects_repos:\s*\[(.*)\]/m) || [])[1] || '').trim();
    if (comps) notes.push(`Grep these components for code that still follows the old decision: ${comps}`);
    if (binds) notes.push(`This decision also binds: ${binds} — check their code and their ADR corpus too.`);
    notes.push('Regenerate the index: bash ~/.claude/skills/adr-author/scripts/adr-index.sh');
  }

  return notes;
}

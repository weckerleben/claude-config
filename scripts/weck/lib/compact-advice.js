'use strict';

const path = require('path');
const { formatTokens, formatUSD } = require('./format');

const MAX_COMMAND_LENGTH = 1400;
const MAX_FILES = 10;
const MAX_PATH_LENGTH = 70;

/**
 * Decide whether to advise compaction. `lastBucket` is the bucket already
 * advised for this session (-1 when none); the advice repeats only after the
 * context grows by another `repeatEveryTokens`.
 */
function evaluateAdvice({ tokens, lastBucket, cfg }) {
  if (!Number.isFinite(tokens) || tokens < cfg.adviseAtTokens) {
    return { advise: false, urgent: false, nextBucket: -1 };
  }
  const bucket = Math.floor((tokens - cfg.adviseAtTokens) / cfg.repeatEveryTokens);
  return {
    advise: bucket > lastBucket,
    urgent: tokens >= cfg.urgentAtTokens,
    nextBucket: bucket
  };
}

function shortenPath(file, cwd) {
  const relative = cwd && file.startsWith(`${cwd}${path.sep}`) ? path.relative(cwd, file) : file;
  return relative.length > MAX_PATH_LENGTH ? `…${relative.slice(-(MAX_PATH_LENGTH - 1))}` : relative;
}

function render({ repo, branch, files }) {
  const where = `repo ${repo}${branch ? ` on branch ${branch}` : ''}`;
  const touched = files.length > 0 ? ` Files touched (most recent last): ${files.join(', ')}.` : '';
  return (
    "/compact Preserve: the user's current goal and the decisions made so far; why each file was changed; " +
    'test/build status and open errors; pending next steps; user preferences stated this session ' +
    '(chat in Paraguayan Spanish, code/commits/docs in English). ' +
    `Context: ${where}.${touched} ` +
    'Drop: raw tool output, dead-end exploration, large file dumps.'
  );
}

/**
 * Single-line `/compact <instructions>` command the user can paste as is.
 */
function buildCompactCommand({ cwd, branch, modifiedFiles }) {
  const repo = cwd ? path.basename(cwd) : 'current project';
  let files = (modifiedFiles || []).slice(-MAX_FILES).map((f) => shortenPath(f, cwd));
  let command = render({ repo, branch, files });
  while (command.length > MAX_COMMAND_LENGTH && files.length > 0) {
    files = files.slice(1);
    command = render({ repo, branch, files });
  }
  return command;
}

/**
 * Text injected into the model's context so it relays the advice to the user.
 */
function buildAdvisorContext({ tokens, urgent, perTurnUSD, command }) {
  const when = urgent
    ? 'NOW (context is very large)'
    : 'at the next logical boundary (if you are mid-implementation, right after finishing it)';
  return [
    `[Compact advisor] Session context is ~${formatTokens(tokens)} tokens and every turn re-reads it ` +
      `(~${formatUSD(perTurnUSD)} per turn, safety margin included).`,
    `Tell the user, in ONE short line in Spanish, that it is a good moment to compact ${when}, ` +
      'and give them this ready-to-paste command in a code block:',
    '```',
    command,
    '```',
    'Do not run /compact yourself.'
  ].join('\n');
}

module.exports = { evaluateAdvice, buildCompactCommand, buildAdvisorContext };

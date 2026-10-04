'use strict';

const { execFileSync } = require('child_process');

const GIT_TIMEOUT_MS = 300;

/** Current branch of `dir`, or '' when it is not a git checkout or git is slow. */
function currentBranch(dir) {
  if (!dir) return '';
  try {
    return execFileSync('git', ['-C', dir, 'symbolic-ref', '--quiet', '--short', 'HEAD'], {
      encoding: 'utf8',
      timeout: GIT_TIMEOUT_MS,
      stdio: ['ignore', 'pipe', 'ignore']
    }).trim();
  } catch {
    return '';
  }
}

module.exports = { currentBranch };

'use strict';

/**
 * Read stdin as JSON. Resolves to {} on empty, invalid or slow input so that
 * hooks and the statusline never fail because of what Claude Code sent.
 */
function readStdinJson(timeoutMs = 1000) {
  return new Promise((resolve) => {
    let data = '';
    const finish = () => {
      try {
        resolve(JSON.parse(data));
      } catch {
        resolve({});
      }
    };
    const timer = setTimeout(finish, timeoutMs);
    timer.unref();
    process.stdin.setEncoding('utf8');
    process.stdin.on('data', (chunk) => {
      data += chunk;
    });
    process.stdin.on('end', () => {
      clearTimeout(timer);
      finish();
    });
    process.stdin.on('error', () => {
      clearTimeout(timer);
      finish();
    });
  });
}

module.exports = { readStdinJson };

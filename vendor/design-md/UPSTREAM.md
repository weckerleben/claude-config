# design-md (Google DESIGN.md format + CLI)

- Source: https://github.com/google-labs-code/design.md (spec) and npm `@google/design.md@0.4.0` (CLI)
- Vendored: `spec.md` and `LICENSE` from the 0.4.0 tarball; `package-lock.json` pins 93 packages with integrity hashes
- License: Apache-2.0
- Audited: 2026-10-31
- Status of the format: **alpha** (spec header says `version: alpha`). Expect changes.

## Audit verdict: ADOPT with conditions

- npm package published by Google maintainers; no preinstall/postinstall scripts.
- Compiled code reads only debug/log-level env vars (from bundled `debug` and `consola`); no network, no child processes, no eval.
- Always installed with `--ignore-scripts` from the lockfile (see `design-md` wrapper).
- `npm audit`: 1 high advisory, zod "can exhaust memory while validating oversized constrained collections" (GHSA-mrhx-c7xc-m3w5), no upstream fix at audit time. Residual risk accepted: it needs an oversized hostile input. **Only lint DESIGN.md files you wrote. Never lint a file from an untrusted source.** Re-check `npm audit` when bumping.

## Known limitation

The `contrast-ratio` rule does not composite alpha. Translucent backgrounds (e.g. `#ffffff1a` glass cards) are reported as 1.00:1. Treat those as false positives and verify them against the real surface behind.

## Usage

```
~/.claude/vendor/design-md/design-md lint DESIGN.md
~/.claude/vendor/design-md/design-md export DESIGN.md --format css-vars   # also: dtcg, css-tailwind, json-tailwind
~/.claude/vendor/design-md/design-md diff OLD.md NEW.md
```

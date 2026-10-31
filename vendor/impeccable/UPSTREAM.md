# impeccable (design playbooks)

- Source: https://github.com/pbakaus/impeccable (skill v4.8.0)
- Pinned commit: 2f97a85a4a87a80066a693bd3546b092bd300772 (2026-10-31)
- License: Apache-2.0 (`LICENSE`, `NOTICE.md` kept as required)
- Audited: 2026-10-31
- Vendored: `SKILL.md` and `reference/*.md` ONLY

## Audit verdict: ADOPT, playbooks only (binary NOT adopted)

- High-quality, actively maintained design methodology: commands shape, critique, audit, polish, typeset, colorize, animate, layout, harden, onboard, clarify, distill, document (DESIGN.md), and more.
- **Deliberately excluded:** the `scripts/` folder. Its launcher downloads a native engine binary from GitHub releases (verified against a SHA-256 list pinned in the same repo, refuses unverified) and then executes it; `live-browser.js` injects a script into the page via a local server; the optional `hooks` command edits settings files. Not adopted without explicit approval from William.
- Scanned all Markdown for zero-width/bidi characters and prompt-injection phrasing: clean.

## How we use it

Read on demand by path from `orch-brand-system` and `orch-product-design`: `~/.claude/vendor/impeccable/reference/<command>.md`. Where `SKILL.md` says to run `scripts/impeccable context`, SKIP it: upstream documents the fallback of reading PRODUCT.md / DESIGN.md directly. Do not run `detect`, `live`, `hooks` or any script command. Not installed as a global skill (same hijack risk as intent).

## Updating

Re-audit before bumping, especially anything touching `scripts/`.

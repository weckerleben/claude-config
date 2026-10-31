# uiux-brand (brand references from ui-ux-pro-max-skill)

- Source: https://github.com/nextlevelbuilder/ui-ux-pro-max-skill, folder `.claude/skills/brand`
- Pinned commit: 9a3f14f7423037ccb8feeb4fee7482291b9c820e (2026-10-31)
- License: MIT
- Audited: 2026-10-31
- Vendored: `references/*.md` and `templates/*.md` ONLY (logo usage rules, color and typography specs, voice and messaging frameworks, consistency and approval checklists, brand guideline template)

## Audit verdict: ADOPT partially (Markdown only)

- Scripts (`scripts/*.cjs`, token sync, color extraction) NOT vendored: superseded by the DESIGN.md CLI export, and not read in full.
- Rest of that repo rejected: the `design` skill generates logos through third-party image APIs with user API keys (Gemini, Atlas Cloud, MuAPI; may cost money), and `ui-styling` runs `npx shadcn` through subprocess.
- Scanned Markdown for hidden characters and injection phrasing: clean.

## How we use it

Reference checklists read on demand by `orch-brand-system` (logo usage rules, consistency checklist, approval checklist). Not installed as a global skill.

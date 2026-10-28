# Retro mode: end-of-session review

Manual, on request ("debrief", "cerrar sesión"). Reads the current conversation; writes nothing until William approves.

Report in Spanish, this fixed shape:

1. **Evaluación general** — two sentences.
2. **Problemas concretos** — each with severity 🔴/🟡/🟢 and a real moment from the session (quote or point to the turn). Never invent a moment. If compaction cut coverage, say so.
3. **Qué salió bien** — only if there is something real.
4. **Mejoras sugeridas** — routed by destination (see Capture step 3).

Checks:
- **Regression**: compare each problem against `applied-changes.md` and memory. A mistake he already corrected before is a regression: raise its severity and route it to a hook, scoped where the rule was written (global CLAUDE.md → global hook).
- **Missing script**: 3+ near-identical tool calls in the session mean a script or skill is missing.
- **Scale**: a short session gets a short retro. Skip any section with nothing real, and end with a **Sin acción** list of what you checked and deliberately did not record.

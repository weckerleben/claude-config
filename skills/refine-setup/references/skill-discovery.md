# Discover mode: turn repeated workflows into skills

A skill is worth building when the same multi-step thing keeps happening and the steps are not obvious to a base model. Most candidates fail that test.

## Where workflows show up
- **Repeated skill/command use**: `python3 scripts/skill_usage.py` shows what he already invokes; heavy use of one skill plus manual follow-up steps suggests an extension.
- **Repeated tool sequences**: the same chain (for example read → edit → test → commit → push, or the same SSH + docker commands) across sessions. Grep tool_use blocks in transcripts.
- **Long instructions he retypes**: briefs of 160+ characters that start the same way in ≥2 sessions (the miner caps at 800 and ignores these, so grep for them).
- **His words**: "otra vez tengo que…", "cada vez que…", "armá lo mismo que…".

## Score before proposing
Count independent sessions (and projects) where the workflow appeared.
- 3 sessions → candidate (backlog, do not build yet)
- ≥6 sessions → strong
- ≥20 sessions across ≥2 projects → very strong

Propose only strong ones, and only if you can state a non-obvious value. Reject: things the base model does unprompted, one-off facts, anything better done as a plain script or alias.

## Near-miss check
Before accepting a pattern found by regex or clustering, read 5 sessions that match and 3 that look similar but are not the same workflow. If the near-misses fit just as well, the pattern is too broad ("debug", "refactor"); do not draft a skill from it.

## Proposal template
```
Nombre: <kebab-case>
Evidencia: <N sesiones, M proyectos, fechas>
Disparador: <frases reales suyas que lo activarían, incl. abreviadas>
Pasos: <3-7 pasos concretos>
Valor no obvio: <qué hace que valga la pena>
Pruebas: <un prompt directo, uno abreviado, uno vecino que NO debe disparar>
```

With his "sí", build it with the `skill-creator` skill and run its evals; do not hand-write a skill and call it done.

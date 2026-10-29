# Discover mode: turn repeated workflows into skills

A skill is worth building when the same multi-step thing keeps happening and the steps are not obvious to a base model. Most candidates fail that test.

## Where workflows show up
- **Repeated command shapes**: `python3 scripts/mine_workflows.py` reads the assistant's top-level work across all sessions and returns `family` (the same kind of command, e.g. `ssh <host>`), `chain` (an ordered run of two or three families) and `skill-chain` candidates, each with `session_count`, `projects` and redacted `examples`. It reads command shapes, not intent: open a few of the listed sessions to see what he was trying to do before proposing anything.
- **Repeated skill/command use**: `scripts/skill_usage.py`; heavy use of one skill plus manual follow-up steps suggests an extension.
- **Long instructions he retypes**: the same 160+ character brief in ≥2 sessions. The rule miner keeps only signal sentences of long messages, so grep for these by hand.
- **His words**: "otra vez tengo que…", "cada vez que…", "armá lo mismo que…".

## Score before proposing
Use `session_count` (independent sessions) and the number of `projects`.
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

# Repo profile

The chain is vertical-generic. Everything repo-specific — the stack, whether
there is a parallel-version axis at all, what a "component" is, the tracker
fields — is **data the repo declares**, not logic baked into the skills.

Resolve it before writing anything:

```bash
bash ~/.claude/skills/spec-flow/scripts/repo-profile.sh
```

Declared beats inferred. A repo with no profile still works — the script infers
one from markers and labels every inferred value as such, so nothing silently
pretends to be authoritative.

## Schema — `.claude/spec-flow.yml`

Committed in the repo, reviewed in PRs, ~15 lines.

```yaml
project: cashea-odoo
stack: odoo                    # odoo | python-service | node-service | terraform | data-pipeline
variant_axis: odoo_version     # none, when the repo has no parallel-version dimension
variants: [v16]
sibling_repos:
  - repo: cashea-odoo-v19      # cannot be inferred — a decision here may bind there
    variant: v19
docs:
  rfc: docs/rfc
  adr: docs/adr
tracker:
  jira_project: ODOO
  fields:
    prd: customfield_12004
    rfc_adr: customfield_12005
    acceptance: customfield_12007
language: {prd: es, rfc: es, adr: en}
```

Only two keys are worth arguing about; the rest is mechanical.

### `variant_axis`

The dimension along which the same decision can land differently. It exists in
some repos and not others, and **assuming it always exists is the mistake this
schema fixes**.

| Repo | Axis | Why |
|---|---|---|
| `cashea-odoo` / `cashea-odoo-v19` | `odoo_version` | v16 and v19 run in production in parallel; a design that covers one is half a design |
| `erp-service`, `debt-facility-ms`, `odoo-helpdesk-bot` | `none` | one deployable, one version |
| `cashea-iac-live` | `environment` | the same stack lands differently in dev / qa / prod, and prod is the one that matters |
| `data-eng-composer-repo` | `none` | |

When the axis is `none`, the RFC's variant section and the ADR's `variant:` field
**disappear from the document**. They are not filled with `n/a` — an empty
section trains people to skip sections.

### `sibling_repos`

The only field that cannot be inferred and the one that earns the schema. A
decision taken in `cashea-odoo` about the ledger contract usually binds
`cashea-odoo-v19` and often `erp-service`. Declaring the siblings is what makes
`adr-author` ask "does this ADR also apply over there?" instead of leaving the
other repo to discover it in six months.

Point them at each other. It is a graph, not a hierarchy.

## Inference, when there is no profile

Grounded in what these repos actually look like, not a generic table:

| Signal | Stack | Components | Axis |
|---|---|---|---|
| `__manifest__.py` with `depends` | `odoo` | top-level dirs holding a manifest | `odoo_version` |
| `package.json` | `node-service` | `src/*` | `none` |
| `pyproject.toml` + `alembic/` | `python-service` | packages with `__init__.py` | `none` |
| `*.tf` | `terraform` | top-level stacks | `environment` |

**Odoo version inference is deliberately weak.** The manifest `version` key is
unreliable — 26 of the 42 modules in `cashea-odoo` say `'1.0'`. The script falls
back to the repo name suffix and prints `UNKNOWN — declare it` when even that
fails. Do not paper over this with a guess; a wrong version on an ADR is worse
than a blank one.

## What replaced the Odoo-specific fields

| Before | Now | Meaning |
|---|---|---|
| `odoo_version: v16 \| v19 \| both` | `variant: <values from the profile's axis>` | omitted entirely when the axis is `none` |
| `modules: [...]` | `components: [...]` | Odoo modules, Python packages, TS workspaces, Terraform stacks — whatever this repo's unit is |

The ADR index groups by `components`, so "what did we already decide about
`cashea_account_factoring`" and "what did we already decide about
`src/infrastructure`" are the same query.

## Where the skills live

Two kinds of skill, two answers:

**Domain skills — one repo each.** `odoo-incident-rca` in `cashea-odoo/.claude/skills/`,
`odoo-postgres-tuning` in `cashea/.claude/skills/`. They only mean something in
that repo, they should travel with it, and they should be reviewed in its PRs.
This pattern is already in use and should stay.

**Process skills — one copy.** `spec-flow`, `rfc-author` and `adr-author` are
~95% identical wherever they run; only the profile differs. Eight copies means
eight drifts, and the drift is silent because nobody diffs skill files across
repos.

So: one copy of the logic, one profile per repo. Today the copy sits at
`~/.claude/skills/` and works with zero setup. When the team needs it, the same
three directories move into a plugin repo installed through a marketplace — the
mechanism already in use for ECC — and **nothing inside them changes**, because
by then they read the repo instead of assuming it.

Not `odoo-workflows`: it is named for one stack, which is the thing being
escaped, and today it holds only a README and a CODEOWNERS.

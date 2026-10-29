---
name: odoo-local-verify
description: >
  Verify an Odoo change (v16 or v19) locally BEFORE pushing or sending it to QA: preflight,
  throwaway database, install/update with odoo-bin --stop-after-init, run the module tests,
  read the result from the log FILE, count WARNING lines (zero-warnings policy), compare
  against a clean origin/main when something fails, and clean up. Use whenever the user says
  "probar en local", "probalo local antes de QA", "instalar el módulo", "actualizar el módulo",
  "correr los tests del módulo", "antes de mandar a QA", "antes de pushear", "verificar
  warnings", "base descartable", "createdb -T", "--stop-after-init", "--test-tags", "ci/odoo.sh
  está rojo, reproducilo local", or after finishing any change in an Odoo module that has not
  been run yet — even if the user never says "verify". Do NOT use to diagnose a failure that
  already happened on production/staging ("por qué falló X en producción", tracebacks pasted
  from Odoo.sh): that is odoo-incident-rca. Do NOT use for pure PostgreSQL tuning (indexes,
  slow queries): that is odoo-postgres-tuning. Not for writing module code (odoo-patterns).
---

# Odoo local verify

Why this exists: `qa` is a shared environment with an Odoo.sh build, and `ci/odoo.sh` goes
red (or yellow) on a single WARNING line. A local run catches that in minutes and keeps QA
clean. William wants every change tried locally before it goes to a PR/QA.

## Real layout on this machine (verified 2026-10-28)

Workspace is `~/dev/cashea` (NOT `~/dev/eagle`). Per version:

| | Odoo 19 (`cashea-odoo-v19`) | Odoo 16 (`cashea-odoo`) |
|---|---|---|
| core | `~/dev/cashea/odoo-src/odoo-19.0` (+ `enterprise-19.0`) | `~/dev/cashea/odoo-src/odoo-16.0` (+ `enterprise-16.0`) |
| venv | `~/dev/cashea/.odoo19/venv` | `~/dev/cashea/.odoo16/venv` |
| conf | `~/dev/cashea/.odoo19/odoo.conf` | `~/dev/cashea/.odoo16/odoo.conf` |
| log file | `~/dev/cashea/.odoo19/logs/odoo.log` | `~/dev/cashea/.odoo16/logs/odoo.log` |
| filestore | `~/dev/cashea/.odoo19/filestore/filestore/<db>` | `~/dev/cashea/.odoo16/filestore/filestore/<db>` |

Both confs have `addons_path` pointing at the MAIN checkout of the repo, `workers = 0`, a
`logfile`, and credentials in plain text: do not print or copy them (`sed` them out if you
must show the file). Postgres is local (brew), user `odoo`, port 5432. The venv is shared by
v16 and v19 projects: never `pip install` into it without asking; for experiments use a
throwaway venv in the scratchpad (see `references/recipes.md`). Check anything else (extra
conf, other venvs) with `ls ~/dev/cashea/.odoo19 ~/dev/cashea/.odoo16`.

## Workflow

0. **Resolve the tree under test.** Find the ticket branch (`git fetch origin; git branch -a --list '*ep-NNN*'`,
   branch names are lowercase). If it does not exist, stop and ask: the main checkout is usually on another ticket's
   branch and would test the wrong code. For a PR, `gh pr view <n> --json headRefName,state` first.
1. **Preflight.** `pg_isready`; which port is free (`lsof -iTCP -sTCP:LISTEN -P | grep -E ':(8069|8213)'`);
   which tree you are testing (`git -C <repo> branch --show-current`). A background v16
   instance often owns 8069, so pass `--http-port=8213 --http-interface=127.0.0.1` whenever
   tests run (Odoo starts HTTP in test mode even with `--no-http`; without the interface
   flag v19 emits a WARNING that breaks the zero-warnings policy).
2. **Point `addons_path` at the code under test.** The conf points at the main checkout. To test
   a branch other than the one checked out there, make a worktree ONLY at
   `~/dev/cashea/worktree/<repo>/<worktree>` (`git worktree add ...`; never beside the repo,
   inside it, or in /tmp) and override `--addons-path=<core addons>,<core odoo/addons>,<enterprise>,<worktree>`
   (same list as the conf, last entry swapped; read it with `grep -E '^(addons_path|data_dir|logfile)' <conf>`, never `cat`). If the branch is already checked out elsewhere, use `git worktree add --detach <path> <sha>`.
3. **Throwaway DB named after the ticket**: `createdb -U odoo epNNN_test` (host/password come
   from the conf or `PG*` env; do not hardcode). Never use an existing DB as a target (`odoo19_test`,
   `odoo16_test`, `odoo19_rbac` are shared; as a `-T` clone source it is fine, if nothing is connected to it) and never touch production/staging. Cloning with
   `createdb -T <db>` does NOT bring the filestore: copy `<data_dir>/filestore/<src>` to `<data_dir>/filestore/<new>` (data_dir is in the conf)
   by hand or attachments/images will be missing (check with `ls` first: a source may have none). On a clone skip `-i` and go straight to `-u`; for migration scripts bump the manifest `version` above the stored one and look for the migration lines in the log, since a green result alone does not prove they ran.
4. **Install, then test.** Install first without tests, then update with the module's tests:
   ```bash
   cd ~/dev/cashea && .odoo19/venv/bin/python odoo-src/odoo-19.0/odoo-bin -c .odoo19/odoo.conf \
     -d epNNN_test -i <module> --stop-after-init --no-http --without-demo=True \
     --log-file=<scratchpad>/epNNN_install.log
   ... -d epNNN_test -u <module> --test-tags=/<module> --stop-after-init \
     --http-port=8213 --http-interface=127.0.0.1 --log-file=<scratchpad>/epNNN_test.log
   ```
   A fresh install can take many minutes: run it in the background and wait on the log. Check that
   `odoo.tests.result` reports more than 0 tests, otherwise the tags matched nothing. In v16 use
   `--without-demo=all` (its documented form; `True` is the v19 form). For a CI-yellow/red reproduction the
   install log is the deliverable (Odoo.sh fails on any WARNING at load, before tests); derive modules with
   `git diff --name-only origin/main...HEAD | cut -d/ -f1 | sort -u`.
   Do not use `--test-enable` in v19 here: it loads the tests of every installed dependency
   and `auth_oidc` fails to import. v16 uses the same shape with `.odoo16/` and
   `odoo-src/odoo-16.0` (install/test notes: `references/recipes.md`). zsh has `noclobber`:
   use `>|` to overwrite files.
5. **Read the result from the log FILE, never stdout** (stdout is empty because of `logfile`):
   `grep -E "odoo.tests.result" <log>` and `grep -c " WARNING " <log>`; also
   `grep -E " (ERROR|CRITICAL) " <log>`. A WARNING counts as a failure: fix the root cause,
   never silence it (`# noqa`, filtering logs, disabling tests).
6. **If something fails, split own vs pre-existing**: repeat step 3-5 on a clean worktree of
   `origin/main` with its own DB (`epNNN_main`). Same failures there = pre-existing, report
   them as such; only new ones are yours. Known pre-existing noise is listed in
   `references/recipes.md`; re-verify it, do not trust it blindly.
7. **Clean up**: `dropdb epNNN_test epNNN_main`, remove the filestore dirs of your DBs (`<data_dir>/filestore/<db>`, also created by a plain `-i`),
   `git worktree remove <path>` and confirm with `git worktree list` that none of yours is
   left. The branch survives, only the folder goes.

## Report

State: version, tree/branch tested, DB name, commands (without credentials), the
`odoo.tests.result` line(s), WARNING count (and each distinct WARNING text), own vs
pre-existing failures, and what was cleaned. If the change has UI, leave a local env ready
and wait for William's OK before anything goes to a PR or QA.

More commands, v16 specifics and known failures: `references/recipes.md`.

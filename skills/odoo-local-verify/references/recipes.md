# Recipes and known gotchas (verified 2026-10-28 from project memory and the real tree)

Re-verify before relying on any of this; main moves.

## Odoo 16 (cashea-odoo)
- Same command shape as v19 with `.odoo16/venv/bin/python odoo-src/odoo-16.0/odoo-bin -c .odoo16/odoo.conf`.
- Odoo.sh marks the dev build `error` on ANY WARNING before tests run. Filtering or disabling
  tests does not help; reproduce the install locally and count WARNING lines.
- Known WARNING sources: `FutureWarning` from `google.api_core` (pinned in requirements, PR #812),
  `Missing license key in manifest` for the 3mit third-party submodule modules (tracked
  as tech debt, EP-532). While EP-532 is open those 4 are not caused by your change.
- `--http-interface` warning is v19-only (not present in the v16 source); omit if unsure.
- Port 8069 is usually busy with a v16 sync-demo instance: use `--http-port=8213`.

## Odoo 19 (cashea-odoo-v19)
- `--without-demo` is boolean in 19 (`--without-demo=True`); `=all` is invalid.
- `auth_oidc` needs `python-jose` (in the repo `requirements.txt`). Missing in venv = install fails; ask before installing.
- `l10n_ve_cashea_sync_guard` is not installable (no manifest).
- Pre-existing failures seen on main (2026-09): `TestPartnerConstraints` (`test_ve_requires_person_type_and_vat`,
  `test_ve_vat_format`), and in the fiscal report tests `test_purchases_summary_has_no_sales_lines`,
  `test_summary_reports_third_party_vat_on_its_own_line`, `SALES_COLUMNS`. Confirm against a clean main worktree.
- Scripts against a DB: `odoo-bin shell -c ... -d <db> --shell-interface=python < script.py`.
- Mass installs: arm64 `lxml==4.8.0` cannot parse emoji; use an isolated venv in the scratchpad
  (`python3.10 -m venv`, `pip install -r ~/dev/cashea/.odoo19/requirements-macos.txt`, then `lxml==5.2.1` + `lxml-html-clean`,
  re-pin 5.2.1). Install with `--no-deps` or pin `cryptography==3.4.8` to avoid breaking pyOpenSSL.

## Clean baseline of main
```bash
git -C ~/dev/cashea/<repo> fetch origin
git -C ~/dev/cashea/<repo> worktree add --detach ~/dev/cashea/worktree/<repo>/epNNN-main origin/main
createdb -U odoo epNNN_main
# same install/test commands, --addons-path with the worktree as last entry, --log-file=<scratchpad>/epNNN_main.log
```

## Cloning a DB
`createdb -U odoo -T <src> epNNN_test` fails if <src> has open connections, and gives an empty
filestore. Then: `cp -R <data_dir>/filestore/<src> <data_dir>/filestore/epNNN_test`.
(`data_dir` is in the conf; verified layout: `<data_dir>/filestore/<db>`, e.g. `.odoo19/filestore/filestore/<db>`.)

## Quick log reading
```bash
grep -E "odoo.tests.result" LOG            # 0 failed, 0 error(s) of N tests
grep -c " WARNING " LOG                    # must be 0
grep " WARNING " LOG | sed 's/^[0-9: .,-]* [0-9]* //' | sort | uniq -c | sort -rn
```

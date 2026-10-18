# Odoo 19 — what is specific to this version

Read this when the instance's `ODOO_VERSION` is 19. Facts marked *(verified)* were
checked against the Odoo 19.0 source; the rest should be re-checked before leaning on them.

## RPC endpoints

- Odoo 19 ships the **JSON-2 API**: `POST /json/2/<model>/<method>`, `Authorization: Bearer <API key>`,
  arguments by name in the JSON body, `ids` for the recordset, optional `X-Odoo-Database` header
  (`addons/rpc/controllers/json2.py`). *(verified)* `odoo_query.py` uses it by default here. An
  unauthenticated request answers 401, which is how the script detects it.
- `/jsonrpc` and `/xmlrpc` moved out of `base` into the **`rpc` module**
  (`addons/rpc/controllers/jsonrpc.py`, `xmlrpc.py`), `auto_install`, the same module that serves JSON-2.
  *(verified)* They remain as the legacy path; JSON-RPC is slated for removal in Odoo 22. If `/json/2`
  ever answers 404 on a 19 instance, check that `rpc` is installed.
- In tracebacks, an RPC frame will point at `/home/odoo/src/odoo/addons/rpc/controllers/...`,
  not at `odoo/addons/base/controllers/rpc.py` as in 16.
- `@route(type='json')` is a deprecated alias for `type='jsonrpc'` since 19.0. *(verified: `odoo/http.py`)*

## Deployed custom code

- `remote_src.sh user` is the deployed `cashea-odoo-v19` tree: modules sit at the top
  level (`cashea_*`, `l10n_ve_*`, `oca_*`), with no legacy submodule tree.
  *(from the repo layout; confirm with `remote_src.sh --instance v19 user exec ls`)*

## Behaviour worth knowing

- `BaseCursor.commit()` is abstract in 19; the real `Cursor.commit()` still flushes,
  commits and calls `self.clear()`, so the cache is emptied on commit exactly as in 16.
  *(verified: `odoo/sql_db.py`)*
- `ThreadedServer.stop()` still waits up to 1 second for request threads and then calls
  `sql_db.close_all()`. *(verified: `odoo/service/server.py`)*
- `--limit-time-real` still defaults to 120 s. *(verified: `odoo/tools/config.py`)*

## Add here

This file is meant to grow. When an incident on a v19 instance turns up something that
is true of 19 and was not true of 16, add it with how it was verified.

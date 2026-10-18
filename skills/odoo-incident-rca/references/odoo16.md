# Odoo 16 — what is specific to this version

Read this when the instance's `ODOO_VERSION` is 16. Facts marked *(verified)* were
checked against the Odoo 16.0 source; the rest come from past incidents and should
be re-checked before leaning on them.

## RPC endpoints

- `/jsonrpc` and `/xmlrpc/2/*` are served by `odoo/addons/base/controllers/rpc.py`
  (`@route('/jsonrpc', type='json', ...)`). *(verified)* `odoo_query.py` works as is.
- There is **no JSON-2** in 16 (`/json/2` appears nowhere in the 16.0 source *(verified)*), so
  `odoo_query.py` falls back to JSON-RPC here and needs `<NAME>_USER` in addition to the key.
- A web-client call goes through `/web/dataset/call_kw/<model>/<method>`.

## Deployed custom code

- `remote_src.sh user` reaches the whole deployed repo, **submodules included**.
  The legacy addons from the original Odoo 16 build sit inside it, e.g.
  `remote_src.sh user cat 3mit/migracion_odoo_16/<module>/models/<file>.py`.
  *(layout from past incidents; confirm with `remote_src.sh user exec ls`)*
- Odoo.sh database names look like `<code>-<branch>-<build>` and change with every build.

## Behaviour worth knowing

- `Cursor.commit()` flushes, commits and then calls `self.clear()`, so the ORM cache is
  **emptied** on every commit — a long loop that commits per record does not grow the
  cache. *(verified: `odoo/sql_db.py`)*
- `ThreadedServer.stop()` waits up to 1 second for request threads, then
  `sql_db.close_all()`. *(verified: `odoo/service/server.py`)*
- `--limit-time-real` defaults to 120 s, and there is a separate
  `--limit-time-real-cron` (defaults to the former). *(verified: `odoo/tools/config.py`)*
  On Odoo.sh the platform adds its own wall-clock budget for crons on top of that.
- `@route(type='json')` is the normal spelling for JSON routes in 16.

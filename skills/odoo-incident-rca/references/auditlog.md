# Audit log: who did what, click by click (Odoo 19)

The v19 instance runs `cashea_auditlog_full` (rules in `full` mode on the key models) plus
`cashea_auditlog_archive`. Together they record every write, create and delete with old and new
values, the user, the session, the HTTP request, auth events and request logs. When the
question is "when did this change, who did it, what did they click", this is the source of
truth — not inference from record dates.

Typical use: a lock date, a journal, a partner, a config parameter or a rule changed and
something downstream behaved differently. `write_date` on the record only says *when*; the audit
log says *who*, *what value before/after* and *from which request*.

## Tables (all queryable through `odoo_query.py --instance v19`)

| Model | What it holds |
|---|---|
| `auditlog.log` | one row per operation: `model_model`, `res_id`, `method`, `user_id`, `create_date`, `http_request_id`, `http_session_id` |
| `auditlog.log.line` | one row per field changed: `field_name`, `old_value`, `new_value` (and `_text` variants), `log_id` |
| `auditlog.http.request` | the HTTP request behind a log (URL, method, user) |
| `auditlog.http.session` | the session (sid is hashed) |
| `auditlog.request.log` | request-level trail, to follow what a user opened and clicked |
| `auditlog.auth.event` | logins, failures, logouts |
| `auditlog.rule` | which models are audited, and in which mode |

```bash
# who changed a field, and when
scripts/odoo_query.py --instance v19 search auditlog.log.line \
  "[['field_name','in',['fiscalyear_lock_date','sale_lock_date']]]" \
  --fields create_date,field_name,old_value,new_value,log_id --order "create_date desc"
# everything one user did in a window
scripts/odoo_query.py --instance v19 search auditlog.log \
  "[['user_id','=',<id>],['create_date','>=','<ts>']]" --fields create_date,model_model,res_id,method
```

Check first that the model is covered: `search auditlog.rule "[['model_id.model','=','<model>']]"`.
A confirmed rule with zero logs for a model that surely changed means the history is not in the
database any more — see the next section, it is not "nothing happened".

## The database holds only the current week

`cashea_auditlog_archive` moves each finished week (Monday–Sunday, UTC) to the bucket and purges
it from PostgreSQL, Monday 03:00–09:59 UTC. So on a given day the database has between 0 and 7
days. Anything older is in `<bucket>/auditlog/YYYY/MM/<monday>_auditlog_<table>.csv.gz`
(`YYYY/MM` is the month of that Monday), with a `<monday>_manifest.json`.

Find which week and file hold a date, and whether it was purged:

```bash
scripts/odoo_query.py --instance v19 search auditlog.archive \
  "[['week_start','>=','<monday>']]" --fields week_start,table_name,state,key,purged_on
```

Line files are standalone: besides the line's own columns they carry `log_model_model`,
`log_res_id`, `log_method`, `log_user_id` and `log_create_date`, so a lock-date change is a
filter on `field_name` with no join.

Reading an archived week:

- **BigQuery external table** over `gs://<bucket>/auditlog/*/*/*_auditlog_log_line.csv.gz` is the
  intended way (no download). Look for it with the BigQuery tools (`list_dataset_ids`, and the
  `cashea-data-dictionary` skill) before anything else.
- **Odoo UI** *Audit > Audit log archive* (system administrators) → **Download** opens a
  five-minute signed URL. Each click is itself a request in the audit trail. A busy week is tens
  of millions of lines: filter, never open it in a spreadsheet (cells starting with `= + - @`
  execute as formulas).
- Downloading is a file download: state filename, source and size and get a yes first.

## Time zones

Everything is UTC (`create_date` in the database and the CSV). Caracas is UTC-4; a change "at
night on the 12th" in Caracas is the 13th in the log.

## Using it in the RCA

- Replace "inferred from record dates" with the log line: user, timestamp, old → new value.
- A change made from the UI has an `http_request_id`; the request log around it shows what the
  user opened before and after (the click path), which answers "was it deliberate, or a side
  effect of another screen".
- Cite the `auditlog.log` id and the archive file in the RCA so the claim can be re-checked.
- If the rule does not cover the model, or the week was never archived, say so under "Qué no
  pudimos determinar" instead of guessing.

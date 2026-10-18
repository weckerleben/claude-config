---
name: odoo-incident-rca
description: Diagnose a production incident on a Cashea Odoo.sh instance (Odoo 16 or Odoo 19) end to end — pull the day's logs off the server, anchor the reported traceback in them, verify every claim against the real source trees, and deliver a root-cause analysis plus the fix. Use this whenever someone reports an Odoo error, RPC_ERROR popup, failed cron, stuck job, timeout, worker kill or "se cayó / no funciona" on production or staging, and whenever a ticket arrives with an Odoo traceback pasted in. Also use it when asked to "mirar los logs", "ver qué pasó ayer", "por qué falló X" or to investigate an Odoo.sh alert — even if the person has not mentioned logs at all. Do NOT use it for pure database performance work with no user-reported error; use odoo-postgres-tuning for that.
---

# Odoo.sh incident RCA

An Odoo traceback names the line where execution *stopped*, which is usually not where the problem *started*. The whole point of this workflow is to resist the pull of that first stack frame: gather the surrounding evidence, check what the code actually does, and try to knock down your own hypothesis before shipping it.

Producing a confident RCA that turns out to be wrong is worse than producing none — someone will spend a sprint fixing the wrong thing.

## One skill, several instances

This skill does not know which Odoo it is looking at. Each instance (Odoo 16, Odoo 19, a staging build…) is a **profile** in `config.env`, and every script takes `--instance <name>`. Nothing in the skill — scripts, paths, examples — is tied to one version or one repo.

```bash
scripts/instance.sh            # which instance would I use, and what is missing for it
scripts/instance.sh --list     # every configured instance
```

Run `instance.sh` first, every time. Reading logs or querying data from the wrong instance produces a convincing RCA of the wrong system.

The instance is chosen in this order: `--instance`, then `$RCA_INSTANCE`, then autodetection (the `origin` remote of the directory you are in matches the profile's `REPO_MATCH`), then `DEFAULT_INSTANCE`, then the only instance if there is just one. Working inside the repo of an instance normally selects it by itself; pass `--instance` when the incident is about a different one than the repo you are in — for example a v19 symptom whose cause sits on the v16 side of a sync.

Facts that depend on the Odoo version live in `references/odoo16.md` and `references/odoo19.md`, not in this file. Read the one that matches the instance's `ODOO_VERSION` before Step 5.

## What you deliver

Four artifacts, in this order:

1. **`<INCIDENTS_DIR>/<date>-<slug>.md`** — the full analysis, committed in the repo of the instance. `instance.sh` prints `INCIDENTS_DIR` (default `<repo>/docs/incidents`). Structure is fixed; see "RCA structure" below.
2. **A row in `<INCIDENTS_DIR>/INDEX.md`** — so the next incident (human or this skill) finds this one before re-deriving it. If the file does not exist yet, create it from `templates/INDEX.md`.
3. **A short reply for the ticket** — plain language, no file paths, answers only: what happened, was anything lost, what to do meanwhile. If there is a Jira ticket, that reply belongs there, with a link to artifact 1 — that link is what makes the analysis reachable from where functional analysts already look, without duplicating it into Notion.
4. **A branch with the fix**, when a code fix is warranted and safe.

Deliver 1, 2 and 3 even when the fix needs a decision from someone else. Say plainly what you left undone.

`incidents/` lives in the repo, is plain text, and is readable by anyone with repo access — including functional analysts who don't otherwise touch code. Never paste a live credential, token, or password into one, even when the incident is *about* an exposed one: say that it was rotated, don't reproduce the value.

## Setup (once per machine)

Local values differ per person, so they live in `config.env`, not in this file or in the scripts. The file is looked up in `$RCA_CONFIG`, then `~/.config/odoo-incident-rca/config.env`, then next to the skill. Keep it outside `~/.claude` — that directory is a git repo and the file can hold API keys.

```bash
mkdir -p ~/.config/odoo-incident-rca
cp config.env.example ~/.config/odoo-incident-rca/config.env
```

Fill in one block per instance. Realistically that is `SSH_TARGET` (the Odoo.sh build number in it changes over time, so update it when it does) and, if you want live data queries, `URL`, `DB`, `USER` and `API_KEY`.

Everything about *where the code and logs live* is a fixed path on the server, identical across every Odoo.sh instance — not a per-person setting, so it is not a variable at all. Odoo community, enterprise, and the deployed custom code (including its submodules) are **not** checked out locally — `scripts/remote_src.sh` reads them straight off the server. This is not just less setup, it is more trustworthy than a local clone: it is exactly the code that ran, with no "is my checkout in sync with what's deployed" question to ask. The logs work the same way — `scripts/fetch_logs.sh` has `/home/odoo/logs` built in.

| Thing | Where it comes from |
|---|---|
| Production shell | `<NAME>_SSH_TARGET` in config.env (`<build>@<project>.odoo.com`) |
| Local repo (git history, deploys, fixes) | `<NAME>_REPO_DIR`, or the current directory when it is that instance's repo |
| Logs on server | fixed: `/home/odoo/logs` |
| Odoo community source | fixed: `remote_src.sh odoo` → `/home/odoo/src/odoo` |
| Odoo enterprise source | fixed: `remote_src.sh enterprise` → `/home/odoo/src/enterprise` |
| Deployed custom code | fixed: `remote_src.sh user` → `/home/odoo/src/user` (submodules included) |

```bash
scripts/remote_src.sh user lines my_module/models/res_users.py 47 64
scripts/remote_src.sh odoo grep "_check_credentials" odoo/addons/base/models/res_users.py
scripts/remote_src.sh --instance v16 user cat my_module/models/account_move.py
```

Note Odoo's own layout quirk, the same in 16 and 19: framework-internal modules (`base`) live under a *nested* `odoo/addons/`, while ordinary business modules (`account`, `sale`, `mail`) sit at the top-level `addons/` — both inside the `odoo` root.

**Server logs are UTC.** Ticket timestamps usually are not. Get this wrong and you will read the wrong hour of a 47 MB file and conclude nothing happened.

## Step 1 — Pin down the report before touching the server

Get, or ask for: the full traceback, the wall-clock time and timezone, **which instance it happened on**, what the person was doing, how many records, and whether it is reproducible. A traceback without a timestamp costs an extra round trip you can avoid by asking now.

## Step 2 — Check the incident index first

Before spending time on logs or source, check whether this exact shape has already been diagnosed. `<INCIDENTS_DIR>/INDEX.md` is one row per past incident: date, instance, ticket(s), a one-line symptom, keywords, the one-line root cause, status, and a link to the full analysis.

```bash
grep -i "<exception class, model/file name, or a couple of words from the report>" <INCIDENTS_DIR>/INDEX.md
```

Code is shared between the instances' history more often than it looks, so when the incident is on one instance also grep the other instance's `INDEX.md` if its repo is available locally.

If a row matches, read the linked file before doing anything else — three outcomes, and they lead to different next steps:

- **Fixed and shipped, but this looks like the same thing again.** That recurrence is itself the finding. Confirm the fix commit is actually in the branch the traceback ran against (Step 5 does this anyway); a "fixed" bug reappearing usually means the fix didn't survive a later change to the same code, not that the fix was wrong. Say so plainly rather than re-deriving the original cause from scratch.
- **Open, fix pending.** Don't restart the investigation. Read what is already known, add whatever new evidence this occurrence brings, and move the existing entry forward instead of writing a parallel one.
- **Nothing matches.** Proceed as normal, and add the new entry when you reach Step 9.

## Step 3 — Pull the logs

```bash
scripts/fetch_logs.sh [--instance <name>] [ssh-target] <dest-dir> [YYYY-MM-DD ...]
```

`ssh-target` can be omitted: it comes from the instance profile. The script tells the two apart by the `@` a real ssh target always has and a destination path never does. Pass it explicitly to reach a different build or branch than the configured one.

Reads the remote directory, copies each file separately and decompresses `.gz` while keeping the originals. Two Odoo.sh quirks are baked in, both of which cost real time when rediscovered: the **SFTP subsystem is unavailable**, so `scp` needs `-O` to fall back to the legacy protocol, and **brace expansion does not happen remotely**, so one `scp` per file.

Grab the adjacent days too. Incidents are often the visible end of something that started earlier, and a quiet day is the baseline that tells you what "normal" looks like.

## Step 4 — Anchor the traceback in the log

Find the exact line, then read a generous window around it — a few hundred lines before and after. Note the PID: everything that PID did in the preceding minutes is the story.

```bash
grep -n "ERROR\|CRITICAL" odoo.log.<date> | tail -50
```

Odoo's perf line at the end of each werkzeug request is `<queries> <sql_time> <other_time>`. When SQL time is a small fraction of the total, the problem is not the database — it is HTTP calls, report rendering, or Python. This one number redirects entire investigations; read it before theorising.

## Step 5 — Read the exact code from the traceback

A traceback path tells you both the root and the path within it: `/home/odoo/src/user/...` is `user`, `/home/odoo/src/odoo/...` is `odoo`, `/home/odoo/src/enterprise/...` is `enterprise` — strip that prefix and hand the rest to `remote_src.sh`:

```bash
scripts/remote_src.sh user lines my_module/models/res_users.py 5834 5850
```

Reading it this way is inherently reading the code that ran, with one exception: if a deploy landed between the incident and now, the server already shows the *new* code — Step 7 (the deploy timeline) is where that gets checked. If a deploy falls in the gap, say so explicitly and treat what the server shows now as "what it changed to," not necessarily "what caused the error."

If SSH access is down (it happens — this workflow once lost it mid-investigation right after a deploy) or you are reading from a local clone anyway for git history, confirm its line numbers actually match before trusting them —

```bash
sed -n '<line>,<line+15>p' <local-path-of-traceback-file>
```

— since a local checkout can silently sit on the wrong branch or behind the deployed revision in a way the live server never can.

## Step 6 — Ask the live data

Reading source tells you what the code does. It does not tell you what it is operating on, and a surprising share of production errors are a mismatch between the two: a field that is empty everywhere, a record in a state the code never anticipated, a relation that returns dicts where the caller expects recordsets.

```bash
scripts/odoo_query.py [--instance <name>] fields account.move --grep residual
scripts/odoo_query.py count account.move "[['state','=','draft']]"
scripts/odoo_query.py search res.partner "[['id','=',123]]" --fields name,vat
scripts/odoo_query.py groupby account.move.line "[]" balance journal_id
```

Read-only by construction: six read methods are allowed and everything else is refused before a request is sent. That matters because Odoo's `execute_kw` will invoke *any* public method of a model — `write`, `unlink`, an `action_confirm` — so a blocklist would leak and an allowlist does not.

The script prints `[instancia: <name>]` and `[api: json2|jsonrpc]` on stderr for every query. Check the first matches the incident.

**Which API it speaks.** JSON-2 (`/json/2/<model>/<method>`, Odoo 19+) whenever the instance has it, JSON-RPC (`/jsonrpc`) only as a fallback on versions that lack it — JSON-RPC is slated for removal in Odoo 22. In `auto` mode (the default) it probes `/json/2` with an unauthenticated request: 401 means the route exists, 404 means it does not. Set `<NAME>_RPC_API=json2` or `jsonrpc` in `config.env` to force one. The read-only allowlist is applied before the API is chosen, so it holds for both.

`<NAME>_URL`, `<NAME>_API_KEY` and, recommended, `<NAME>_DB` come from `config.env` or the environment, never from arguments, which would leave them in shell history and in the process list. `<NAME>_USER` is needed only on the JSON-RPC fallback; JSON-2 identifies the user by the key. Use an API key rather than a password so it can be revoked on its own.

Be clear-eyed about the boundary: the allowlist is a guardrail in this script, not a permission on the server. The API key still carries its owner's full rights. When a real boundary is needed, the answer is a dedicated Odoo user with read-only access rights, not a more careful script.

When an `AttributeError` or a `KeyError` names a field, checking whether the model actually has that field — and what type it is — usually settles in one call what would otherwise be a long argument with the code.

### When the data comes from BigQuery

A lot of Cashea's reporting does not read Odoo tables at all: `pg.connection` fetches from BigQuery via `conn.bq_dictfetchall()`, `bq_fetchall()` or `query_result()`. When the failing code path goes through one of those, the source of truth is the warehouse, and the BigQuery MCP tools reach it directly — use `execute_sql_readonly`, and load the `cashea-data-dictionary` skill for the table inventory rather than guessing at names.

Three traps live in this seam, and this workflow was extended after all three bit at once:

**The table name is usually not in the code.** It typically comes from an `ir.config_parameter` with a hardcoded default — the literal you see is only the fallback. Resolve the real value against the live instance before trusting it:

```bash
scripts/odoo_query.py search ir.config_parameter "[['key','like','bq_']]" --fields key,value
```

**`bq_dictfetchall` returns dicts, not recordsets.** Attribute access on the result raises `AttributeError: 'dict' object has no attribute ...`. Anything downstream of it must use `o['key']`.

**Aliases in the SELECT rename the columns.** The dict keys are the *aliases*, not the warehouse column names, so a column that plainly exists in BigQuery may be absent from the result — and an alias can even shadow a real column of the same name with a different meaning. Read the `SELECT` list in the Odoo source and the table schema in BigQuery side by side; they answer different halves of the question.

**Caveat on the project.** The Odoo connector authenticates with its own service account, whose project comes from the credentials JSON stored as an attachment on `pg.connection`. There is no guarantee it is the same project your BigQuery tools are pointed at. If a schema does not match what the code expects, check that before concluding the code is wrong.

Once you can query the warehouse, use it to size the fix rather than reason about it. Counting how many rows actually satisfy each arm of a condition turns "this filter looks equivalent" into a number.

## Step 7 — Build the timeline around the failure

```bash
scripts/timeline.sh <log-file> <HH:MM:SS> [window-seconds]
```

Surfaces restarts, deploys, cron activity, worker kills and genuine memory events in a window around the failure. What to look for:

**Deploy or restart underneath a live request.** Many processes logging `Initiating shutdown` in the same second, then new processes with *low* PIDs loading all modules from scratch, is a **deploy** — a fresh container. The same message on one PID with `Initiating server reload` is a SIGHUP reload and much less disruptive. This matters because `ThreadedServer.stop()` waits **one second** for in-flight request threads and then closes the entire connection pool (`odoo/service/server.py` → `sql_db.close_all()`; `scripts/remote_src.sh odoo grep close_all odoo/service/server.py` finds it directly), ignoring whether connections are in use. Any long request dies, and the error surfaces at whatever ORM statement it happened to reach — which is why the traceback often accuses an innocent line. Verified identical in the Odoo 16.0 and 19.0 sources.

**Confirm it against the repository, don't infer it from the log alone.** Odoo.sh deploys on push to the production branch, so a merge timestamp is the trigger for a restart. Correlating the two turns "there was a restart" into "this specific PR caused it":

```bash
scripts/deploys.sh [--instance <name>] [repo-dir] <YYYY-MM-DD> [fin] --log <log-file>
```

`repo-dir` defaults to the instance's repo (`<NAME>_REPO_DIR`, or the current directory when it is that repo) and can be omitted; pass it explicitly to correlate a different repo's history. It pulls merge times from GitHub via `gh` — exact, already UTC, and independent of whether the local checkout is current, which it usually is not. It falls back to `git log`, where you must normalise: commit dates carry the committer's offset (`+0200`, `-0300`), and comparing those against UTC log lines silently shifts everything by hours. Use committer date, not author date; on a merge the author date can be weeks old.

A delta of seconds between merge and restart is conclusive. In the incident this workflow came from, four merges matched four fleet restarts within 14 to 60 seconds each, and two of them landed on top of the user's failing request.

When that is the finding, say plainly that the commit contents are irrelevant — nothing in that PR is buggy. What broke the request is the restart, and the real defect is a request long enough to be caught by one.

**Worker kills that are not what they say.** Odoo.sh logs `killed by signal 9 (most likely hit a memory limit, please check your custom modules memory usage.)` for *any* SIGKILL, including a worker that simply failed to exit in time or blew a wall-clock budget. That string is not in the Odoo source at all — it comes from Odoo.sh's own supervisor. Confirm a real OOM by finding Odoo's own messages:

```bash
for p in "Server memory limit" "virtual memory limit" "MemoryError" "timeout after"; do
  echo "$p: $(grep -c "$p" odoo.log*)"
done
```

All zero means it was not Odoo's limiter. Note also that Odoo measures VMS, not RSS, and only between units of work — a different number from the one the container killer acts on.

## Step 8 — Analyse against the source, then try to break your own analysis

Read the actual code for every frame on the path, not just the top one. Then decompose the incident into independent angles — the failing code path, the data volume it touches, concurrency and locking, the surrounding infrastructure — and work each one.

Then run an adversarial pass. Every finding that carries weight goes to a fresh reader whose job is to **refute** it: check the claim is true of the code as written rather than the code you imagined, check the causal mechanism actually follows, and check nothing elsewhere contradicts it (a guard, an override, a caller that never reaches this path, a different behaviour in this Odoo version than assumed).

This is not ceremony. In the incident this workflow was built from, 26 of 64 findings were refuted, including the lead hypothesis. Skipping it is how a wrong RCA ships.

Use `Workflow` when it is available — fan out the angles, verify each finding in parallel, synthesise what survives. Otherwise use subagents, or at minimum re-read each conclusion against the source with deliberate skepticism before writing it down.

## Step 9 — Write the deliverables

### The RCA file and the index

Save the full analysis to `<INCIDENTS_DIR>/<YYYY-MM-DD>-<slug>.md` (`<slug>` short and kebab-case, e.g. `jumpcloud-api-key-rpc`). Structure is fixed:

```
# Análisis de causa raíz — <síntoma> (<fecha>)
Instancia: <nombre> (Odoo <versión>)
## 1. Causa raíz directa          — one paragraph, no hedging, with the file:line chain
## 2. Cadena causal completa      — numbered, user action to error message, each step cited
## 3. Factores amplificadores     — ranked by real weight, with the evidence for each
## 4. Hallazgos independientes    — real bugs found on the way that are not the cause
## 5. Remediación                 — (a) mitigación inmediata (b) arreglos de código (c) trabajo de fondo
## 6. Qué no pudimos determinar   — what needs runtime data rather than source reading
```

Write in Spanish. Every technical claim carries a `file:line`. Never invent a line number — name the function instead if you do not have one.

Include a short subsection listing hypotheses that were **refuted**. It stops the next person re-running the same dead end, and it is often the most useful part of the document.

Section 6 is not optional. Source reading cannot tell you table sizes, index usage, lock waits or real memory profiles. State the exact query or measurement needed and what decision it unblocks.

Then append one row to `<INCIDENTS_DIR>/INDEX.md` — its header explains the columns and shows the format. This row is the thing Step 2 greps for the next time, so keep the symptom and keywords in the words someone would actually search, not just the internal function name.

### The ticket reply

Plain language, no file paths, no internals. What happened, whether anything was lost or half-applied, what to do in the meantime. If work was left in a partial state — a loop that commits per record and then aborts will do this — say exactly which records and what to check.

### The fix branch

The fix goes in the repo of the instance the incident happened on (`REPO_DIR` from `instance.sh`). Check before touching its working tree: `git status`. Whatever is there — someone's half-finished work, a stray untracked directory — is not yours to build on top of or lose. If there is uncommitted work unrelated to this fix, stash it (`git stash push -u -m "wip before <slug> fix"`) rather than risk it; note that you did, and leave popping it back to whoever it belongs to. This is a low-probability situation but a costly one to get wrong, so check every time rather than assuming the tree is clean.

Branch off the remote production branch directly, not a local branch that might itself be stale or dirty:

```bash
git fetch origin
BRANCH=$(git symbolic-ref --short refs/remotes/origin/HEAD | sed 's|^origin/||')
git checkout -b fix/<slug> "origin/$BRANCH"
```

Same detection `deploys.sh` already uses (Step 7) — don't hardcode `master` or `main`.

Apply the fix, commit. In English, following the repo's own commit convention (Odoo repos use `[FIX] module: …`). Stage specific paths, not `-A`: if something unrelated rode along on the branch switch, an explicit `git add` is what keeps it out of the commit. Only do any of this when the change is clearly correct and in scope — if it needs a product or accounting decision, write the recommendation into the RCA instead and say why you stopped.

## Known false leads

Each of these looked like the answer at some point and was not. Check them off quickly rather than exploring them.

| Looks like | Actually |
|---|---|
| `killed by signal 9 (most likely hit a memory limit)` | Generic label on any SIGKILL. Confirm with Odoo's own memory messages. |
| The traceback's top frame | Frequently the first ORM statement after the connection died elsewhere. |
| `InterfaceError: connection already closed` from a `rollback()` in an `except` | Masks the real error. The handler failed while handling. Look before it. |
| ORM cache growing across a long loop | `cr.commit()` **clears** the cache (`sql_db.py` → `Cursor.commit` calls `self.clear()`) in both 16 and 19. It bounds memory, it does not grow it. |
| A slow single-row `DELETE ... WHERE id = N` | Almost always unindexed FK columns in *referencing* tables. Use odoo-postgres-tuning. |
| A cron that "never finishes" | Odoo.sh imposes a wall-clock budget and deactivates repeat offenders. Check for the deactivation notice before assuming a hang. |
| `xlsxwriter` `{'in_memory': True}` | Only avoids temp files for the XML/zip. The cell table is always held in RAM; `constant_memory` is the flag that changes that. |

## Reference

- `references/log-formats.md` — the shape of each file in `/home/odoo/logs`, the perf-line fields, the `pg_slow_queries.log` block format and its 30-second capture floor, and the grep patterns for cron lifecycle, deploys and restarts. Read it when a log line is not self-explanatory.
- `references/odoo16.md`, `references/odoo19.md` — what is specific to each version. Read the one that matches the instance.
- `templates/INDEX.md` — header and column format for a new incident index.

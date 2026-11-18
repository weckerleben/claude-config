#!/usr/bin/env python3
"""Asientos que la sync V16 -> V19 dejó en V19 con una fecha distinta a la de V16.

Solo lectura: usa la lista blanca de odoo_query.py (search_read y afines), no escribe nada.
Pensado para ODOO-383 (paso 6): Odoo 19 movía al primer día abierto los asientos que caían
en un período bloqueado, y la sync los espejaba con otra fecha.

    shifted_dates.py [--since 2026-10-01] [--source v16] [--dest v19] [--out archivo.csv]

Qué compara, según cómo la sync identifica cada asiento en V19 (external ID bajo el módulo
`__account_sync_o16__`):
  * documentos (`move_<db>_<id v16>`): la fecha del asiento V16 contra la de V19;
  * agregados (`agg_...`): el día que lleva la referencia ("Aggregated entries AAAA-MM-DD ...")
    contra la fecha de V19;
  * cortes de EP-443 (`orphan_...`): se fechan como el asiento viejo del matching; la
    referencia ("EP443 orphan matching <id>") da el matching en V16 y un corte es sospechoso
    si su fecha no coincide con la de ninguno de los dos asientos del matching;
  * lo demás (extractos agrupados `sagg_`) solo se cuenta: no hay una fecha de origen que se
    pueda leer sin ambigüedad.

Salida: un CSV (stdout, o --out) con una fila por asiento corrido y un resumen por compañía y
por mes en stderr. Compartir el CSV con Contabilidad antes de tocar nada.
"""
import argparse
import csv
import re
import sys
from collections import Counter
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

XMLID_MODULE = "__account_sync_o16__"
PAGE = 5000

CSV_FIELDS = [
    "company", "kind", "v16_id", "v19_id", "v19_name", "move_type", "state",
    "date_v16", "date_v19", "gap_days", "amount", "link_ok",
]

_DOC_KEY = re.compile(r"^move_.+_(\d+)$")
_AGG_DAY = re.compile(r"Aggregated entries (\d{4}-\d{2}-\d{2})")
_ORPHAN_REF = re.compile(r"EP443 orphan matching (?:\d+/)?(\d+)")


def classify_key(name):
    """(tipo, id de V16 o None) a partir del nombre del external ID."""
    m = _DOC_KEY.match(name or "")
    if m:
        return "document", int(m.group(1))
    if (name or "").startswith("agg_"):
        return "aggregate", None
    if (name or "").startswith("sagg_"):
        return "statement", None
    if (name or "").startswith("orphan_"):
        return "orphan", None
    return "other", None


def aggregate_day(ref):
    m = _AGG_DAY.search(ref or "") if isinstance(ref, str) else None
    return m.group(1) if m else None


def orphan_partial_id(ref):
    """Id del matching de V16 que originó un corte de EP-443, leído de su referencia."""
    m = _ORPHAN_REF.search(ref) if isinstance(ref, str) else None
    return int(m.group(1)) if m else None


def date_gap(source, destination):
    """Días de destino menos origen; None si coinciden o falta el origen."""
    if not source or not destination:
        return None
    gap = (date.fromisoformat(destination) - date.fromisoformat(source)).days
    return gap or None


def build_rows(tagged, v19_moves, v16_moves, partial_dates=None):
    """Filas de los asientos corridos y contadores. Sin red: recibe todo ya leído.

    `partial_dates` ({id del matching V16: {fechas de sus dos asientos}}) habilita la
    comparación de los cortes de EP-443: un corte debe llevar la fecha de uno de los dos
    asientos del matching; si no coincide con ninguno, fue corrido.
    """
    rows = []
    stats = Counter()
    for tag in tagged:
        kind, v16_id = classify_key(tag["name"])
        move = v19_moves.get(tag["res_id"])
        if move is None:
            stats["v19_missing"] += 1
            continue
        if kind in ("other", "statement") or (kind == "orphan" and partial_dates is None):
            stats["other"] += 1
            continue
        link_ok = ""
        if kind == "orphan":
            dates = (partial_dates or {}).get(orphan_partial_id(move.get("ref")))
            if not dates:
                stats["v16_missing"] += 1
                continue
            stats["checked"] += 1
            if move["date"] in dates:
                continue
            source_date = min(dates)
            gap = date_gap(source_date, move["date"])
            rows.append(_row(kind, "", move, source_date, gap, link_ok))
            continue
        if kind == "document":
            source = v16_moves.get(v16_id)
            if source is None:
                stats["v16_missing"] += 1
                continue
            source_date = source["date"]
            link_ok = "yes" if source.get("sync_v19_move_id") == move["id"] else "no"
            if link_ok == "no":
                stats["link_mismatch"] += 1
        else:
            source_date = aggregate_day(move.get("ref"))
        stats["checked"] += 1
        gap = date_gap(source_date, move["date"])
        if gap is None:
            continue
        rows.append(_row(kind, v16_id, move, source_date, gap, link_ok))
    return rows, stats


def _row(kind, v16_id, move, source_date, gap, link_ok):
    return {
        "company": (move.get("company_id") or ["", ""])[1],
        "kind": kind,
        "v16_id": v16_id if v16_id is not None else "",
        "v19_id": move["id"],
        "v19_name": move.get("name") or "",
        "move_type": move.get("move_type") or "",
        "state": move.get("state") or "",
        "date_v16": source_date,
        "date_v19": move["date"],
        "gap_days": gap,
        "amount": move.get("amount_total_signed"),
        "link_ok": link_ok,
    }


def write_csv(rows, out):
    writer = csv.DictWriter(out, fieldnames=CSV_FIELDS, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)


# ----------------------------------------------------------------------
# Lectura (solo search_read, vía la lista blanca de odoo_query)
# ----------------------------------------------------------------------
def read_all(oq, target, model, domain, fields, label):
    """search_read paginado por id; no depende del orden ni de offsets que se muevan."""
    out, last = [], 0
    while True:
        page = oq.call(target, model, "search_read",
                       [domain + [("id", ">", last)]],
                       {"fields": fields, "limit": PAGE, "order": "id"})
        out.extend(page)
        print("  %s: %d" % (label, len(out)), file=sys.stderr, end="\r")
        if len(page) < PAGE:
            break
        last = page[-1]["id"]
    print("", file=sys.stderr)
    return out


def read_by_ids(oq, target, model, ids, fields, label):
    ids = sorted(set(ids))
    found = {}
    for i in range(0, len(ids), PAGE):
        chunk = ids[i:i + PAGE]
        for rec in oq.call(target, model, "search_read", [[("id", "in", chunk)]], {"fields": fields}):
            found[rec["id"]] = rec
        print("  %s: %d/%d" % (label, min(i + PAGE, len(ids)), len(ids)), file=sys.stderr, end="\r")
    print("", file=sys.stderr)
    return found


def read_partial_dates(oq, target, partial_ids):
    """{id del matching: {fechas de los dos asientos}} leído en V16 (matching -> líneas -> fecha)."""
    partials = read_by_ids(oq, target, "account.partial.reconcile", partial_ids,
                           ["debit_move_id", "credit_move_id"], "matchings de %s" % target.instance)
    line_ids = {l[0] for p in partials.values() for l in (p["debit_move_id"], p["credit_move_id"]) if l}
    lines = read_by_ids(oq, target, "account.move.line", line_ids, ["date"],
                        "líneas de %s" % target.instance)
    out = {}
    for pid, p in partials.items():
        dates = {lines[l[0]]["date"] for l in (p["debit_move_id"], p["credit_move_id"])
                 if l and l[0] in lines and lines[l[0]].get("date")}
        if dates:
            out[pid] = dates
    return out


def summarize(rows, stats, out=sys.stderr):
    print("\nRevisados: %d | corridos: %d | sin mirar (extractos agrupados y otros): %d" % (
        stats["checked"], len(rows), stats["other"]), file=out)
    for key, label in (("link_mismatch", "documentos con el vínculo V16->V19 cruzado"),
                       ("v16_missing", "documentos sin su asiento en V16"),
                       ("v19_missing", "externals IDs sin asiento en V19")):
        if stats[key]:
            print("  ATENCIÓN: %d %s" % (stats[key], label), file=out)
    by_company = Counter(r["company"] for r in rows)
    by_month = Counter(r["date_v16"][:7] for r in rows)
    print("\nPor compañía:", file=out)
    for name, n in by_company.most_common():
        print("  %5d  %s" % (n, name), file=out)
    print("Por mes de la fecha original (V16):", file=out)
    for month, n in sorted(by_month.items()):
        print("  %5d  %s" % (n, month), file=out)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--since", default="2026-10-01",
                        help="solo lo sincronizado desde esta fecha (create_date del external ID)")
    parser.add_argument("--source", default="v16", help="instancia de origen (default v16)")
    parser.add_argument("--dest", default="v19", help="instancia de destino (default v19)")
    parser.add_argument("--only", help="tipos a revisar, separados por coma: document, aggregate, orphan "
                                       "(default todos)")
    parser.add_argument("--out", help="archivo CSV de salida (default stdout)")
    args = parser.parse_args(argv)

    import odoo_query as oq
    cfg = oq._read_config_file()
    source, dest = oq.Target(args.source, cfg), oq.Target(args.dest, cfg)
    print("[origen: %s | destino: %s | desde %s]" % (args.source, args.dest, args.since), file=sys.stderr)

    tagged = read_all(oq, dest, "ir.model.data",
                      [("module", "=", XMLID_MODULE), ("model", "=", "account.move"),
                       ("create_date", ">=", args.since)],
                      ["name", "res_id"], "external IDs de %s" % args.dest)
    if args.only:
        wanted = {k.strip() for k in args.only.split(",")}
        tagged = [t for t in tagged if classify_key(t["name"])[0] in wanted]
    v19_moves = read_by_ids(
        oq, dest, "account.move", [t["res_id"] for t in tagged],
        ["name", "date", "ref", "state", "move_type", "company_id", "amount_total_signed"],
        "asientos de %s" % args.dest)
    v16_ids = [classify_key(t["name"])[1] for t in tagged if classify_key(t["name"])[0] == "document"]
    v16_moves = read_by_ids(oq, source, "account.move", v16_ids,
                            ["date", "sync_v19_move_id"], "asientos de %s" % args.source)

    partial_ids = {orphan_partial_id(v19_moves[t["res_id"]].get("ref"))
                   for t in tagged
                   if classify_key(t["name"])[0] == "orphan" and t["res_id"] in v19_moves}
    partial_ids.discard(None)
    partial_dates = read_partial_dates(oq, source, partial_ids)

    rows, stats = build_rows(tagged, v19_moves, v16_moves, partial_dates)
    rows.sort(key=lambda r: (r["company"], r["date_v16"], r["v19_id"]))
    if args.out:
        with open(args.out, "w", newline="", encoding="utf-8") as handle:
            write_csv(rows, handle)
    else:
        write_csv(rows, sys.stdout)
    summarize(rows, stats)


if __name__ == "__main__":
    main()

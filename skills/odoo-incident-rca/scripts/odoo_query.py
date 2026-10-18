#!/usr/bin/env python3
"""Consultar un Odoo vivo por API externa. SOLO LECTURA.

Sirve para contrastar una hipótesis contra los datos reales en vez de deducirlos
del código: qué campos tiene realmente un modelo, de qué tipo son, cuántos
registros hay en cierto estado, si un campo está poblado o vacío.

## Instancia

El skill no sabe de qué Odoo habla: cada instancia es un perfil en config.env
(ver config.env.example). Se elige, en este orden:

    1. --instance <nombre>
    2. $RCA_INSTANCE
    3. autodetección: el remote `origin` del cwd coincide con <NOMBRE>_REPO_MATCH
    4. DEFAULT_INSTANCE de config.env
    5. la única instancia de INSTANCES, si hay una sola

## Qué API usa

JSON-2 (`POST /json/2/<modelo>/<método>`, Odoo 19+) siempre que la instancia lo
tenga; JSON-RPC (`/jsonrpc`) solo como respaldo en versiones que no lo traen.
JSON-RPC queda deprecado en Odoo 22, así que JSON-2 es el camino por defecto.

`<NOMBRE>_RPC_API` lo controla: `auto` (por defecto) prueba JSON-2 con un request
sin autenticar — 401 significa que existe, 404 que no — y cae a JSON-RPC si no está;
`json2` o `jsonrpc` fuerzan una de las dos sin probar. Cada corrida imprime
`[api: ...]` en stderr.

## Credenciales

Por instancia, con el nombre en mayúsculas como prefijo (p. ej. V19_URL):

    <NOMBRE>_URL, <NOMBRE>_API_KEY       siempre
    <NOMBRE>_DB                          recomendada (JSON-2 la manda en X-Odoo-Database)
    <NOMBRE>_USER                        solo para JSON-RPC; JSON-2 identifica al usuario por la clave

Pueden vivir en config.env (fuera del repo, por persona) o en el entorno; el
entorno gana. Nunca por argumento: quedan en el historial del shell y en la lista
de procesos.

Usá siempre una clave API, no tu contraseña de cuenta — se genera en
Preferencias -> Seguridad de la cuenta -> Clave API, y se puede revocar sola sin
tocar el resto de la cuenta si algo sale mal.

## Hasta dónde llega el "solo lectura"

Este script permite seis métodos de lectura y rechaza todo lo demás, antes de
elegir la API. Es una barrera del lado del cliente, no un permiso del lado del
servidor: la clave API conserva todos los permisos de tu usuario, así que
cualquier otra herramienta con esa clave sí puede escribir. Si necesitás una
garantía real, creá un usuario de Odoo con permisos de solo lectura y usá su clave.

## Uso

    odoo_query.py [--instance v19] fields account.move [--grep residual]
    odoo_query.py count account.move "[['state','=','draft']]"
    odoo_query.py search res.partner "[['id','=',123]]" --fields name,vat --limit 5
    odoo_query.py groupby account.move.line "[]" balance journal_id
"""
import ast
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

# Lista blanca. Cualquier otro método puede tener efectos secundarios: invocar
# métodos arbitrarios del modelo incluye write, unlink y los action_*.
READ_ONLY_METHODS = {
    "search", "search_read", "search_count", "read", "fields_get", "read_group",
}

# JSON-2 recibe los argumentos por nombre. Orden de los parámetros posicionales de
# cada método permitido, para traducir la forma execute_kw (args, kwargs) a un body.
# `read` lleva `ids` como primer parámetro: en JSON-2 `ids` es el recordset.
JSON2_PARAMS = {
    "search": ("domain", "offset", "limit", "order"),
    "search_read": ("domain", "fields", "offset", "limit", "order"),
    "search_count": ("domain", "limit"),
    "read": ("ids", "fields"),
    "fields_get": ("allfields", "attributes"),
    "read_group": ("domain", "fields", "groupby", "offset", "limit", "orderby", "lazy"),
}

API_AUTO, API_JSON2, API_JSONRPC = "auto", "json2", "jsonrpc"
HTTP_TIMEOUT = 120
PROBE_TIMEOUT = 20
SKILL_DIR = Path(__file__).resolve().parent.parent


def _config_candidates():
    xdg = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return [
        os.environ.get("RCA_CONFIG"),
        str(Path(xdg) / "odoo-incident-rca" / "config.env"),
        str(SKILL_DIR / "config.env"),
    ]


def _read_config_file():
    """Lee KEY=value del primer config.env que exista. No falla si no hay ninguno."""
    values = {}
    for cand in _config_candidates():
        if not cand or not Path(cand).is_file():
            continue
        for line in Path(cand).read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            m = re.match(r'^(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)=(.*)$', line)
            if m:
                values[m.group(1)] = m.group(2).strip().strip('"').strip("'")
        break
    return values


def _setting(name, cfg):
    """El entorno tiene prioridad sobre config.env."""
    return os.environ.get(name) or cfg.get(name) or ""


def _prefix(instance):
    return re.sub(r"[^A-Za-z0-9]", "_", instance).upper()


def _cwd_repo_name():
    try:
        url = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""
    return Path(url).name.removesuffix(".git")


def resolve_instance(flag, cfg):
    instances = _setting("INSTANCES", cfg).split()
    want = flag or os.environ.get("RCA_INSTANCE") or ""
    if not want:
        repo = _cwd_repo_name()
        for name in instances:
            match = _setting(f"{_prefix(name)}_REPO_MATCH", cfg)
            if match and match == repo:
                want = name
                break
    if not want:
        want = _setting("DEFAULT_INSTANCE", cfg)
    if not want and len(instances) == 1:
        want = instances[0]
    if not want:
        raise SystemExit(
            "ERROR: no pude decidir la instancia. Pasá --instance <nombre> "
            f"(INSTANCES='{' '.join(instances)}')."
        )
    if instances and want not in instances:
        raise SystemExit(f"ERROR: instancia '{want}' no está en INSTANCES='{' '.join(instances)}'.")
    return want


class Target:
    """Conexión resuelta de una instancia; las credenciales se leen al usarse."""

    def __init__(self, instance, cfg):
        self.instance = instance
        self.prefix = _prefix(instance)
        self.cfg = cfg
        self._api = None

    def optional(self, key):
        return _setting(f"{self.prefix}_{key}", self.cfg)

    def get(self, key):
        name = f"{self.prefix}_{key}"
        value = _setting(name, self.cfg)
        if not value:
            raise SystemExit(
                f"ERROR: falta {name}.\n"
                "Definila en config.env o por variable de entorno.\n"
                "Para USER / API_KEY usá una clave API, no tu contraseña:\n"
                "Preferencias -> Seguridad de la cuenta -> Clave API."
            )
        return value

    def api(self):
        """json2 o jsonrpc, resuelto una sola vez por corrida."""
        if self._api is None:
            wanted = (self.optional("RPC_API") or API_AUTO).lower()
            if wanted not in (API_AUTO, API_JSON2, API_JSONRPC):
                raise SystemExit(f"ERROR: {self.prefix}_RPC_API debe ser auto, json2 o jsonrpc (vino '{wanted}').")
            if wanted == API_AUTO:
                wanted = API_JSON2 if json2_available(self.get("URL"), self.optional("DB")) else API_JSONRPC
            self._api = wanted
            print(f"[api: {self._api}]", file=sys.stderr)
        return self._api


def _post(url, payload, headers, timeout=HTTP_TIMEOUT):
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def json2_available(url, db):
    """¿La instancia sirve /json/2? Request sin autenticar: 401 = existe, 404 = no.

    No lleva credenciales, así que no filtra nada y no cuenta como acceso. Cualquier
    otra respuesta (red caída, 5xx) se propaga: no se adivina la API con la instancia
    inalcanzable.
    """
    headers = {"Content-Type": "application/json"}
    if db:
        headers["X-Odoo-Database"] = db
    try:
        _post(url.rstrip("/") + "/json/2/res.users/search", {"domain": []}, headers, PROBE_TIMEOUT)
    except urllib.error.HTTPError as e:
        if e.code == 401:
            return True
        if e.code in (404, 405):
            return False
        raise SystemExit(f"ERROR: la prueba de /json/2 devolvió HTTP {e.code}; no sé qué API usar. "
                         "Fijala con <NOMBRE>_RPC_API=json2|jsonrpc.")
    except urllib.error.URLError as e:
        raise SystemExit(f"ERROR: no pude conectar con {url}: {e.reason}")
    # 2xx sin credenciales sobre /json/2/...: la ruta existe.
    return True


def _error_text(raw):
    """Mensaje legible de un cuerpo de error JSON-2 ({name, message, debug}) o de texto plano."""
    try:
        body = json.loads(raw)
    except ValueError:
        return raw[:800]
    if isinstance(body, dict):
        return f"{body.get('name', 'error')}: {body.get('message', '')}\n{str(body.get('debug', ''))[:800]}"
    return raw[:800]


def call_json2(target, model, method, args, kwargs):
    url, key = target.get("URL"), target.get("API_KEY")
    names = JSON2_PARAMS[method]
    if len(args) > len(names):
        raise SystemExit(f"ERROR: demasiados argumentos posicionales para {method}.")
    body = dict(zip(names, args))
    body.update(kwargs)
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {key}"}
    db = target.optional("DB")
    if db:
        headers["X-Odoo-Database"] = db
    try:
        return _post(f"{url.rstrip('/')}/json/2/{model}/{method}", body, headers)
    except urllib.error.HTTPError as e:
        if e.code == 401:
            raise SystemExit(f"ERROR: autenticación rechazada. Revisá {target.prefix}_API_KEY / {target.prefix}_DB.")
        raise SystemExit(f"ERROR Odoo (HTTP {e.code}): {_error_text(e.read().decode(errors='replace'))}")
    except urllib.error.URLError as e:
        raise SystemExit(f"ERROR: no pude conectar con {url}: {e.reason}")


def rpc(url, service, method, args):
    payload = {
        "jsonrpc": "2.0", "method": "call",
        "params": {"service": service, "method": method, "args": args},
        "id": 1,
    }
    body = _post(url.rstrip("/") + "/jsonrpc", payload, {"Content-Type": "application/json"})
    if "error" in body:
        err = body["error"]
        data = err.get("data", {})
        msg = data.get("message") or err.get("message", "error desconocido")
        raise SystemExit(f"ERROR Odoo: {msg}\n{data.get('debug', '')[:800]}")
    return body.get("result")


def call_jsonrpc(target, model, method, args, kwargs):
    url, db, user, key = (target.get(n) for n in ("URL", "DB", "USER", "API_KEY"))
    uid = rpc(url, "common", "login", [db, user, key])
    if not uid:
        raise SystemExit(
            f"ERROR: autenticación rechazada. Revisá {target.prefix}_USER / "
            f"{target.prefix}_API_KEY / {target.prefix}_DB."
        )
    return rpc(url, "object", "execute_kw", [db, uid, key, model, method, args, kwargs])


def call(target, model, method, args, kwargs=None):
    """Una llamada de lectura. La lista blanca se aplica antes de elegir la API."""
    if method not in READ_ONLY_METHODS:
        raise SystemExit(
            f"ERROR: '{method}' no está permitido. Este script es de solo lectura.\n"
            f"Permitidos: {', '.join(sorted(READ_ONLY_METHODS))}\n"
            "Para escribir, hacelo desde la interfaz de Odoo con la trazabilidad correspondiente."
        )
    kwargs = kwargs or {}
    if target.api() == API_JSON2:
        return call_json2(target, model, method, args, kwargs)
    return call_jsonrpc(target, model, method, args, kwargs)


def cmd_fields(target, model, grep=None):
    res = call(target, model, "fields_get", [[]], {"attributes": ["string", "type", "relation", "store", "required"]})
    rows = sorted(res.items())
    if grep:
        g = grep.lower()
        rows = [(n, m) for n, m in rows if g in n.lower() or g in (m.get("string") or "").lower()]
    print(f"{model}: {len(rows)} campos" + (f" que matchean '{grep}'" if grep else ""))
    for name, meta in rows:
        rel = f" -> {meta['relation']}" if meta.get("relation") else ""
        stored = "" if meta.get("store", True) else "  (no almacenado)"
        req = "  (requerido)" if meta.get("required") else ""
        print(f"  {name:<44} {meta.get('type','?'):<14}{rel}{stored}{req}")
        print(f"  {'':<44} {meta.get('string','')}")


def cmd_search(target, model, domain, fields=None, limit=10, order=None):
    kw = {"limit": int(limit)}
    if fields:
        kw["fields"] = [f.strip() for f in fields.split(",")]
    if order:
        kw["order"] = order
    res = call(target, model, "search_read", [domain], kw)
    print(json.dumps(res, indent=2, ensure_ascii=False, default=str))
    print(f"\n-- {len(res)} registros (limit={limit})", file=sys.stderr)


def cmd_count(target, model, domain):
    print(call(target, model, "search_count", [domain]))


def cmd_groupby(target, model, domain, fields, groupby, limit=40):
    res = call(target, model, "read_group", [domain, [f.strip() for f in fields.split(",")],
                                             [g.strip() for g in groupby.split(",")]],
               {"lazy": False, "limit": int(limit)})
    print(json.dumps(res, indent=2, ensure_ascii=False, default=str))


def parse_domain(text):
    """Acepta tanto JSON (comillas dobles) como literales Python/Odoo
    (comillas simples, True/False/None) — los dominios de Odoo se escriben
    convencionalmente como estos últimos."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        try:
            return ast.literal_eval(text)
        except (ValueError, SyntaxError) as e:
            raise SystemExit(f"ERROR: no pude parsear el dominio: {text!r}\n{e}")


def _pop_instance_flag(argv):
    """Saca --instance X / --instance=X de argv. Devuelve (valor, argv_sin_flag)."""
    out, value, i = [], "", 0
    while i < len(argv):
        a = argv[i]
        if a == "--instance":
            if i + 1 >= len(argv):
                raise SystemExit("ERROR: --instance necesita un nombre.")
            value = argv[i + 1]
            i += 2
        elif a.startswith("--instance="):
            value = a.split("=", 1)[1]
            i += 1
        else:
            out.append(a)
            i += 1
    return value, out


def main():
    flag, argv = _pop_instance_flag(sys.argv[1:])
    if len(argv) < 2:
        print(__doc__)
        raise SystemExit(2)
    cfg = _read_config_file()
    instance = resolve_instance(flag, cfg)
    print(f"[instancia: {instance}]", file=sys.stderr)
    target = Target(instance, cfg)

    cmd, model = argv[0], argv[1]
    rest = argv[2:]

    def opt(name, default=None):
        return rest[rest.index(name) + 1] if name in rest else default

    positional = [a for i, a in enumerate(rest)
                  if not a.startswith("--") and (i == 0 or not rest[i - 1].startswith("--"))]

    if cmd == "fields":
        cmd_fields(target, model, opt("--grep"))
    elif cmd == "count":
        cmd_count(target, model, parse_domain(positional[0]) if positional else [])
    elif cmd == "search":
        cmd_search(target, model, parse_domain(positional[0]) if positional else [],
                   opt("--fields"), opt("--limit", 10), opt("--order"))
    elif cmd == "groupby":
        cmd_groupby(target, model, parse_domain(positional[0]), positional[1], positional[2],
                    opt("--limit", 40))
    else:
        raise SystemExit(f"comando desconocido: {cmd}\n{__doc__}")


if __name__ == "__main__":
    main()

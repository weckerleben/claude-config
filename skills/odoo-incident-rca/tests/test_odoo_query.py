"""Tests de odoo_query.py contra dos servidores falsos: uno con /json/2 (Odoo 19+)
y uno "legacy" que solo tiene /jsonrpc. Sin red ni credenciales reales.

    python3 -I -m unittest discover -s tests -v      (desde la carpeta del skill)
"""
import json
import os
import subprocess
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "odoo_query.py"
KEY = "test-key"


def make_handler(has_json2, seen):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def _send(self, code, body, ctype="application/json"):
            raw = body if isinstance(body, bytes) else json.dumps(body).encode()
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def do_POST(self):
            payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])) or b"{}")
            if self.path.startswith("/json/2/"):
                if not has_json2:
                    return self._send(404, b"<html>not found</html>", "text/html")
                if self.headers.get("Authorization") != f"Bearer {KEY}":
                    return self._send(401, {"name": "werkzeug.exceptions.Unauthorized",
                                            "message": "User not authenticated", "debug": ""})
                seen.append(("json2", self.path, payload, self.headers.get("X-Odoo-Database")))
                method = self.path.rsplit("/", 1)[1]
                if method == "search_count":
                    return self._send(200, 7)
                if method == "fields_get":
                    return self._send(200, {"name": {"string": "Name", "type": "char", "store": True}})
                return self._send(200, [{"id": 1, "name": "A"}])
            if self.path == "/jsonrpc":
                params = payload["params"]
                if params["service"] == "common":
                    return self._send(200, {"jsonrpc": "2.0", "id": 1, "result": 42})
                seen.append(("jsonrpc", params["args"][4], params["args"][5], params["args"][6]))
                result = 7 if params["args"][4] == "search_count" else [{"id": 1, "name": "A"}]
                return self._send(200, {"jsonrpc": "2.0", "id": 1, "result": result})
            return self._send(404, b"nope", "text/plain")

    return Handler


class FakeOdoo:
    def __init__(self, has_json2):
        self.seen = []
        self.server = HTTPServer(("127.0.0.1", 0), make_handler(has_json2, self.seen))
        self.url = f"http://127.0.0.1:{self.server.server_port}"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def close(self):
        self.server.shutdown()
        self.server.server_close()


def run(url, *args, **env):
    full_env = {k: v for k, v in os.environ.items() if not k.startswith(("RCA_", "V19_", "V16_"))}
    full_env.update({"RCA_CONFIG": "/nonexistent", "INSTANCES": "t", "DEFAULT_INSTANCE": "t",
                     "T_URL": url, "T_DB": "mydb", "T_API_KEY": KEY})
    full_env.update(env)
    return subprocess.run([sys.executable, "-I", str(SCRIPT), *args],
                          capture_output=True, text=True, env=full_env, cwd="/")


class OdooQueryApiSelection(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.modern, cls.legacy = FakeOdoo(True), FakeOdoo(False)

    @classmethod
    def tearDownClass(cls):
        cls.modern.close()
        cls.legacy.close()

    def setUp(self):
        self.modern.seen.clear()
        self.legacy.seen.clear()

    def test_auto_uses_json2_when_the_instance_has_it(self):
        r = run(self.modern.url, "count", "res.partner", "[['active','=',True]]")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.strip(), "7")
        self.assertIn("[api: json2]", r.stderr)
        kind, path, body, db = self.modern.seen[0]
        self.assertEqual((kind, path, db), ("json2", "/json/2/res.partner/search_count", "mydb"))
        self.assertEqual(body, {"domain": [["active", "=", True]]})

    def test_auto_falls_back_to_jsonrpc_when_there_is_no_json2(self):
        r = run(self.legacy.url, "count", "res.partner", "[]", T_USER="u@x")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.strip(), "7")
        self.assertIn("[api: jsonrpc]", r.stderr)
        self.assertEqual(self.legacy.seen[0][:2], ("jsonrpc", "search_count"))

    def test_json2_does_not_need_a_user(self):
        r = run(self.modern.url, "count", "res.partner", "[]")
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_jsonrpc_still_needs_a_user(self):
        r = run(self.legacy.url, "count", "res.partner", "[]")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("falta T_USER", r.stderr)

    def test_forced_api_skips_the_probe(self):
        r = run(self.legacy.url, "count", "res.partner", "[]", T_RPC_API="jsonrpc", T_USER="u@x")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("[api: jsonrpc]", r.stderr)
        r = run(self.modern.url, "count", "res.partner", "[]", T_RPC_API="jsonrpc", T_USER="u@x")
        self.assertIn("[api: jsonrpc]", r.stderr)

    def test_invalid_rpc_api_value_is_rejected(self):
        r = run(self.modern.url, "count", "res.partner", "[]", T_RPC_API="soap")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("T_RPC_API", r.stderr)

    def test_search_maps_to_named_json2_arguments(self):
        r = run(self.modern.url, "search", "res.partner", "[]", "--fields", "name,vat", "--limit", "3")
        self.assertEqual(r.returncode, 0, r.stderr)
        body = self.modern.seen[0][2]
        self.assertEqual(body, {"domain": [], "limit": 3, "fields": ["name", "vat"]})

    def test_groupby_maps_to_named_json2_arguments(self):
        r = run(self.modern.url, "groupby", "account.move.line", "[]", "balance", "journal_id")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.modern.seen[0][2],
                         {"domain": [], "fields": ["balance"], "groupby": ["journal_id"],
                          "lazy": False, "limit": 40})

    def test_fields_lists_json2_metadata(self):
        r = run(self.modern.url, "fields", "res.partner")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("name", r.stdout)

    def test_wrong_key_reports_auth_failure_on_json2(self):
        r = run(self.modern.url, "count", "res.partner", "[]", T_API_KEY="wrong")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("autenticación rechazada", r.stderr)

    def test_unreachable_instance_fails_instead_of_guessing(self):
        r = run("http://127.0.0.1:9", "count", "res.partner", "[]")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("no pude conectar", r.stderr)


class OdooQueryReadOnly(unittest.TestCase):
    def test_write_methods_are_refused_before_any_request(self):
        code = (
            "import sys; sys.path.insert(0, %r); import odoo_query as q;"
            "t = q.Target('t', {}); q.call(t, 'res.partner', 'write', [[1], {}])"
        ) % str(SCRIPT.parent)
        r = subprocess.run([sys.executable, "-I", "-c", code], capture_output=True, text=True,
                           env={"PATH": os.environ["PATH"]})
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("no está permitido", r.stderr)
        self.assertNotIn("[api:", r.stderr)


if __name__ == "__main__":
    unittest.main()

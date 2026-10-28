import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import skill_usage as su  # noqa: E402

NOW = datetime(2026, 10, 28, tzinfo=timezone.utc)


def write(tmp, records, name="s1.jsonl"):
    path = Path(tmp) / name
    path.write_text("\n".join(json.dumps(r) for r in records) + "\n")


def skill_call(name, ts="2026-10-20T10:00:00Z", **extra):
    rec = {"type": "assistant", "timestamp": ts, "message": {"content": [
        {"type": "tool_use", "name": "Skill", "input": {"skill": name}}]}}
    rec.update(extra)
    return rec


def slash(name, ts="2026-10-21T10:00:00Z"):
    return {"type": "user", "timestamp": ts, "message": {"role": "user",
            "content": f"<command-name>/{name}</command-name>\n<command-args></command-args>"}}


def make_skills(tmp, names):
    root = Path(tmp) / "skills"
    for n in names:
        (root / n).mkdir(parents=True)
        (root / n / "SKILL.md").write_text(f"---\nname: {n}\ndescription: x\n---\n")
    return root


class Usage(unittest.TestCase):
    def test_counts_skill_tool_calls_and_slash_commands(self):
        with tempfile.TemporaryDirectory() as tmp:
            write(tmp, [skill_call("adr-author"), skill_call("adr-author", "2026-10-25T10:00:00Z"),
                        slash("rfc-author")])
            u = su.usage(Path(tmp))
            self.assertEqual(u["adr-author"]["count"], 2)
            self.assertEqual(u["adr-author"]["last_used"], "2026-10-25T10:00:00Z")
            self.assertEqual(u["rfc-author"]["count"], 1)

    def test_namespaced_calls_are_kept_under_their_full_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            write(tmp, [skill_call("ecc:make-interfaces-feel-better")])
            self.assertIn("ecc:make-interfaces-feel-better", su.usage(Path(tmp)))

    def test_subagent_calls_count_and_sessions_are_distinct(self):
        with tempfile.TemporaryDirectory() as tmp:
            write(tmp, [skill_call("x", isSidechain=True)], "a.jsonl")
            write(tmp, [skill_call("x")], "b.jsonl")
            u = su.usage(Path(tmp))
            self.assertEqual(u["x"]["count"], 2)
            self.assertEqual(sorted(u["x"]["sessions"]), ["a.jsonl", "b.jsonl"])

    def test_ignores_corrupt_lines_and_other_tools(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "s.jsonl"
            other = {"type": "assistant", "message": {"content": [
                {"type": "tool_use", "name": "Bash", "input": {"command": "ls"}}]}}
            path.write_text("{bad\n" + json.dumps(other) + "\n")
            self.assertEqual(su.usage(Path(tmp)), {})


class Report(unittest.TestCase):
    def test_classifies_used_never_and_too_new(self):
        with tempfile.TemporaryDirectory() as tmp:
            write(tmp, [skill_call("used-one")])
            skills = make_skills(tmp, ["used-one", "never-one", "new-one"])
            old = datetime(2026, 8, 1, tzinfo=timezone.utc).timestamp()
            for n in ("used-one", "never-one"):
                import os
                os.utime(skills / n / "SKILL.md", (old, old))
            os_new = datetime(2026, 10, 25, tzinfo=timezone.utc).timestamp()
            import os
            os.utime(skills / "new-one" / "SKILL.md", (os_new, os_new))
            rows = {r["name"]: r for r in su.report(su.usage(Path(tmp)), skills, now=NOW, grace_days=14)}
            self.assertEqual(rows["used-one"]["status"], "used")
            self.assertEqual(rows["never-one"]["status"], "never")
            self.assertEqual(rows["new-one"]["status"], "too-new")

    def test_never_used_sort_first_and_report_is_read_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            write(tmp, [skill_call("used-one")])
            skills = make_skills(tmp, ["used-one", "never-one"])
            before = sorted(p.name for p in skills.iterdir())
            rows = su.report(su.usage(Path(tmp)), skills, now=datetime.now(timezone.utc), grace_days=0)
            self.assertEqual(rows[0]["name"], "never-one")
            self.assertEqual(sorted(p.name for p in skills.iterdir()), before)


if __name__ == "__main__":
    unittest.main()

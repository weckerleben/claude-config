import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import mine_workflows as mw  # noqa: E402


def bash(cmd, day=10, **extra):
    rec = {"type": "assistant", "timestamp": f"2026-10-{day:02d}T10:00:00Z", "sessionId": "s",
           "message": {"content": [{"type": "tool_use", "name": "Bash", "input": {"command": cmd}}]}}
    rec.update(extra)
    return rec


def skill(name, day=10):
    return {"type": "assistant", "timestamp": f"2026-10-{day:02d}T10:00:00Z", "sessionId": "s",
            "message": {"content": [{"type": "tool_use", "name": "Skill", "input": {"skill": name}}]}}


def write(tmp, records, name="s1.jsonl", project=None):
    d = Path(tmp) / project if project else Path(tmp)
    d.mkdir(parents=True, exist_ok=True)
    (d / name).write_text("\n".join(json.dumps(r) for r in records) + "\n")


class Family(unittest.TestCase):
    def test_ssh_family_uses_the_host_and_skips_option_arguments(self):
        self.assertEqual(mw.families("ssh -o ConnectTimeout=5 zeus.local 'sudo systemctl status x'"), ["ssh zeus.local"])
        self.assertEqual(mw.families("ssh -i ~/.ssh/key -p 2222 zeus 'cd /opt'"), ["ssh zeus"])

    def test_scp_and_curl_use_the_remote_host(self):
        self.assertEqual(mw.families("scp zeus:/tmp/a.gz ~/backups/"), ["scp zeus"])
        self.assertEqual(mw.families("curl -fsS https://zeus.example/health"), ["curl zeus.example"])

    def test_docker_compose_and_git_keep_the_subcommand(self):
        self.assertEqual(mw.families("docker compose up -d"), ["docker compose up"])
        self.assertEqual(mw.families("git push origin main"), ["git push"])

    def test_trivial_commands_are_ignored(self):
        self.assertEqual(mw.families("cd /tmp && ls -la && git status"), [])

    def test_compound_command_yields_each_meaningful_segment_and_respects_quotes(self):
        cmd = "cd /opt && ssh zeus 'a; b' && docker compose pull"
        self.assertEqual(mw.families(cmd), ["ssh zeus", "docker compose pull"])

    def test_script_runs_are_named_but_inline_python_is_trivial(self):
        self.assertEqual(mw.families("python3 scripts/deploy.py --prod"), ["python3 deploy.py"])
        self.assertEqual(mw.families("python3 -c 'print(1)'"), [])


class ShellSyntax(unittest.TestCase):
    def test_loop_keywords_are_not_commands_but_the_body_is(self):
        self.assertEqual(mw.families("for p in 1 2; do ssh zeus 'x'; done"), ["ssh zeus"])

    def test_if_then_else_keeps_the_commands_inside(self):
        cmd = "if curl -fsS https://zeus.example/h; then echo ok; else echo no; fi"
        self.assertEqual(mw.families(cmd), ["curl zeus.example"])

    def test_heredoc_bodies_are_ignored(self):
        self.assertEqual(mw.families("cat > f.py <<'EOF'\nimport os\nprint(1)\nEOF"), [])
        self.assertEqual(mw.families("python3 - <<'PY'\nimport sys\nPY"), [])
        self.assertEqual(mw.families("ssh zeus 'x' && cat > a <<EOF\nsiempre\nEOF\ndocker compose up -d"),
                         ["ssh zeus", "docker compose up"])

    def test_comments_braces_and_assignments_are_ignored(self):
        for cmd in ("# explanation", "}", "{", "pid=$(lsof -ti :3000)", "done", "fi", "esac"):
            self.assertEqual(mw.families(cmd), [], cmd)

    def test_multiline_loop_with_do_on_its_own_line(self):
        cmd = "for h in a b\ndo\n  ssh $h uptime\ndone"
        self.assertEqual(mw.families(cmd), ["ssh $h"])


class Redaction(unittest.TestCase):
    def test_secrets_are_redacted_in_examples(self):
        out = mw.redact("curl -H 'Authorization: Bearer abc123def456' https://x --token=s3cr3tvalue sk-abcdefghijklmnop1234")
        self.assertNotIn("abc123def456", out)
        self.assertNotIn("s3cr3tvalue", out)
        self.assertNotIn("sk-abcdefghijklmnop1234", out)
        self.assertIn("<redacted>", out)


class Mine(unittest.TestCase):
    def test_family_needs_the_minimum_number_of_distinct_sessions(self):
        with tempfile.TemporaryDirectory() as tmp:
            for i in range(3):
                write(tmp, [bash("ssh zeus 'uptime'"), bash("ssh zeus 'df -h'")], f"s{i}.jsonl")
            write(tmp, [bash("ssh other 'uptime'")], "s9.jsonl")
            fams = [c for c in mw.mine(Path(tmp)) if c["kind"] == "family"]
            self.assertEqual([c["signature"] for c in fams], ["ssh zeus"])
            self.assertEqual(fams[0]["session_count"], 3)

    def test_repeats_inside_one_session_count_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            write(tmp, [bash("ssh zeus 'a'")] * 10)
            self.assertEqual(mw.mine(Path(tmp)), [])

    def test_ordered_chain_across_sessions_is_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            for i in range(3):
                write(tmp, [bash("ssh zeus 'git pull'"), bash("ssh zeus 'x'"), bash("docker compose up -d"),
                            bash("curl -fsS https://zeus.example/health")], f"s{i}.jsonl")
            chains = [c for c in mw.mine(Path(tmp)) if c["kind"] == "chain"]
            self.assertIn("ssh zeus → docker compose up → curl zeus.example", [c["signature"] for c in chains])

    def test_subsumed_shorter_chain_is_dropped(self):
        with tempfile.TemporaryDirectory() as tmp:
            for i in range(3):
                write(tmp, [bash("ssh zeus 'a'"), bash("docker compose up -d"), bash("curl https://zeus.example/h")], f"s{i}.jsonl")
            sigs = [c["signature"] for c in mw.mine(Path(tmp)) if c["kind"] == "chain"]
            self.assertEqual(len(sigs), 1)

    def test_skill_chains_are_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            for i in range(3):
                write(tmp, [skill("plan"), skill("tdd")], f"s{i}.jsonl")
            sigs = [c["signature"] for c in mw.mine(Path(tmp)) if c["kind"] == "skill-chain"]
            self.assertEqual(sigs, ["plan → tdd"])

    def test_subagent_records_are_ignored(self):
        with tempfile.TemporaryDirectory() as tmp:
            for i in range(3):
                write(tmp, [bash("ssh zeus 'a'", isSidechain=True)], f"s{i}.jsonl")
            self.assertEqual(mw.mine(Path(tmp)), [])

    def test_examples_are_capped_and_redacted(self):
        with tempfile.TemporaryDirectory() as tmp:
            for i in range(5):
                write(tmp, [bash(f"curl -H 'Authorization: Bearer tok{i}abcdefgh' https://api.example/x{i}")], f"s{i}.jsonl")
            [c] = [c for c in mw.mine(Path(tmp)) if c["kind"] == "family"]
            self.assertLessEqual(len(c["examples"]), 3)
            self.assertTrue(all("abcdefgh" not in e for e in c["examples"]))

    def test_projects_are_collected_and_since_filters(self):
        with tempfile.TemporaryDirectory() as tmp:
            for i, proj in enumerate(("p-a", "p-b", "p-c")):
                write(tmp, [bash("ssh zeus 'a'", day=10 + i)], "s.jsonl", project=proj)
            [c] = mw.mine(Path(tmp))
            self.assertEqual(sorted(c["projects"]), ["p-a", "p-b", "p-c"])
            self.assertEqual(mw.mine(Path(tmp), since="2026-10-12"), [])

    def test_corrupt_lines_and_other_tools_are_ignored(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "s.jsonl").write_text("{bad\n" + json.dumps({"type": "assistant", "message": {"content": [
                {"type": "tool_use", "name": "Read", "input": {"file_path": "x"}}]}}) + "\n")
            self.assertEqual(mw.mine(Path(tmp)), [])

    def test_handled_ids_are_suppressed(self):
        with tempfile.TemporaryDirectory() as tmp:
            for i in range(3):
                write(tmp, [bash("ssh zeus 'a'")], f"s{i}.jsonl")
            [c] = mw.mine(Path(tmp))
            self.assertEqual(mw.mine(Path(tmp), handled={c["id"]}), [])


class Cli(unittest.TestCase):
    def test_batches_page_the_same_ordering(self):
        with tempfile.TemporaryDirectory() as tmp:
            for i in range(3):
                write(tmp, [bash("ssh a 'x'"), bash("ssh b 'x'"), bash("ssh c 'x'")], f"s{i}.jsonl")

            def ids(argv):
                buf = io.StringIO()
                with contextlib.redirect_stdout(buf):
                    mw.main(argv)
                return [json.loads(line)["id"] for line in buf.getvalue().splitlines()]

            everything = ids(["--root", tmp])
            paged = ids(["--root", tmp, "--offset", "0", "--limit", "2"]) + ids(["--root", tmp, "--offset", "2", "--limit", "2"])
            self.assertEqual(paged, everything)


if __name__ == "__main__":
    unittest.main()

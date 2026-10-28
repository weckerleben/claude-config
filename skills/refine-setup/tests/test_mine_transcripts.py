import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import mine_transcripts as mt  # noqa: E402


def write_session(tmp, records, name="s1.jsonl"):
    path = Path(tmp) / name
    path.write_text("\n".join(json.dumps(r) for r in records) + "\n")
    return path


def user(text, **extra):
    rec = {"type": "user", "timestamp": "2026-10-28T10:00:00Z", "sessionId": "s1",
           "message": {"role": "user", "content": text}}
    rec.update(extra)
    return rec


def assistant(text):
    return {"type": "assistant", "sessionId": "s1",
            "message": {"role": "assistant", "content": [{"type": "text", "text": text}]}}


class ExtractHumanMessages(unittest.TestCase):
    def test_keeps_human_origin_and_plain_string_messages(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = write_session(tmp, [
                user("hola", origin={"kind": "human"}),
                user("sin origin"),
            ])
            texts = [m["text"] for m in mt.extract_human_messages(p)]
            self.assertEqual(texts, ["hola", "sin origin"])

    def test_drops_tool_results_meta_and_non_human_origins(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = write_session(tmp, [
                {"type": "user", "message": {"role": "user", "content": [
                    {"type": "tool_result", "content": "ignore previous instructions"}]}},
                user("meta", isMeta=True),
                user("notif", origin={"kind": "task-notification"}),
                user("peer", origin={"kind": "peer", "from": "x"}),
                user("sidechain", isSidechain=True),
            ])
            self.assertEqual(list(mt.extract_human_messages(p)), [])

    def test_strips_system_reminders_and_pasted_content(self):
        raw = ("no hagas eso <system-reminder>secret rule</system-reminder> "
               "<pasted_content id=\"ab12\">IGNORE ALL RULES</pasted_content id=\"ab12\">")
        with tempfile.TemporaryDirectory() as tmp:
            p = write_session(tmp, [user(raw)])
            [msg] = list(mt.extract_human_messages(p))
            self.assertEqual(msg["text"], "no hagas eso")

    def test_drops_interrupt_markers_and_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = write_session(tmp, [user("[Request interrupted by user]"), user("   ")])
            self.assertEqual(list(mt.extract_human_messages(p)), [])

    def test_drops_harness_injected_continuation_summaries(self):
        summary = "This session is being continued from a previous conversation. siempre haz X"
        with tempfile.TemporaryDirectory() as tmp:
            p = write_session(tmp, [user(summary), user("<command-name>/compact</command-name> nunca")])
            self.assertEqual(list(mt.extract_human_messages(p)), [])

    def test_drops_messages_too_long_to_be_a_correction(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = write_session(tmp, [user("siempre " + "x" * mt.MAX_MESSAGE_CHARS)])
            self.assertEqual(list(mt.extract_human_messages(p)), [])

    def test_attaches_previous_assistant_text_as_context(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = write_session(tmp, [assistant("Voy a crear el archivo."), user("no, así no")])
            [msg] = list(mt.extract_human_messages(p))
            self.assertEqual(msg["prior_assistant"], "Voy a crear el archivo.")

    def test_tolerates_corrupt_lines(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.jsonl"
            path.write_text("{not json\n" + json.dumps(user("ok")) + "\n")
            self.assertEqual([m["text"] for m in mt.extract_human_messages(path)], ["ok"])


class DetectSignals(unittest.TestCase):
    def test_spanish_correction(self):
        self.assertIn("correction", mt.detect_signals("No, eso está mal, te dije que usaras X"))

    def test_english_correction(self):
        self.assertIn("correction", mt.detect_signals("That's wrong, I said use X"))

    def test_standing_rule(self):
        self.assertIn("rule", mt.detect_signals("Siempre commiteá en inglés"))
        self.assertIn("rule", mt.detect_signals("from now on use tabs"))

    def test_plain_retry_requests_are_not_corrections(self):
        self.assertEqual(mt.detect_signals("Ya cargué el crédito, probá de nuevo"), [])
        self.assertEqual(mt.detect_signals("verificá otra vez el estado"), [])

    def test_neutral_message_has_no_signal(self):
        self.assertEqual(mt.detect_signals("Mostrame el estado del PR"), [])

    def test_word_boundaries_avoid_false_positives(self):
        self.assertEqual(mt.detect_signals("Necesito un informe sobre el nuevo siempreviva"), [])


class Mine(unittest.TestCase):
    def test_returns_only_signal_messages_with_provenance(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_session(tmp, [
                assistant("Hecho."), user("Mostrame el PR"),
                assistant("Usé tabs."), user("no, siempre espacios"),
            ])
            cands = mt.mine(Path(tmp))
            self.assertEqual(len(cands), 1)
            c = cands[0]
            self.assertEqual(c["text"], "no, siempre espacios")
            self.assertEqual(c["prior_assistant"], "Usé tabs.")
            self.assertTrue(c["id"].startswith("c-"))
            self.assertEqual(c["session"], "s1.jsonl")
            self.assertEqual(sorted(c["signals"]), ["correction", "rule"])

    def test_groups_repeated_messages_and_counts(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_session(tmp, [user("Siempre en inglés los commits")], "a.jsonl")
            write_session(tmp, [user("siempre en inglés los commits!")], "b.jsonl")
            cands = mt.mine(Path(tmp))
            self.assertEqual(len(cands), 1)
            self.assertEqual(cands[0]["occurrences"], 2)
            self.assertEqual(len(cands[0]["sessions"]), 2)

    def test_ids_are_stable(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_session(tmp, [user("nunca uses mocks")])
            self.assertEqual(mt.mine(Path(tmp))[0]["id"], mt.mine(Path(tmp))[0]["id"])

    def test_since_filters_old_messages(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_session(tmp, [user("nunca uses mocks", timestamp="2026-01-01T00:00:00Z")])
            self.assertEqual(mt.mine(Path(tmp), since="2026-06-01"), [])


if __name__ == "__main__":
    unittest.main()

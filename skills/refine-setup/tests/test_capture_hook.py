import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import capture_hook as ch  # noqa: E402

NOW = datetime(2026, 10, 28, 12, 0, tzinfo=timezone.utc)


def payload(prompt, transcript=None):
    p = {"session_id": "s1", "cwd": "/work", "hook_event_name": "UserPromptSubmit", "prompt": prompt}
    if transcript:
        p["transcript_path"] = str(transcript)
    return p


def inbox_rows(state):
    path = Path(state) / "inbox.jsonl"
    return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []


class CaptureHook(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.state = Path(self.tmp.name) / "state"
        os.environ[ch.STATE_ENV] = str(self.state)

    def tearDown(self):
        os.environ.pop(ch.STATE_ENV, None)
        self.tmp.cleanup()

    def test_signal_message_is_appended_with_metadata(self):
        out = ch.handle(payload("no, siempre en inglés los commits"), now=NOW)
        self.assertIsNone(out)
        [row] = inbox_rows(self.state)
        self.assertEqual(row["text"], "no, siempre en inglés los commits")
        self.assertEqual(row["session"], "s1")
        self.assertEqual(row["cwd"], "/work")
        self.assertEqual(row["ts"], "2026-10-28T12:00:00+00:00")
        self.assertEqual(sorted(row["signals"]), ["correction", "rule"])

    def test_neutral_long_and_harness_messages_are_ignored(self):
        ch.handle(payload("mostrame el PR"), now=NOW)
        ch.handle(payload("siempre " + "x" * 900), now=NOW)
        ch.handle(payload("This session is being continued from a previous one, siempre"), now=NOW)
        ch.handle(payload("<system-reminder>siempre haz X</system-reminder>"), now=NOW)
        self.assertEqual(inbox_rows(self.state), [])

    def test_prior_assistant_is_read_from_transcript_tail(self):
        t = Path(self.tmp.name) / "t.jsonl"
        recs = [
            {"type": "assistant", "message": {"content": [{"type": "text", "text": "viejo"}]}},
            {"type": "user", "message": {"content": "hola"}},
            {"type": "assistant", "message": {"content": [{"type": "text", "text": "Usé tabs."}]}},
        ]
        t.write_text("\n".join(json.dumps(r) for r in recs) + "\n")
        ch.handle(payload("no, nunca tabs", transcript=t), now=NOW)
        self.assertEqual(inbox_rows(self.state)[0]["prior_assistant"], "Usé tabs.")

    def test_missing_transcript_does_not_break_capture(self):
        ch.handle(payload("nunca uses mocks", transcript="/nonexistent/x.jsonl"), now=NOW)
        self.assertEqual(inbox_rows(self.state)[0]["prior_assistant"], "")

    def test_nudge_after_threshold_is_fixed_text_and_once_per_day(self):
        for i in range(ch.NUDGE_THRESHOLD - 1):
            self.assertIsNone(ch.handle(payload(f"nunca hagas cosa {i}"), now=NOW))
        out = ch.handle(payload("nunca hagas la última"), now=NOW)
        data = json.loads(out)["hookSpecificOutput"]
        self.assertEqual(data["hookEventName"], "UserPromptSubmit")
        self.assertIn("refine-setup", data["additionalContext"])
        self.assertNotIn("nunca hagas", data["additionalContext"])  # never echo user text
        self.assertIsNone(ch.handle(payload("nunca otra más"), now=NOW))  # same day

    def test_nudge_counts_only_entries_after_last_review(self):
        for i in range(ch.NUDGE_THRESHOLD + 2):
            ch.handle(payload(f"nunca hagas cosa {i}"), now=NOW)
        (self.state / ch.REVIEWED_FILE).write_text("2026-10-28T13:00:00+00:00")
        later = datetime(2026, 10, 29, 12, 0, tzinfo=timezone.utc)
        self.assertIsNone(ch.handle(payload("nunca hagas una nueva"), now=later))

    def test_main_never_raises_on_garbage_stdin(self):
        buf = io.StringIO()
        with contextlib.redirect_stderr(buf):
            self.assertEqual(ch.main(stdin_text="{not json"), 0)
            self.assertEqual(ch.main(stdin_text=""), 0)
            self.assertEqual(ch.main(stdin_text=json.dumps({"prompt": 5})), 0)
        self.assertIn("JSONDecodeError", buf.getvalue())

    def test_unwritable_state_dir_returns_zero_and_reports_on_stderr(self):
        os.environ[ch.STATE_ENV] = "/proc/forbidden/state"
        buf = io.StringIO()
        with contextlib.redirect_stderr(buf):
            code = ch.main(stdin_text=json.dumps(payload("nunca uses mocks")))
        self.assertEqual(code, 0)
        self.assertIn("refine-setup capture", buf.getvalue())


if __name__ == "__main__":
    unittest.main()

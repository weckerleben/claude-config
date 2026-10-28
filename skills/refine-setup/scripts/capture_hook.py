#!/usr/bin/env python3
"""UserPromptSubmit hook: log William's corrections/rules and nudge when many are unreviewed.

Design constraints:
- Never blocks or fails a prompt: always exits 0; errors go to stderr.
- Writes only to ~/.claude/self-improvement/ (override with REFINE_SETUP_STATE).
- The nudge is fixed text. User text is never echoed into the model context, so a
  crafted prompt or pasted page cannot use this hook to inject instructions.
"""
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mine_transcripts as mt  # noqa: E402

STATE_ENV = "REFINE_SETUP_STATE"
INBOX = "inbox.jsonl"
REVIEWED_FILE = "reviewed-at.txt"
NUDGED_FILE = "nudged-on.txt"
NUDGE_THRESHOLD = 10
TRANSCRIPT_TAIL_BYTES = 200_000
NUDGE_TEXT = (
    "Hay correcciones tuyas sin revisar en ~/.claude/self-improvement/inbox.jsonl. "
    "Cuando cierres lo que estás haciendo, ofrecé correr el skill refine-setup."
)


def state_dir():
    override = os.environ.get(STATE_ENV)
    return Path(override) if override else Path.home() / ".claude" / "self-improvement"


def last_assistant_text(transcript_path):
    """Return the most recent assistant text in the transcript tail, or ''."""
    if not transcript_path:
        return ""
    try:
        path = Path(transcript_path)
        size = path.stat().st_size
        with path.open("rb") as fh:
            fh.seek(max(0, size - TRANSCRIPT_TAIL_BYTES))
            raw = fh.read().decode("utf-8", errors="replace")
    except OSError:
        return ""
    for line in reversed(raw.splitlines()):
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if rec.get("type") == "assistant":
            text = mt._assistant_text(rec).strip()
            if text:
                return text[: mt.PRIOR_ASSISTANT_MAX]
    return ""


def _read(path):
    try:
        return path.read_text().strip()
    except OSError:
        return ""


def _pending_count(state, reviewed_at):
    inbox = state / INBOX
    if not inbox.exists():
        return 0
    count = 0
    for line in inbox.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            ts = json.loads(line).get("ts", "")
        except json.JSONDecodeError:
            continue
        if ts > reviewed_at:
            count += 1
    return count


def handle(payload, now=None):
    """Process one hook payload. Returns hook stdout (JSON string) or None."""
    now = now or datetime.now(timezone.utc)
    prompt = payload.get("prompt")
    if not isinstance(prompt, str):
        return None
    text = mt._clean(prompt)
    if not text or len(text) > mt.MAX_MESSAGE_CHARS or text.startswith(mt._HARNESS_PREFIXES):
        return None
    signals = mt.detect_signals(text)
    if not signals:
        return None

    state = state_dir()
    state.mkdir(parents=True, exist_ok=True)
    row = {
        "ts": now.isoformat(timespec="seconds"),
        "session": payload.get("session_id", ""),
        "cwd": payload.get("cwd", ""),
        "text": text,
        "signals": signals,
        "prior_assistant": last_assistant_text(payload.get("transcript_path")),
    }
    with (state / INBOX).open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    today = now.date().isoformat()
    if _read(state / NUDGED_FILE) == today:
        return None
    if _pending_count(state, _read(state / REVIEWED_FILE)) < NUDGE_THRESHOLD:
        return None
    (state / NUDGED_FILE).write_text(today)
    return json.dumps({"hookSpecificOutput": {
        "hookEventName": "UserPromptSubmit", "additionalContext": NUDGE_TEXT}})


def main(stdin_text=None):
    try:
        raw = sys.stdin.read() if stdin_text is None else stdin_text
        payload = json.loads(raw) if raw.strip() else {}
        out = handle(payload) if isinstance(payload, dict) else None
        if out:
            sys.stdout.write(out)
    except Exception as exc:  # a capture hook must never break the user's prompt
        sys.stderr.write(f"refine-setup capture: {type(exc).__name__}: {exc}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())

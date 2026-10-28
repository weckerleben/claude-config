#!/usr/bin/env python3
"""Mine Claude Code transcripts for user corrections and standing rules.

Reads only what the human typed. Tool results, subagent hand-backs, meta
records, system reminders and pasted blocks are discarded: they can contain
text from the web or from other models, and a self-editing system must never
promote that into a rule.

Output is a list of *candidates* (JSONL). Nothing here edits any file.
"""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

DEFAULT_ROOT = Path.home() / ".claude" / "projects"
PRIOR_ASSISTANT_MAX = 400
# Corrections are short. Longer messages are almost always pasted material or briefs.
MAX_MESSAGE_CHARS = 800

_STRIP_BLOCKS = [
    re.compile(r"<system-reminder>.*?</system-reminder>", re.S),
    re.compile(r"<pasted_content\b[^>]*>.*?</pasted_content\b[^>]*>", re.S),
]
_INTERRUPT = re.compile(r"^\[Request interrupted by user[^\]]*\]$")
# Strings the harness injects as "user" turns; they are not things the human typed.
_HARNESS_PREFIXES = ("This session is being continued", "<command-name>", "<local-command", "Caveat:")

# Word-boundary patterns; accents are matched explicitly because \b is ASCII-aware only for ASCII letters.
_SIGNALS = {
    "correction": re.compile(
        r"(?<![\w])(?:no[,.!]|no hagas|no así|no asi|está mal|esta mal|mal\b|te dije|"
        r"no era|no quiero|en vez de|stop|wrong|i said|don't|do not|instead|not what i)",
        re.I),
    "rule": re.compile(
        r"(?<![\w])(?:siempre|nunca|jamás|jamas|prohibido|a partir de ahora|de ahora en más|"
        r"de ahora en mas|recordá|recorda|acordate|from now on|always|never|every time)(?![\w])",
        re.I),
}


def _clean(text):
    for pat in _STRIP_BLOCKS:
        text = pat.sub("", text)
    return text.strip()


def _assistant_text(record):
    content = record.get("message", {}).get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text")
    return ""


def _is_human(record):
    if record.get("type") != "user" or record.get("isMeta") or record.get("isSidechain"):
        return False
    if not isinstance(record.get("message", {}).get("content"), str):
        return False
    origin = record.get("origin")
    return origin is None or (isinstance(origin, dict) and origin.get("kind") == "human")


def extract_human_messages(path):
    """Yield {text, timestamp, session, prior_assistant} for each human message."""
    path = Path(path)
    prior = ""
    with path.open(encoding="utf-8", errors="replace") as fh:
        for line in fh:
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if rec.get("type") == "assistant":
                text = _assistant_text(rec).strip()
                if text:
                    prior = text
                continue
            if not _is_human(rec):
                continue
            text = _clean(rec["message"]["content"])
            if not text or _INTERRUPT.match(text) or len(text) > MAX_MESSAGE_CHARS:
                continue
            if text.startswith(_HARNESS_PREFIXES):
                continue
            yield {
                "text": text,
                "timestamp": rec.get("timestamp", ""),
                "session": path.name,
                "prior_assistant": prior[:PRIOR_ASSISTANT_MAX],
            }


def detect_signals(text):
    return [name for name, pat in _SIGNALS.items() if pat.search(text)]


def _norm(text):
    return re.sub(r"[\W_]+", " ", text.lower()).strip()


def _candidate_id(norm_text):
    return "c-" + hashlib.sha1(norm_text.encode()).hexdigest()[:8]


def mine(root, since=None):
    """Return deduplicated candidates under `root`, most-repeated first."""
    groups = {}
    for path in sorted(Path(root).rglob("*.jsonl")):
        for msg in extract_human_messages(path):
            if since and msg["timestamp"][:10] < since:
                continue
            signals = detect_signals(msg["text"])
            if not signals:
                continue
            key = _norm(msg["text"])
            if not key:
                continue
            group = groups.get(key)
            if group is None:
                groups[key] = {
                    "id": _candidate_id(key), "text": msg["text"], "signals": signals,
                    "prior_assistant": msg["prior_assistant"], "session": msg["session"],
                    "timestamp": msg["timestamp"], "occurrences": 1, "sessions": [msg["session"]],
                }
            else:
                group["occurrences"] += 1
                if msg["session"] not in group["sessions"]:
                    group["sessions"].append(msg["session"])
    return sorted(groups.values(), key=lambda c: (-c["occurrences"], c["timestamp"]))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default=str(DEFAULT_ROOT), help="transcripts root (default ~/.claude/projects)")
    ap.add_argument("--since", help="YYYY-MM-DD lower bound")
    ap.add_argument("--limit", type=int, default=100)
    args = ap.parse_args(argv)
    for cand in mine(args.root, args.since)[: args.limit]:
        sys.stdout.write(json.dumps(cand, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()

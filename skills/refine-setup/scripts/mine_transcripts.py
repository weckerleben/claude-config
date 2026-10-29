#!/usr/bin/env python3
"""Mine Claude Code transcripts for user corrections and standing rules.

Reads only what the human typed (plus the text of his own tool rejections).
Tool results, subagent hand-backs, meta records, compaction summaries, system
reminders and pasted blocks are discarded: they can contain text from the web
or from other models, and a self-editing system must never promote that into
a rule.

Output is a list of *candidates* (JSONL). Nothing here edits any file.

Signal ideas (interrupt-redirect, tool-rejection text, repeat grouping by a
normalized key, harness-turn filters) were inspired by skill-miner and
claude-reflect; the code and the Spanish patterns are original.
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
MIN_INTERRUPT_REDIRECT_CHARS = 8
EXCERPT_SENTENCE_MAX = 300
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")

_STRIP_BLOCKS = [
    re.compile(r"<system-reminder>.*?</system-reminder>", re.S),
    re.compile(r"<pasted_content\b[^>]*>.*?</pasted_content\b[^>]*>", re.S),
]
_INTERRUPT = re.compile(r"^\[Request interrupted by user[^\]]*\]$")
# Strings the harness injects as "user" turns; they are not things the human typed.
_HARNESS_PREFIXES = (
    "This session is being continued", "<command-name>", "<local-command", "<bash-",
    "<task-notification", "<user-memory-input", "<teammate-message", "Caveat:",
    "Another Claude session sent a message",
)
# Stack traces, tracebacks and log lines pasted into the prompt.
_PASTED_LOG = re.compile(
    r"Traceback \(most recent call last\)|^\s+File \".+\", line \d+|^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}",
    re.M)
# Harness sentence that opens a tool result when the user rejects a tool call. Requiring the exact
# opening keeps a tool that merely prints similar words from being mistaken for the user.
_REJECTION_PREFIX = "The user doesn't want to proceed with this tool use."
_REJECTION_SAID = "the user said:\n"

_NOT_CORRECTION = re.compile(
    r"^\s*(?:no (?:hay )?problema|no pasa nada|no te preocupes|no hace falta|no (?:sé|se)\b|"
    r"no,? (?:así )?está bien|no,? (?:todo )?(?:bien|perfecto|dale)|"
    r"(?:perfecto|dale|genial|listo)[!,. ]+(?:ahora|ahí|y ahora|seguí))", re.I)

# Word-boundary patterns; accents are matched explicitly because \b is ASCII-aware only for ASCII letters.
_SIGNALS = {
    "correction": re.compile(
        r"(?<![\w])(?:no[,.!]|no hagas|no así|no asi|así no|asi no|eso no\b|no es (?:así|asi|eso|lo que)|"
        r"está mal|esta mal|mal\b|te dije|ya te dije|otra vez (?:en|con|lo mismo|así)|"
        r"de nuevo (?:en|con|lo mismo)|no era|no (?:te )?pedí|no quiero|en vez de|dejá (?:eso|todo) como|"
        r"revertí|volvé a como|seguís mal|stop|wrong|i said|don't|do not|instead|not what i)", re.I),
    "rule": re.compile(
        r"(?<![\w])(?:siempre|nunca|jamás|jamas|prohibido|a partir de ahora|a partir de hoy|"
        r"de ahora en más|de ahora en mas|que quede (?:claro|como regla)|regla:|hacelo regla|"
        r"no quiero que vuelvas a|recordá|recorda|acordate|from now on|always|never|every time)(?![\w])",
        re.I),
    "guardrail": re.compile(
        r"(?<![\w])(?:no (?:agregues|incluyas|crees|toques|cambies|refactorices|reorganices|borres)\b"
        r".{0,40}\b(?:a menos que|salvo que|sin que)|solo (?:cambiá|tocá|modificá) lo que|cambios mínimos|"
        r"dejá\s+.{1,30}\s+(?:quieto|en paz|como está)|no (?:compliques|sobreingenierices))", re.I),
}


def _clean(text):
    for pat in _STRIP_BLOCKS:
        text = pat.sub("", text)
    return text.strip()


def looks_like_pasted_log(text):
    return bool(_PASTED_LOG.search(text))


def _assistant_text(record):
    content = record.get("message", {}).get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text")
    return ""


def _is_human(record):
    if record.get("type") != "user" or record.get("isMeta") or record.get("isSidechain") \
            or record.get("isCompactSummary"):
        return False
    if not isinstance(record.get("message", {}).get("content"), str):
        return False
    origin = record.get("origin")
    return origin is None or (isinstance(origin, dict) and origin.get("kind") == "human")


def _is_interrupt_record(record):
    content = record.get("message", {}).get("content")
    if record.get("type") != "user" or not isinstance(content, list):
        return False
    return any(isinstance(b, dict) and b.get("type") == "text"
               and _INTERRUPT.match(b.get("text", "").strip()) for b in content)


def _rejection_text(record):
    """Return what the user typed when rejecting a tool call, or ''."""
    content = record.get("message", {}).get("content")
    if record.get("type") != "user" or record.get("isSidechain") or not isinstance(content, list):
        return ""
    for block in content:
        if not (isinstance(block, dict) and block.get("type") == "tool_result" and block.get("is_error")):
            continue
        body = block.get("content")
        if isinstance(body, list):
            body = "\n".join(b.get("text", "") for b in body if isinstance(b, dict))
        if not isinstance(body, str) or not body.startswith(_REJECTION_PREFIX) or _REJECTION_SAID not in body:
            continue
        typed = body.split(_REJECTION_SAID, 1)[1]
        lines = [ln for ln in typed.splitlines()
                 if ln.strip() and not ln.lstrip().startswith(">") and ln.strip() != "On selected text:"]
        return "\n".join(lines).strip()
    return ""


def _is_noise(text):
    return bool(_INTERRUPT.match(text) or text.startswith(_HARNESS_PREFIXES) or looks_like_pasted_log(text))


def _acceptable(text):
    return bool(text) and len(text) <= MAX_MESSAGE_CHARS and not _is_noise(text)


def _explicitly_human(record):
    origin = record.get("origin")
    return isinstance(origin, dict) and origin.get("kind") == "human"


def _signal_excerpt(text):
    """Keep only the sentences of a long message that carry a signal, capped in size."""
    picked = [s.strip()[:EXCERPT_SENTENCE_MAX] for s in _SENTENCE_SPLIT.split(text)
              if s.strip() and detect_signals(s)]
    return " … ".join(picked)[:MAX_MESSAGE_CHARS]


def extract_human_messages(path):
    """Yield {text, timestamp, session, project, origin, after_interrupt, prior_assistant} per message."""
    path = Path(path)
    prior = ""
    after_interrupt = False
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
            if _is_interrupt_record(rec):
                after_interrupt = True
                continue
            origin, text = "typed", ""
            rejected = _rejection_text(rec)
            if rejected:
                origin, text = "tool-rejection", _clean(rejected)
            elif _is_human(rec):
                text = _clean(rec["message"]["content"])
            else:
                continue
            flagged, after_interrupt = after_interrupt, False
            if not text or _is_noise(text):
                continue
            excerpt = False
            if len(text) > MAX_MESSAGE_CHARS:
                # Long text is only trusted as his when the harness marks it human, and then only
                # the sentences that carry a signal are kept (the rest is usually a brief or paste).
                if origin != "typed" or not _explicitly_human(rec):
                    continue
                text, excerpt = _signal_excerpt(text), True
                if not text:
                    continue
            yield {
                "text": text,
                "timestamp": rec.get("timestamp", ""),
                "session": path.name,
                "project": path.parent.name,
                "origin": origin,
                "after_interrupt": flagged,
                "excerpt": excerpt,
                "prior_assistant": prior[:PRIOR_ASSISTANT_MAX],
            }


def detect_signals(text):
    s = text.strip()
    signals = []
    if _SIGNALS["correction"].search(s) and not _NOT_CORRECTION.search(s) \
            and not ("¿" in s and s.endswith("?")):
        signals.append("correction")
    for name in ("rule", "guardrail"):
        if _SIGNALS[name].search(s):
            signals.append(name)
    return signals


def _norm(text):
    return re.sub(r"[\W_]+", " ", text.lower()).strip()


def _candidate_id(norm_text):
    return "c-" + hashlib.sha1(norm_text.encode()).hexdigest()[:8]


def _message_signals(msg):
    signals = detect_signals(msg["text"])
    if msg["origin"] == "tool-rejection":
        signals.append("rejection")
    if msg["after_interrupt"] and len(msg["text"]) >= MIN_INTERRUPT_REDIRECT_CHARS:
        signals.append("interrupt")
    return signals


def mine(root, since=None, handled=None):
    """Return deduplicated candidates under `root`, most-repeated first. `handled` = ids to skip."""
    handled = set(handled or ())
    groups = {}
    for path in sorted(Path(root).rglob("*.jsonl")):
        for msg in extract_human_messages(path):
            if since and msg["timestamp"][:10] < since:
                continue
            signals = _message_signals(msg)
            key = _norm(msg["text"])
            if not signals or not key or _candidate_id(key) in handled:
                continue
            group = groups.get(key)
            if group is None:
                groups[key] = {
                    "id": _candidate_id(key), "text": msg["text"], "signals": signals,
                    "prior_assistant": msg["prior_assistant"], "session": msg["session"],
                    "timestamp": msg["timestamp"], "occurrences": 1, "sessions": [msg["session"]],
                    "projects": [msg["project"]], "origin": msg["origin"], "excerpt": msg["excerpt"],
                }
                continue
            group["occurrences"] += 1
            for field, value in (("sessions", msg["session"]), ("projects", msg["project"])):
                if value not in group[field]:
                    group[field].append(value)
            group["signals"] = sorted(set(group["signals"]) | set(signals))
    return sorted(groups.values(), key=lambda c: (-c["occurrences"], c["timestamp"]))


def _load_handled(path):
    if not path:
        return set()
    try:
        return set(json.loads(Path(path).read_text()))
    except (OSError, json.JSONDecodeError):
        return set()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default=str(DEFAULT_ROOT), help="transcripts root (default ~/.claude/projects)")
    ap.add_argument("--since", help="YYYY-MM-DD lower bound")
    ap.add_argument("--limit", type=int, default=None, help="cap the output; omit for every candidate")
    ap.add_argument("--offset", type=int, default=0, help="skip this many candidates (page through in batches with --limit)")
    ap.add_argument("--handled", help="JSON file with a list of candidate ids already decided; they are skipped")
    args = ap.parse_args(argv)
    cands = mine(args.root, args.since, _load_handled(args.handled))
    end = None if args.limit is None else args.offset + args.limit
    for cand in cands[args.offset:end]:
        sys.stdout.write(json.dumps(cand, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Mine Claude Code transcripts for repeated *workflows* that could become skills. Read-only.

Looks at what the assistant actually ran at the top level of each session (Bash commands and
Skill calls; subagent work is skipped) and reports, across independent sessions:
- family:      the same kind of command (`ssh zeus`, `docker compose up`, `git push`)
- chain:       an ordered run of two or three families seen in several sessions
- skill-chain: an ordered pair of Skill calls seen in several sessions

Examples are redacted before they are printed. Nothing here edits any file.
"""
import argparse
import hashlib
import json
import re
import shlex
import sys
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mine_transcripts as mt  # noqa: E402

DEFAULT_ROOT = mt.DEFAULT_ROOT
MIN_SESSIONS = 3
MAX_EXAMPLES = 3
EXAMPLE_CHARS = 140
CHAIN_LENGTHS = (2, 3)
KIND_ORDER = {"family": 0, "chain": 1, "skill-chain": 2}

TRIVIAL = {
    "cd", "ls", "pwd", "echo", "cat", "head", "tail", "wc", "grep", "rg", "sed", "awk", "true", "false",
    "sleep", "export", "set", "test", "[", "printf", "which", "mkdir", "rm", "cp", "mv", "touch", "find",
    "tee", "sort", "uniq", "tr", "cut", "xargs", "date", "source", "exit", "read", "basename", "dirname",
    "jq", "open", "clear", "ps", "kill", "diff", "stat", "du", "df", "chmod", "ln", "less", "file",
}
WRAPPERS = {"sudo", "time", "nohup", "env", "command", "exec"}
# Shell grammar words that open a clause: the command that follows them is the real one.
CLAUSE_OPENERS = {"do", "then", "else", "if", "elif", "while", "until", "{", "(", "!"}
# Shell grammar words and code keywords that are never a command by themselves.
NOT_COMMANDS = {"for", "case", "in", "done", "fi", "esac", "function", "select",
                "}", ")", "break", "continue", "return", "import", "from", "def", "class", "print"}
_HEREDOC = re.compile(r"<<-?\s*(['\"]?)(\w+)\1[^\n]*\n.*?\n[ \t]*\2[ \t]*(?=\n|$)", re.S)
GIT_TRIVIAL = {"status", "diff", "log", "add", "show", "branch", "fetch", "remote", "rev-parse", "config",
               "ls-files", "blame", "describe", "tag"}
SUBCMD_TOOLS = {"make", "cargo", "go", "kubectl", "helm", "terraform", "brew", "launchctl", "systemctl",
                "supabase", "vercel", "gh", "npm", "pnpm", "yarn", "bun", "pip", "pip3", "uv", "poetry"}
SSH_OPTS_WITH_ARG = set("-o -i -p -l -F -J -L -R -D -c -b -E -e -S -W -w -B -m -O -Q".split())

_REDACTIONS = [
    (re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._\-]+"), "Bearer <redacted>"),
    (re.compile(r"(?i)((?:token|key|secret|passw(?:or)?d|pwd)(?:=|:\s*))\S+"), r"\1<redacted>"),
    (re.compile(r"\b(?:sk|ghp|gho|ghs|xox[abp])[-_][A-Za-z0-9\-_]{10,}"), "<redacted>"),
    (re.compile(r"\b[A-Za-z0-9+/_\-]{40,}\b"), "<redacted>"),
]
_ENV_ASSIGN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")


def redact(text):
    for pattern, replacement in _REDACTIONS:
        text = pattern.sub(replacement, text)
    return text


def _segments(cmd):
    """Split a shell command on && || ; | and newlines that are outside quotes."""
    out, buf, quote, i = [], [], None, 0
    while i < len(cmd):
        ch = cmd[i]
        if quote:
            buf.append(ch)
            if ch == quote:
                quote = None
            i += 1
        elif ch in "'\"":
            quote = ch
            buf.append(ch)
            i += 1
        elif cmd.startswith(("&&", "||"), i):
            out.append("".join(buf))
            buf = []
            i += 2
        elif ch in ";\n|":
            out.append("".join(buf))
            buf = []
            i += 1
        else:
            buf.append(ch)
            i += 1
    out.append("".join(buf))
    return [seg.strip() for seg in out if seg.strip()]


def _tokens(segment):
    try:
        tokens = shlex.split(segment)
    except ValueError:
        tokens = segment.split()
    while tokens and (tokens[0] in WRAPPERS or tokens[0] in CLAUSE_OPENERS or _ENV_ASSIGN.match(tokens[0])):
        if _ENV_ASSIGN.match(tokens[0]) and ("$(" in tokens[0] or "`" in tokens[0]):
            return []  # `VAR=$(cmd ...)`: an assignment, not a command of its own
        tokens = tokens[1:]
    if not tokens or tokens[0].startswith("#") or Path(tokens[0]).name in NOT_COMMANDS:
        return []
    return tokens


def _first_word(tokens):
    for token in tokens:
        if not token.startswith("-"):
            return token
    return ""


def _host_of(token):
    return token.split("@")[-1].split(":")[0]


def _ssh_family(tokens):
    skip = False
    for token in tokens[1:]:
        if skip:
            skip = False
        elif token in SSH_OPTS_WITH_ARG:
            skip = True
        elif not token.startswith("-"):
            return f"ssh {_host_of(token)}"
    return "ssh"


def _copy_family(tool, tokens):
    for token in tokens[1:]:
        if ":" in token and "://" not in token and not token.startswith("-"):
            return f"{tool} {_host_of(token)}"
    return tool


def _web_family(tool, tokens):
    for token in tokens[1:]:
        if re.match(r"https?://", token):
            return f"{tool} {urlparse(token).hostname or ''}".strip()
    return tool


def _script_family(tool, tokens, extensions):
    for token in tokens[1:]:
        if token.startswith("-"):
            if token == "-c":
                return None
            continue
        return f"{tool} {Path(token).name}" if token.endswith(extensions) else None
    return None


def _family_of(segment):
    tokens = _tokens(segment)
    if not tokens:
        return None
    tool = Path(tokens[0]).name
    if tool == "ssh":
        return _ssh_family(tokens)
    if tool in ("scp", "rsync", "sftp"):
        return _copy_family(tool, tokens)
    if tool in ("curl", "wget"):
        return _web_family(tool, tokens)
    if tool in ("python", "python3"):
        return _script_family("python3", tokens, (".py",))
    if tool == "node":
        return _script_family("node", tokens, (".js", ".mjs", ".cjs"))
    if tool in ("bash", "sh", "zsh"):
        return _script_family(tool, tokens, (".sh",))
    if tool == "docker":
        rest = [t for t in tokens[1:] if not t.startswith("-")]
        if rest[:1] == ["compose"]:
            return f"docker compose {rest[1]}" if len(rest) > 1 else "docker compose"
        return f"docker {rest[0]}" if rest else "docker"
    if tool == "git":
        rest = tokens[1:]
        if rest[:1] == ["-C"]:
            rest = rest[2:]
        sub = _first_word(rest)
        return None if not sub or sub in GIT_TRIVIAL else f"git {sub}"
    if tool in TRIVIAL:
        return None
    if tool in SUBCMD_TOOLS:
        rest = [t for t in tokens[1:] if not t.startswith("-")]
        if tool in ("npm", "pnpm", "yarn", "bun") and rest[:1] == ["run"] and len(rest) > 1:
            return f"{tool} run {rest[1]}"
        return f"{tool} {rest[0]}" if rest else tool
    return tool


def families(cmd):
    """Return the meaningful command families inside one shell command line, in order."""
    cmd = _HEREDOC.sub("", cmd)
    found = (_family_of(seg) for seg in _segments(cmd))
    return [f for f in found if f]


def _collapse(seq):
    return [x for i, x in enumerate(seq) if i == 0 or x != seq[i - 1]]


def _grams(seq):
    return {tuple(seq[i:i + n]) for n in CHAIN_LENGTHS for i in range(len(seq) - n + 1)}


def _contains(longer, shorter):
    n = len(shorter)
    return any(longer[i:i + n] == shorter for i in range(len(longer) - n + 1))


def _scan(path):
    """Yield (kind, name, example) for the top-level tool calls in one transcript."""
    with path.open(encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if '"tool_use"' not in line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if rec.get("type") != "assistant" or rec.get("isSidechain"):
                continue
            content = rec.get("message", {}).get("content")
            if not isinstance(content, list):
                continue
            for block in content:
                if not (isinstance(block, dict) and block.get("type") == "tool_use"):
                    continue
                if block.get("name") == "Bash":
                    cmd = block.get("input", {}).get("command", "")
                    for fam in families(cmd):
                        yield rec.get("timestamp", ""), "bash", fam, redact(cmd.strip().splitlines()[0])[:EXAMPLE_CHARS] if cmd.strip() else ""
                elif block.get("name") == "Skill":
                    name = block.get("input", {}).get("skill")
                    if isinstance(name, str) and name:
                        yield rec.get("timestamp", ""), "skill", name, ""


def _candidate(kind, signature, sessions, projects, examples):
    ident = "w-" + hashlib.sha1(f"{kind}:{signature}".encode()).hexdigest()[:8]
    return {"id": ident, "kind": kind, "signature": signature, "session_count": len(sessions),
            "sessions": sorted(sessions), "projects": sorted(projects), "examples": examples[:MAX_EXAMPLES]}


def mine(root, since=None, handled=None, min_sessions=MIN_SESSIONS):
    handled = set(handled or ())
    fam_sessions, fam_projects, fam_examples = {}, {}, {}
    gram_sessions, gram_projects = {}, {}
    skill_gram_sessions, skill_gram_projects = {}, {}
    for path in sorted(Path(root).rglob("*.jsonl")):
        if "subagents" in path.parts:
            continue
        project, key = path.parent.name, f"{path.parent.name}/{path.name}"
        bash_seq, skill_seq = [], []
        for ts, kind, name, example in _scan(path):
            if since and ts[:10] < since:
                continue
            if kind == "skill":
                skill_seq.append(name)
                continue
            bash_seq.append(name)
            fam_sessions.setdefault(name, set()).add(key)
            fam_projects.setdefault(name, set()).add(project)
            examples = fam_examples.setdefault(name, [])
            if example and example not in examples and len(examples) < MAX_EXAMPLES:
                examples.append(example)
        for gram in _grams(_collapse(bash_seq)):
            gram_sessions.setdefault(gram, set()).add(key)
            gram_projects.setdefault(gram, set()).add(project)
        for gram in _grams(_collapse(skill_seq)):
            if len(gram) == 2:
                skill_gram_sessions.setdefault(gram, set()).add(key)
                skill_gram_projects.setdefault(gram, set()).add(project)
    out = [_candidate("family", fam, s, fam_projects[fam], fam_examples[fam])
           for fam, s in fam_sessions.items() if len(s) >= min_sessions]
    strong = {g: s for g, s in gram_sessions.items() if len(s) >= min_sessions}
    for gram, sessions in strong.items():
        if any(len(other) > len(gram) and _contains(other, gram) and len(strong[other]) == len(sessions)
               for other in strong):
            continue
        out.append(_candidate("chain", " → ".join(gram), sessions, gram_projects[gram], []))
    for gram, sessions in skill_gram_sessions.items():
        if len(sessions) >= min_sessions:
            out.append(_candidate("skill-chain", " → ".join(gram), sessions, skill_gram_projects[gram], []))
    out = [c for c in out if c["id"] not in handled]
    return sorted(out, key=lambda c: (-c["session_count"], KIND_ORDER[c["kind"]], c["signature"]))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default=str(DEFAULT_ROOT))
    ap.add_argument("--since", help="YYYY-MM-DD lower bound")
    ap.add_argument("--min-sessions", type=int, default=MIN_SESSIONS)
    ap.add_argument("--handled", help="JSON file with candidate ids already decided; they are skipped")
    ap.add_argument("--offset", type=int, default=0)
    ap.add_argument("--limit", type=int, default=None, help="cap the output; omit for every candidate")
    args = ap.parse_args(argv)
    cands = mine(args.root, args.since, mt._load_handled(args.handled), args.min_sessions)
    end = None if args.limit is None else args.offset + args.limit
    for cand in cands[args.offset:end]:
        sys.stdout.write(json.dumps(cand, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()

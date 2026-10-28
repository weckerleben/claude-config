#!/usr/bin/env python3
"""Report which installed skills Claude actually used, from transcripts. Read-only.

A use is a `Skill` tool call (any session, subagents included) or a typed
`<command-name>/skill</command-name>`. Skills that were never used after a grace
period are *candidates* for pruning; this script never moves or deletes anything.

The idea (usage-based pruning with a grace period) comes from skill-miner;
the implementation is original.
"""
import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_ROOT = Path.home() / ".claude" / "projects"
DEFAULT_SKILLS = Path.home() / ".claude" / "skills"
DEFAULT_GRACE_DAYS = 14
_COMMAND = re.compile(r"<command-name>/?([^<\s]+)</command-name>")


def _names_in(record):
    """Yield skill names used in one transcript record."""
    content = record.get("message", {}).get("content")
    if record.get("type") == "assistant" and isinstance(content, list):
        for block in content:
            if isinstance(block, dict) and block.get("type") == "tool_use" and block.get("name") == "Skill":
                name = block.get("input", {}).get("skill")
                if isinstance(name, str) and name:
                    yield name
    elif record.get("type") == "user" and isinstance(content, str):
        yield from _COMMAND.findall(content)


def usage(root):
    """Return {skill_name: {count, last_used, sessions}} across all transcripts under root."""
    found = {}
    for path in sorted(Path(root).rglob("*.jsonl")):
        with path.open(encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if "Skill" not in line and "<command-name>" not in line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                for name in _names_in(rec):
                    entry = found.setdefault(name, {"count": 0, "last_used": "", "sessions": []})
                    entry["count"] += 1
                    entry["last_used"] = max(entry["last_used"], rec.get("timestamp", ""))
                    if path.name not in entry["sessions"]:
                        entry["sessions"].append(path.name)
    return found


def report(used, skills_dir, now=None, grace_days=DEFAULT_GRACE_DAYS):
    """Classify each locally installed skill as used / too-new / never. Never-used sort first."""
    now = now or datetime.now(timezone.utc)
    rows = []
    for skill_md in sorted(Path(skills_dir).glob("*/SKILL.md")):
        name = skill_md.parent.name
        age_days = (now.timestamp() - skill_md.stat().st_mtime) / 86400
        info = used.get(name)
        if info:
            status = "used"
        elif age_days < grace_days:
            status = "too-new"
        else:
            status = "never"
        rows.append({"name": name, "status": status, "count": info["count"] if info else 0,
                     "last_used": info["last_used"] if info else "", "age_days": round(age_days)})
    order = {"never": 0, "too-new": 1, "used": 2}
    return sorted(rows, key=lambda r: (order[r["status"]], -r["count"], r["name"]))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default=str(DEFAULT_ROOT))
    ap.add_argument("--skills-dir", default=str(DEFAULT_SKILLS))
    ap.add_argument("--grace-days", type=int, default=DEFAULT_GRACE_DAYS)
    args = ap.parse_args(argv)
    for row in report(usage(args.root), args.skills_dir, grace_days=args.grace_days):
        sys.stdout.write(json.dumps(row, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()

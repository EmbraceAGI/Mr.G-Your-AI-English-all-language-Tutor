#!/usr/bin/env python3
"""Find entries in vocab-template knowledge base.

Usage examples:
  python3 scripts/find_template_entry.py --word nostalgia
  python3 scripts/find_template_entry.py --word obstreperous --format markdown
  python3 scripts/find_template_entry.py --file words.txt
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

PAREN_RE = re.compile(r"^\s*([A-Za-z][A-Za-z\- ]*[A-Za-z])\s*\((.+)\)\s*$")
PIPE_RE = re.compile(r"^\s*-\s*([A-Za-z][A-Za-z\- ]*[A-Za-z])\s*\|\s*(.+)\s*$")


def parse_entries(path: Path) -> dict[str, dict[str, str]]:
    data: dict[str, dict[str, str]] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = PAREN_RE.match(line)
        if not m:
            m = PIPE_RE.match(line)
        if not m:
            continue
        word = " ".join(m.group(1).split())
        hint = " ".join(m.group(2).split())
        data[word.lower()] = {"word": word, "hint": hint}
    return data


def collect_queries(words: list[str], file_path: str | None) -> list[str]:
    queries = [w.strip() for w in words if w.strip()]
    if file_path:
        p = Path(file_path)
        if p.exists():
            for line in p.read_text(encoding="utf-8").splitlines():
                q = line.strip()
                if q:
                    queries.append(q)
    seen = set()
    out = []
    for q in queries:
        k = q.lower()
        if k in seen:
            continue
        seen.add(k)
        out.append(q)
    return out


def find_matches(entries: dict[str, dict[str, str]], query: str) -> dict[str, object]:
    q = query.lower().strip()
    exact = entries.get(q)
    fuzzy = []
    if not exact:
        for key, val in entries.items():
            if q in key or (len(q) >= 4 and key.startswith(q[:4])):
                fuzzy.append(val)
                if len(fuzzy) >= 5:
                    break
    return {
        "query": query,
        "exact": exact,
        "fuzzy": fuzzy,
    }


def format_markdown(results: list[dict[str, object]]) -> str:
    lines: list[str] = []
    for item in results:
        lines.append(f"## {item['query']}")
        exact = item.get("exact")
        if exact:
            lines.append(f"- exact: {exact['word']} ({exact['hint']})")
        else:
            lines.append("- exact: not found")
        fuzzy = item.get("fuzzy", [])
        if fuzzy:
            lines.append("- fuzzy:")
            for ent in fuzzy:
                lines.append(f"  - {ent['word']} ({ent['hint']})")
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Find entries in vocab-template.md")
    parser.add_argument("--kb", default="references/vocab-template.md", help="Path to vocab template")
    parser.add_argument("--word", action="append", default=[], help="Word query; can repeat")
    parser.add_argument("--file", help="File with one word per line")
    parser.add_argument("--format", choices=["json", "markdown"], default="json")
    args = parser.parse_args()

    kb = Path(args.kb)
    if not kb.exists():
        raise SystemExit(f"Knowledge base not found: {kb}")

    queries = collect_queries(args.word, args.file)
    if not queries:
        raise SystemExit("Provide at least one --word or --file")

    entries = parse_entries(kb)
    results = [find_matches(entries, q) for q in queries]

    if args.format == "json":
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        print(format_markdown(results), end="")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Manage learn-eng user profile, learning repos, card csv, and test mode.

Commands:
  init
  show-profile
  set-profile
  ingest
  test-mode
  mark-missed
  save-cards
"""

from __future__ import annotations

import argparse
import csv
import random
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


PROFILE_DEFAULTS = {
    "Learning Language": "English",
    "Level": "CEFR A1 (or equivalent)",
    "Exam Track": "Not set",
    "Exam Score": "Not set",
    "Learner Tier": "intermediate",
    "Goal": "Exam Prep",
    "Tone": "Encouraging",
    "Style": "Informative",
    "Explanation Mode": "English-first",
}

SESSION_DEFAULTS = {
    "First Use Completed": "no",
    "Initialized At": "",
    "Last Updated At": "",
    "Last Test Mode At": "-",
}

PHRASE_RE = re.compile(r"^[A-Za-z][A-Za-z'\- ]*[A-Za-z]$")
PROFILE_LINE_RE = re.compile(r"^-\s+([^:]+):\s*(.*)$")
CARD_VOCAB_RE = re.compile(r"\b(?:Vocabulary|Word)\s*:\s*(.+)$", re.IGNORECASE)
CARD_MNEMONIC_RE = re.compile(r"\bMnemonic\s*:\s*(.+)$", re.IGNORECASE)
INLINE_CARD_RE = re.compile(
    r"Vocabulary\s*:\s*([^,\n，]+)\s*[,，]\s*Mnemonic\s*:\s*([^\n]+)",
    re.IGNORECASE,
)
VOCAB_CSV_FIELDS = ["Vocabulary", "Mnemonic", "TestErrors", "LastUpdatedAt"]

VOCAB_MEANING_BANK: dict[str, str] = {
    "cosmology": "the scientific study of the origin and structure of the universe",
    "craven": "cowardly and lacking courage",
    "sycophancy": "insincere praise toward powerful people to gain advantage",
    "decorum": "proper and polite behavior in formal situations",
}


@dataclass
class RepoRow:
    key: str
    text: str
    added_at: str
    source: str
    seen: int
    misses: int
    last_reviewed: str
    notes: str


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def collapse_ws(text: str) -> str:
    return " ".join(text.strip().split())


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def normalize_exam_track(value: str) -> str:
    s = (value or "").strip().upper()
    if "TOEFL" in s:
        return "TOEFL"
    if "IELTS" in s:
        return "IELTS"
    if "CEFR" in s:
        return "CEFR"
    return "Not set"


def parse_score(value: str) -> float | None:
    if not value:
        return None
    m = re.search(r"\d+(?:\.\d+)?", value)
    if not m:
        return None
    try:
        return float(m.group(0))
    except Exception:
        return None


def extract_cefr(level_text: str) -> str | None:
    m = re.search(r"\b([ABC][12])\b", (level_text or "").upper())
    return m.group(1) if m else None


def apply_level_hints(profile: dict[str, str]) -> None:
    level = profile.get("Level", "")
    level_u = level.upper()

    if profile.get("Exam Track", "Not set") == "Not set":
        if "TOEFL" in level_u:
            profile["Exam Track"] = "TOEFL"
        elif "IELTS" in level_u:
            profile["Exam Track"] = "IELTS"
        elif "CEFR" in level_u or extract_cefr(level):
            profile["Exam Track"] = "CEFR"

    if profile.get("Exam Score", "Not set") in {"", "Not set", "NOT SET"}:
        score = parse_score(level)
        if score is not None:
            profile["Exam Score"] = str(score).rstrip("0").rstrip(".")


def infer_tier(profile: dict[str, str]) -> str:
    track = normalize_exam_track(profile.get("Exam Track", ""))
    score = parse_score(profile.get("Exam Score", ""))

    if track == "TOEFL" and score is not None:
        if score < 60:
            return "beginner"
        if score < 100:
            return "intermediate"
        return "advanced"

    if track == "IELTS" and score is not None:
        if score < 5.5:
            return "beginner"
        if score < 7:
            return "intermediate"
        return "advanced"

    cefr = extract_cefr(profile.get("Level", ""))
    if cefr:
        if cefr.startswith("A"):
            return "beginner"
        if cefr.startswith("B"):
            return "intermediate"
        return "advanced"

    return "intermediate"


def infer_explanation_mode(profile: dict[str, str]) -> str:
    style = (profile.get("Style", "") or "").lower()
    if any(x in style for x in ["bilingual", "中英"]):
        return "Bilingual (Chinese + English)"
    if any(x in style for x in ["english only", "纯英文", "全英文"]):
        return "English-first"

    track = normalize_exam_track(profile.get("Exam Track", ""))
    score = parse_score(profile.get("Exam Score", ""))

    if track == "TOEFL" and score is not None and score < 100:
        return "Bilingual (Chinese + English)"
    if track == "IELTS" and score is not None and score < 7:
        return "Bilingual (Chinese + English)"

    if profile.get("Learner Tier", "intermediate") == "beginner":
        return "Bilingual (Chinese + English)"

    return "English-first"


def user_defaults() -> tuple[dict[str, str], dict[str, str]]:
    profile = dict(PROFILE_DEFAULTS)
    session = dict(SESSION_DEFAULTS)
    ts = now_iso()
    session["Initialized At"] = ts
    session["Last Updated At"] = ts
    return profile, session


def write_user_md(path: Path, profile: dict[str, str], session: dict[str, str]) -> None:
    ensure_parent(path)
    lines = [
        "# User Profile",
        "",
        "First-time use rule:",
        "Ask user to provide profile settings. If omitted, keep defaults.",
        "",
        "## Profile",
    ]
    for key in [
        "Learning Language",
        "Level",
        "Exam Track",
        "Exam Score",
        "Learner Tier",
        "Goal",
        "Tone",
        "Style",
        "Explanation Mode",
    ]:
        lines.append(f"- {key}: {profile.get(key, PROFILE_DEFAULTS[key])}")
    lines.extend(
        [
            "",
            "## Session",
            f"- First Use Completed: {session.get('First Use Completed', 'no')}",
            f"- Initialized At: {session.get('Initialized At', now_iso())}",
            f"- Last Updated At: {session.get('Last Updated At', now_iso())}",
            f"- Last Test Mode At: {session.get('Last Test Mode At', '-')}",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def read_user_md(path: Path) -> tuple[dict[str, str], dict[str, str]]:
    if not path.exists():
        return user_defaults()

    profile, session = user_defaults()
    for raw in path.read_text(encoding="utf-8").splitlines():
        m = PROFILE_LINE_RE.match(raw.strip())
        if not m:
            continue
        key, value = m.group(1).strip(), m.group(2).strip()
        if key in profile:
            profile[key] = value
        elif key in session:
            session[key] = value

    apply_level_hints(profile)
    if profile.get("Learner Tier") in {"", "Not set", "NOT SET"}:
        profile["Learner Tier"] = infer_tier(profile)
    if profile.get("Explanation Mode") in {"", "Not set", "NOT SET"}:
        profile["Explanation Mode"] = infer_explanation_mode(profile)

    return profile, session


def ensure_repo(path: Path, kind: str) -> None:
    if path.exists():
        return
    ensure_parent(path)
    if kind == "vocab":
        title = "# Vocab Repo"
        desc = "Store difficult words/phrases captured from user input."
        header = "| Word/Phrase | Added At | Source | Seen | Misses | Last Reviewed | Notes |"
    else:
        title = "# Stenc Repo"
        desc = "Store difficult/long sentences or paragraph lines captured from user input."
        header = "| Sentence | Added At | Source | Seen | Misses | Last Reviewed | Notes |"

    lines = [
        title,
        "",
        desc,
        "",
        header,
        "| --- | --- | --- | --- | --- | --- | --- |",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def ensure_vocabs_csv(path: Path) -> None:
    if path.exists():
        return
    ensure_parent(path)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=VOCAB_CSV_FIELDS)
        writer.writeheader()


def ensure_state(
    user_path: Path,
    vocab_path: Path,
    stenc_path: Path,
    vocabs_csv_path: Path,
    quiet: bool,
) -> None:
    created: list[Path] = []
    if not user_path.exists():
        profile, session = user_defaults()
        write_user_md(user_path, profile, session)
        created.append(user_path)
    if not vocab_path.exists():
        ensure_repo(vocab_path, "vocab")
        created.append(vocab_path)
    if not stenc_path.exists():
        ensure_repo(stenc_path, "sentence")
        created.append(stenc_path)
    if not vocabs_csv_path.exists():
        ensure_vocabs_csv(vocabs_csv_path)
        created.append(vocabs_csv_path)

    if not quiet:
        if created:
            for p in created:
                print(f"initialized: {p}")
        else:
            print("already initialized")


def parse_repo(path: Path, kind: str) -> list[RepoRow]:
    ensure_repo(path, kind)
    rows: list[RepoRow] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.split("|")[1:-1]]
        if len(cells) < 7:
            continue
        if cells[0] in {"Word", "Word/Phrase", "Sentence", "---"}:
            continue

        text = cells[0].replace(r"\|", "|")
        key = text.lower() if kind == "vocab" else collapse_ws(text).lower()
        rows.append(
            RepoRow(
                key=key,
                text=text,
                added_at=cells[1],
                source=cells[2],
                seen=_to_int(cells[3]),
                misses=_to_int(cells[4]),
                last_reviewed=cells[5],
                notes=cells[6],
            )
        )
    return rows


def _to_int(value: str) -> int:
    try:
        return int(value)
    except Exception:
        return 0


def write_repo(path: Path, kind: str, rows: list[RepoRow]) -> None:
    if kind == "vocab":
        title = "# Vocab Repo"
        desc = "Store difficult words/phrases captured from user input."
        header = "| Word/Phrase | Added At | Source | Seen | Misses | Last Reviewed | Notes |"
    else:
        title = "# Stenc Repo"
        desc = "Store difficult/long sentences or paragraph lines captured from user input."
        header = "| Sentence | Added At | Source | Seen | Misses | Last Reviewed | Notes |"

    lines = [
        title,
        "",
        desc,
        "",
        header,
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]

    for row in rows:
        text = row.text.replace("|", r"\|")
        lines.append(
            f"| {text} | {row.added_at} | {row.source} | {row.seen} | {row.misses} | {row.last_reviewed} | {row.notes} |"
        )

    lines.append("")
    ensure_parent(path)
    path.write_text("\n".join(lines), encoding="utf-8")


def read_vocab_cards(path: Path) -> list[dict[str, str]]:
    ensure_vocabs_csv(path)
    rows: list[dict[str, str]] = []
    seen_idx: dict[str, int] = {}

    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            normalized = {field: (row.get(field, "") or "").strip() for field in VOCAB_CSV_FIELDS}
            normalized["Vocabulary"] = cleanup_card_value(normalized.get("Vocabulary", ""))
            normalized["Mnemonic"] = collapse_ws(normalized.get("Mnemonic", ""))

            if not normalized["Vocabulary"]:
                continue
            if not normalized["TestErrors"]:
                normalized["TestErrors"] = "0"
            if not normalized["LastUpdatedAt"]:
                normalized["LastUpdatedAt"] = "-"

            key = collapse_ws(normalized["Vocabulary"]).lower()
            if key not in seen_idx:
                seen_idx[key] = len(rows)
                rows.append(normalized)
                continue

            idx = seen_idx[key]
            existing = rows[idx]
            if not existing.get("Mnemonic") and normalized.get("Mnemonic"):
                existing["Mnemonic"] = normalized["Mnemonic"]
            existing_err = _to_int(existing.get("TestErrors", "0"))
            incoming_err = _to_int(normalized.get("TestErrors", "0"))
            if incoming_err > existing_err:
                existing["TestErrors"] = str(incoming_err)
                existing["LastUpdatedAt"] = normalized.get("LastUpdatedAt", existing.get("LastUpdatedAt", "-"))

    return rows

def write_vocab_cards(path: Path, rows: list[dict[str, str]]) -> None:
    ensure_parent(path)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=VOCAB_CSV_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in VOCAB_CSV_FIELDS})


def upsert_vocab_card(
    rows: list[dict[str, str]],
    vocab: str,
    mnemonic: str,
    updated_at: str,
    test_errors: int | None = None,
) -> bool:
    key = collapse_ws(vocab).lower()
    if not key:
        return False

    for row in rows:
        if collapse_ws(row.get("Vocabulary", "")).lower() != key:
            continue

        changed = False
        vocab_norm = collapse_ws(vocab)
        mnemonic_norm = collapse_ws(mnemonic)
        if row.get("Vocabulary", "") != vocab_norm:
            row["Vocabulary"] = vocab_norm
            changed = True
        if mnemonic_norm and row.get("Mnemonic", "") != mnemonic_norm:
            row["Mnemonic"] = mnemonic_norm
            changed = True
        if test_errors is not None and row.get("TestErrors", "0") != str(test_errors):
            row["TestErrors"] = str(test_errors)
            changed = True
        if changed:
            row["LastUpdatedAt"] = updated_at
        return changed

    rows.append(
        {
            "Vocabulary": collapse_ws(vocab),
            "Mnemonic": collapse_ws(mnemonic),
            "TestErrors": str(test_errors if test_errors is not None else 0),
            "LastUpdatedAt": updated_at,
        }
    )
    return True


def sync_vocab_csv_errors(
    csv_path: Path,
    vocab_rows: list[RepoRow],
    ts: str,
    create_missing: bool,
) -> None:
    cards = read_vocab_cards(csv_path)
    changed = False

    for row in vocab_rows:
        key = row.key
        match = None
        for c in cards:
            if collapse_ws(c.get("Vocabulary", "")).lower() == key:
                match = c
                break

        if match:
            misses = str(row.misses)
            if match.get("TestErrors", "0") != misses:
                match["TestErrors"] = misses
                match["LastUpdatedAt"] = ts
                changed = True
            continue

        if create_missing and row.misses > 0:
            cards.append(
                {
                    "Vocabulary": row.text,
                    "Mnemonic": "",
                    "TestErrors": str(row.misses),
                    "LastUpdatedAt": ts,
                }
            )
            changed = True

    if changed:
        write_vocab_cards(csv_path, cards)


def token_count(text: str) -> int:
    return len(re.findall(r"[A-Za-z][A-Za-z'\-]*", text))


def looks_vocab_phrase(text: str) -> bool:
    s = collapse_ws(text).strip('"\'“”')
    if not s:
        return False
    if any(p in s for p in ".?!"):
        return False
    if not PHRASE_RE.fullmatch(s):
        return False
    n = token_count(s)
    return 1 <= n <= 5


def split_line_candidates(line: str) -> list[str]:
    line = collapse_ws(line)
    if not line:
        return []

    if "," not in line and ";" not in line:
        return [line]

    parts = [p.strip() for p in re.split(r"[;,]", line) if p.strip()]
    out: list[str] = []
    sentence_parts: list[str] = []
    collecting_sentence = False

    for p in parts:
        if not collecting_sentence and looks_vocab_phrase(p):
            out.append(p)
        else:
            collecting_sentence = True
            sentence_parts.append(p)

    if sentence_parts:
        out.append(", ".join(sentence_parts))

    return out


def split_input_chunks(raw: str) -> list[str]:
    out: list[str] = []
    for line in raw.splitlines():
        out.extend(split_line_candidates(line))
    return out


def classify_item(item: str) -> str:
    s = collapse_ws(item).strip('"\'“”')
    if looks_vocab_phrase(s):
        return "vocab"
    return "sentence"


def collect_inputs(args: argparse.Namespace) -> list[str]:
    blocks: list[str] = []
    for x in args.input or []:
        if x.strip():
            blocks.append(x)
    if args.file:
        p = Path(args.file)
        if p.exists():
            blocks.append(p.read_text(encoding="utf-8"))
    text = "\n".join(blocks)
    return split_input_chunks(text)


def collect_raw_text(args: argparse.Namespace) -> str:
    blocks: list[str] = []
    for x in args.input or []:
        if x.strip():
            blocks.append(x)
    if args.file:
        p = Path(args.file)
        if p.exists():
            blocks.append(p.read_text(encoding="utf-8"))
    return "\n".join(blocks)


def cleanup_card_value(value: str) -> str:
    s = value.strip()
    s = s.strip("`")
    s = s.strip("*")
    s = s.strip("`")
    s = re.sub(r"^[\-\*\d\.\)\s]+", "", s)
    s = re.sub(r"[,，;；:\.。]+$", "", s)
    return collapse_ws(s)


def card_key(vocab: str, mnemonic: str) -> tuple[str, str]:
    return (collapse_ws(vocab).lower(), collapse_ws(mnemonic).lower())


def extract_vocab_cards(raw: str) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    pending_vocab = ""

    for line_raw in raw.splitlines():
        line = collapse_ws(line_raw)
        if not line:
            continue

        vocab_match = CARD_VOCAB_RE.search(line)
        mnemonic_match = CARD_MNEMONIC_RE.search(line)

        if vocab_match:
            vocab = cleanup_card_value(vocab_match.group(1))
            if "Mnemonic:" in vocab:
                vocab = cleanup_card_value(vocab.split("Mnemonic:", 1)[0])
            pending_vocab = vocab

            if mnemonic_match and pending_vocab:
                mnemonic = cleanup_card_value(mnemonic_match.group(1))
                key = card_key(pending_vocab, mnemonic)
                if pending_vocab and mnemonic and key not in seen:
                    pairs.append((pending_vocab, mnemonic))
                    seen.add(key)
                pending_vocab = ""
            continue

        if mnemonic_match and pending_vocab:
            mnemonic = cleanup_card_value(mnemonic_match.group(1))
            key = card_key(pending_vocab, mnemonic)
            if pending_vocab and mnemonic and key not in seen:
                pairs.append((pending_vocab, mnemonic))
                seen.add(key)
            pending_vocab = ""

    for m in INLINE_CARD_RE.finditer(raw):
        vocab = cleanup_card_value(m.group(1))
        mnemonic = cleanup_card_value(m.group(2))
        key = card_key(vocab, mnemonic)
        if vocab and mnemonic and key not in seen:
            pairs.append((vocab, mnemonic))
            seen.add(key)

    return pairs

def pick_function_target(sentence: str) -> str:
    text = collapse_ws(sentence)

    patterns = [
        r"\b(that|which|who|whom|whose)\b[^,.;!?]*",
        r"\bto\s+[A-Za-z][^,.;!?]*",
        r"\b(in|on|at|with|for|among|between|of)\b[^,.;!?]*",
    ]
    for pattern in patterns:
        m = re.search(pattern, text, flags=re.IGNORECASE)
        if m:
            chunk = collapse_ws(m.group(0))
            # Keep function target focused; avoid swallowing long coordinated tails.
            chunk = re.split(r"\s+(?:or|and)\s+among\b", chunk, maxsplit=1, flags=re.IGNORECASE)[0]
            words = chunk.split()
            if len(words) > 14:
                chunk = " ".join(words[:14])
            if len(chunk.split()) >= 2:
                return chunk

    words = text.split()
    if not words:
        return sentence
    return " ".join(words[: min(10, len(words))])


def option_lines(options: list[str]) -> list[str]:
    labels = "ABCD"
    out: list[str] = []
    for i, opt in enumerate(options):
        out.append(f"   {labels[i]}. {opt}")
    return out


def build_vocab_meaning_options(word: str, rng: random.Random) -> list[str]:
    key = collapse_ws(word).lower()
    correct = VOCAB_MEANING_BANK.get(key, f"[Correct meaning of {word}]")

    wrong_pool = [
        "an opposite meaning",
        "an unrelated technical concept",
        "a social behavior term with different meaning",
        "a literal but incorrect interpretation",
    ]
    rng.shuffle(wrong_pool)
    options = [correct, wrong_pool[0], wrong_pool[1]]
    rng.shuffle(options)
    return options



def build_sentence_meaning_options(sentence: str) -> list[str]:
    text = collapse_ws(sentence)
    if re.search(r"\bno evidence\b", text, flags=re.IGNORECASE):
        return [
            "Researchers did not find evidence for the claimed seasonal breeding pattern.",
            "Researchers proved seasonal breeding is universal in these species.",
            "Researchers compared algae blooms across all oceans and confirmed causation.",
        ]
    return [
        "This option captures the sentence's main claim.",
        "This option distorts the main claim by changing polarity.",
        "This option is largely unrelated to the sentence focus.",
    ]


def build_function_options(target: str) -> list[str]:
    low = target.lower()
    if re.match(r"^(that|which|who|whom|whose)\b", low):
        return [
            "A relative clause that modifies a noun phrase.",
            "The sentence's main predicate.",
            "An independent conclusion clause.",
        ]
    if re.match(r"^to\b", low):
        return [
            "An infinitive phrase expressing purpose/result.",
            "A finite verb that serves as the main predicate.",
            "A discourse marker introducing contrast.",
        ]
    if re.match(r"^(in|on|at|with|for|among|between|of)\b", low):
        return [
            "A prepositional phrase adding context/restriction.",
            "A subject complement defining identity.",
            "A sentence-level coordinator connecting clauses.",
        ]
    return [
        "A modifier phrase adding extra information.",
        "The main clause subject.",
        "A standalone independent clause.",
    ]


def build_sentence_detail_prompt(sentence: str) -> tuple[str, list[str]]:
    text = collapse_ws(sentence)
    m = re.search(r"no evidence of\s+(.+?)(?:\s+among\b|[.,;]|$)", text, flags=re.IGNORECASE)
    if m:
        focus = collapse_ws(m.group(1))
        return (
            "Detail check: no evidence of what exactly?",
            [
                focus,
                "rapid yearly migration",
                "increased predator density",
            ],
        )

    m2 = re.search(r"with\s+(no|not)\s+([^.,;]+)", text, flags=re.IGNORECASE)
    if m2:
        cond = collapse_ws(f"{m2.group(1)} {m2.group(2)}")
        return (
            "Detail check: which condition is explicitly mentioned?",
            [
                cond,
                "abundant seasonal nutrients",
                "stable shallow-water habitat",
            ],
        )

    return (
        "Detail check: which statement is explicitly supported by the sentence?",
        [
            "The sentence makes a constrained claim with specific qualifiers.",
            "The sentence gives a broad universal law with no qualifiers.",
            "The sentence focuses on policy recommendations.",
        ],
    )


def cmd_init(args: argparse.Namespace) -> None:
    ensure_state(
        Path(args.user),
        Path(args.vocab_repo),
        Path(args.stenc_repo),
        Path(args.vocabs_csv),
        quiet=False,
    )


def cmd_show_profile(args: argparse.Namespace) -> None:
    user_path = Path(args.user)
    ensure_state(
        user_path,
        Path(args.vocab_repo),
        Path(args.stenc_repo),
        Path(args.vocabs_csv),
        quiet=True,
    )
    profile, session = read_user_md(user_path)
    for k in [
        "Learning Language",
        "Level",
        "Exam Track",
        "Exam Score",
        "Learner Tier",
        "Goal",
        "Tone",
        "Style",
        "Explanation Mode",
    ]:
        print(f"{k}: {profile[k]}")
    for k in ["First Use Completed", "Initialized At", "Last Updated At", "Last Test Mode At"]:
        print(f"{k}: {session[k]}")


def cmd_set_profile(args: argparse.Namespace) -> None:
    user_path = Path(args.user)
    ensure_state(
        user_path,
        Path(args.vocab_repo),
        Path(args.stenc_repo),
        Path(args.vocabs_csv),
        quiet=True,
    )
    profile, session = read_user_md(user_path)

    mapping = {
        "language": "Learning Language",
        "level": "Level",
        "tier": "Learner Tier",
        "exam": "Exam Track",
        "score": "Exam Score",
        "goal": "Goal",
        "tone": "Tone",
        "style": "Style",
    }
    for arg_key, profile_key in mapping.items():
        value = getattr(args, arg_key)
        if value:
            profile[profile_key] = value.strip()

    profile["Exam Track"] = normalize_exam_track(profile.get("Exam Track", ""))
    apply_level_hints(profile)

    if not args.tier:
        profile["Learner Tier"] = infer_tier(profile)
    profile["Explanation Mode"] = infer_explanation_mode(profile)

    session["First Use Completed"] = "yes"
    session["Last Updated At"] = now_iso()
    write_user_md(user_path, profile, session)
    print(f"updated: {user_path}")


def cmd_ingest(args: argparse.Namespace) -> None:
    user_path = Path(args.user)
    vocab_path = Path(args.vocab_repo)
    stenc_path = Path(args.stenc_repo)
    vocabs_csv_path = Path(args.vocabs_csv)
    ensure_state(user_path, vocab_path, stenc_path, vocabs_csv_path, quiet=True)

    vocab_rows = parse_repo(vocab_path, "vocab")
    stenc_rows = parse_repo(stenc_path, "sentence")
    vocab_map = {r.key: r for r in vocab_rows}
    stenc_map = {r.key: r for r in stenc_rows}

    items = collect_inputs(args)
    if not items:
        raise SystemExit("No input provided. Use --input or --file.")

    added_vocab = 0
    added_sentence = 0
    ts = now_iso()

    for raw in items:
        text = collapse_ws(raw).strip('"\'“”')
        if not text:
            continue
        kind = classify_item(text)
        if kind == "vocab":
            key = text.lower()
            if key in vocab_map:
                continue
            row = RepoRow(key=key, text=text, added_at=ts, source=args.source, seen=0, misses=0, last_reviewed="-", notes="")
            vocab_rows.append(row)
            vocab_map[key] = row
            added_vocab += 1
        else:
            key = collapse_ws(text).lower()
            if key in stenc_map:
                continue
            row = RepoRow(key=key, text=text, added_at=ts, source=args.source, seen=0, misses=0, last_reviewed="-", notes="")
            stenc_rows.append(row)
            stenc_map[key] = row
            added_sentence += 1

    if args.dry_run:
        print(f"dry-run: +{added_vocab} vocab, +{added_sentence} sentences")
        return

    write_repo(vocab_path, "vocab", vocab_rows)
    write_repo(stenc_path, "sentence", stenc_rows)

    profile, session = read_user_md(user_path)
    session["Last Updated At"] = ts
    write_user_md(user_path, profile, session)

    print(f"ingested: +{added_vocab} vocab, +{added_sentence} sentences")


def select_for_test(rows: list[RepoRow], count: int, rng: random.Random) -> list[RepoRow]:
    if count <= 0 or not rows:
        return []

    ordered = sorted(
        rows,
        key=lambda r: (
            -r.misses,
            r.seen,
            "" if r.last_reviewed in {"", "-"} else r.last_reviewed,
            r.added_at,
        ),
    )
    pool = ordered[: max(count * 3, count)]
    rng.shuffle(pool)
    return pool[:count]


def cmd_test_mode(args: argparse.Namespace) -> None:
    user_path = Path(args.user)
    vocab_path = Path(args.vocab_repo)
    stenc_path = Path(args.stenc_repo)
    vocabs_csv_path = Path(args.vocabs_csv)
    ensure_state(user_path, vocab_path, stenc_path, vocabs_csv_path, quiet=True)

    vocab_rows = parse_repo(vocab_path, "vocab")
    stenc_rows = parse_repo(stenc_path, "sentence")

    rng = random.Random(args.seed)
    picked_vocab = select_for_test(vocab_rows, args.vocab_count, rng)
    picked_stenc = select_for_test(stenc_rows, args.sentence_count, rng)

    lines = ["# Test Mode (Multiple Choice)", ""]

    q_index = 1
    if picked_vocab:
        lines.append("## Vocabulary MCQ")
        for row in picked_vocab:
            lines.append(f"{q_index}. For `{row.text}`, choose the closest meaning.")
            lines.extend(option_lines(build_vocab_meaning_options(row.text, rng)))
            q_index += 1
        lines.append("")

    if picked_stenc:
        lines.append("## Sentence MCQ")
        for s_idx, row in enumerate(picked_stenc, 1):
            target = pick_function_target(row.text)
            detail_prompt, detail_options = build_sentence_detail_prompt(row.text)

            lines.append(f"Sentence {s_idx} (original):")
            lines.append(f"{row.text}")
            lines.append("")

            lines.append(f"{q_index}. Sentence meaning: what does this sentence mainly say?")
            lines.extend(option_lines(build_sentence_meaning_options(row.text)))
            q_index += 1

            lines.append(f"{q_index}. Function: what is the role of `{target}` in this sentence?")
            lines.extend(option_lines(build_function_options(target)))
            q_index += 1

            lines.append(f"{q_index}. {detail_prompt}")
            lines.extend(option_lines(detail_options))
            q_index += 1
            lines.append("")

    if not picked_vocab and not picked_stenc:
        lines.append("No items found in repos. Ingest words/sentences first.")
        lines.append("")

    lines.append("Answer format:")
    lines.append("- Single-choice: 1A 3C ...")
    lines.append("Use `mark-missed` after checking answers to increase misses for weak items.")
    print("\n".join(lines).strip() + "\n")

    if args.dry_run:
        return

    ts = now_iso()
    vocab_keys = {r.key for r in picked_vocab}
    stenc_keys = {r.key for r in picked_stenc}

    for row in vocab_rows:
        if row.key in vocab_keys:
            row.seen += 1
            row.last_reviewed = ts

    for row in stenc_rows:
        if row.key in stenc_keys:
            row.seen += 1
            row.last_reviewed = ts

    write_repo(vocab_path, "vocab", vocab_rows)
    write_repo(stenc_path, "sentence", stenc_rows)
    sync_vocab_csv_errors(vocabs_csv_path, vocab_rows, ts=ts, create_missing=False)

    profile, session = read_user_md(user_path)
    session["Last Updated At"] = ts
    session["Last Test Mode At"] = ts
    write_user_md(user_path, profile, session)


def cmd_mark_missed(args: argparse.Namespace) -> None:
    user_path = Path(args.user)
    vocab_path = Path(args.vocab_repo)
    stenc_path = Path(args.stenc_repo)
    vocabs_csv_path = Path(args.vocabs_csv)
    ensure_state(user_path, vocab_path, stenc_path, vocabs_csv_path, quiet=True)

    vocab_rows = parse_repo(vocab_path, "vocab")
    stenc_rows = parse_repo(stenc_path, "sentence")

    vocab_map = {r.key: r for r in vocab_rows}
    stenc_map = {r.key: r for r in stenc_rows}

    ts = now_iso()
    hit_vocab = 0
    hit_stenc = 0

    for w in args.word or []:
        key = collapse_ws(w).lower()
        row = vocab_map.get(key)
        if row:
            row.misses += 1
            row.last_reviewed = ts
            hit_vocab += 1

    for s in args.sentence or []:
        key = collapse_ws(s).lower()
        row = stenc_map.get(key)
        if row:
            row.misses += 1
            row.last_reviewed = ts
            hit_stenc += 1

    write_repo(vocab_path, "vocab", vocab_rows)
    write_repo(stenc_path, "sentence", stenc_rows)
    sync_vocab_csv_errors(vocabs_csv_path, vocab_rows, ts=ts, create_missing=True)

    profile, session = read_user_md(user_path)
    session["Last Updated At"] = ts
    write_user_md(user_path, profile, session)

    print(f"updated misses: vocab={hit_vocab}, sentence={hit_stenc}")


def cmd_save_cards(args: argparse.Namespace) -> None:
    user_path = Path(args.user)
    vocab_path = Path(args.vocab_repo)
    stenc_path = Path(args.stenc_repo)
    vocabs_csv_path = Path(args.vocabs_csv)
    ensure_state(user_path, vocab_path, stenc_path, vocabs_csv_path, quiet=True)

    raw = collect_raw_text(args)
    if not raw.strip():
        raise SystemExit("No card text provided. Use --input or --file.")

    pairs = extract_vocab_cards(raw)
    if not pairs:
        raise SystemExit("No Vocabulary/Mnemonic pair found.")

    vocab_rows = parse_repo(vocab_path, "vocab")
    vocab_map = {r.key: r for r in vocab_rows}

    cards = read_vocab_cards(vocabs_csv_path)
    ts = now_iso()
    changed = 0

    for vocab, mnemonic in pairs:
        key = collapse_ws(vocab).lower()
        misses = vocab_map.get(key).misses if key in vocab_map else 0
        if upsert_vocab_card(cards, vocab, mnemonic, updated_at=ts, test_errors=misses):
            changed += 1

    if args.dry_run:
        print(f"dry-run: extracted={len(pairs)}, changed={changed}")
        return

    write_vocab_cards(vocabs_csv_path, cards)

    profile, session = read_user_md(user_path)
    session["Last Updated At"] = ts
    write_user_md(user_path, profile, session)

    print(f"saved cards: extracted={len(pairs)}, changed={changed}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="learn-eng profile/repo/test-mode manager")
    parser.add_argument("--user", default="user.md", help="Path to user profile markdown")
    parser.add_argument("--vocab-repo", default="vocab-repo.md", help="Path to vocab repo markdown")
    parser.add_argument("--stenc-repo", default="stenc-repo.md", help="Path to sentence repo markdown")
    parser.add_argument("--vocabs-csv", default="vocabs.csv", help="Path to vocab card csv")

    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init", help="Initialize user/profile and repo files")
    sub.add_parser("show-profile", help="Print current profile")

    set_profile = sub.add_parser("set-profile", help="Update profile values")
    set_profile.add_argument("--language")
    set_profile.add_argument("--level")
    set_profile.add_argument("--tier", choices=["beginner", "intermediate", "advanced"])
    set_profile.add_argument("--exam")
    set_profile.add_argument("--score")
    set_profile.add_argument("--goal")
    set_profile.add_argument("--tone")
    set_profile.add_argument("--style")

    ingest = sub.add_parser("ingest", help="Auto-classify user input and append repos")
    ingest.add_argument("--input", action="append", default=[], help="Raw user input; can repeat")
    ingest.add_argument("--file", help="Text file containing raw input")
    ingest.add_argument("--source", default="user-input", help="Source tag")
    ingest.add_argument("--dry-run", action="store_true")

    test_mode = sub.add_parser("test-mode", help="Generate MCQ quiz from repos")
    test_mode.add_argument("--vocab-count", type=int, default=5)
    test_mode.add_argument("--sentence-count", type=int, default=3)
    test_mode.add_argument("--seed", type=int, default=42)
    test_mode.add_argument("--dry-run", action="store_true")

    mark = sub.add_parser("mark-missed", help="Mark missed items to drive iterative learning")
    mark.add_argument("--word", action="append", default=[])
    mark.add_argument("--sentence", action="append", default=[])

    save_cards = sub.add_parser("save-cards", help="Extract Vocabulary+Mnemonic pairs into vocabs.csv")
    save_cards.add_argument("--input", action="append", default=[], help="Card text block; can repeat")
    save_cards.add_argument("--file", help="Markdown/text file that contains card output")
    save_cards.add_argument("--dry-run", action="store_true")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "init":
        cmd_init(args)
    elif args.command == "show-profile":
        cmd_show_profile(args)
    elif args.command == "set-profile":
        cmd_set_profile(args)
    elif args.command == "ingest":
        cmd_ingest(args)
    elif args.command == "test-mode":
        cmd_test_mode(args)
    elif args.command == "mark-missed":
        cmd_mark_missed(args)
    elif args.command == "save-cards":
        cmd_save_cards(args)
    else:
        raise SystemExit(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    main()

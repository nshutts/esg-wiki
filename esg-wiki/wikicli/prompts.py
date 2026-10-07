"""Prompt assembly. The model never reads project files itself; this module
loads the instruction files and packs retrieved passages into the message."""
from __future__ import annotations

import re
from pathlib import Path

from .retrieval import Hit


def load_instructions(root: Path, name: str) -> str:
    """Load persona.md / wiki-instructions.md / ingest-instructions.md.

    The first heading and the note to human readers directly under it are
    skipped; everything from the first '## ' section or rule list onward is sent.
    """
    path = root / name
    if not path.exists():
        raise FileNotFoundError(f"Missing instruction file: {path}")
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    # drop "# Title" and the following "These ... are loaded ..." paragraph
    if lines and lines[0].startswith("# "):
        lines = lines[1:]
        while lines and not lines[0].strip():
            lines = lines[1:]
        if lines and re.match(r"^These (rules|instructions)", lines[0]):
            while lines and lines[0].strip():
                lines = lines[1:]
    return "\n".join(lines).strip()


def format_passages(hits: list[Hit]) -> str:
    blocks = []
    for n, h in enumerate(hits, start=1):
        p = h.passage
        label = "wiki note (generated summary)" if p.kind == "wiki" else "source"
        loc = f", {p.location}" if p.location else ""
        blocks.append(f"[{n}] {p.title}{loc} ({label})\n{p.text}")
    return "\n\n".join(blocks)


def ask_messages(system: str, question: str, hits: list[Hit]) -> list[dict]:
    user = (
        "Source passages:\n\n" + format_passages(hits) +
        f"\n\nQuestion: {question}\n\n"
        "Answer from the passages only, with [n] citations. If they do not answer the "
        "question, reply with a line starting INSUFFICIENT EVIDENCE:"
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def word_count(text: str) -> int:
    return len(text.split())

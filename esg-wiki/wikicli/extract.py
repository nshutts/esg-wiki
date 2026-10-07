"""Turn source files into clean, located text passages.

Reading never modifies the file in vault/raw/. Each passage keeps its source ID,
file path, page numbers (PDF) or table row (DOCX), and section heading so
citations can point back to the exact place in the original.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

SUPPORTED = {".pdf", ".docx", ".md", ".txt"}


@dataclass
class Line:
    text: str
    page: int | None = None


@dataclass
class Passage:
    id: str
    source_id: str
    kind: str                 # "source" (original evidence) or "wiki" (generated note)
    path: str                 # path relative to the project root
    title: str                # source title or note title
    section: str
    pages: list = field(default_factory=list)
    text: str = ""

    @property
    def location(self) -> str:
        if self.pages:
            ps = sorted(set(self.pages))
            loc = f"p.{ps[0]}" if len(ps) == 1 else f"pp.{ps[0]}-{ps[-1]}"
        else:
            loc = ""
        sec = f'"{self.section}"' if self.section else ""
        return ", ".join(x for x in [loc, sec] if x)

    def to_dict(self) -> dict:
        return asdict(self)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(65536), b""):
            h.update(block)
    return h.hexdigest()


# --------------------------------------------------------------------------
# Readers
# --------------------------------------------------------------------------

def read_pdf(path: Path) -> list[Line]:
    try:
        import pymupdf  # PyMuPDF: local, no network, good text order
    except ImportError:  # older PyMuPDF versions
        import fitz as pymupdf
    lines: list[Line] = []
    with pymupdf.open(str(path)) as doc:
        for i, page in enumerate(doc, start=1):
            for t in page.get_text().splitlines():
                t = t.replace("​", "").strip()
                if t:
                    lines.append(Line(t, i))
    return lines


def read_docx(path: Path) -> tuple[list[Line], list[dict]]:
    """Return paragraph lines plus table rows (each row as {header: value})."""
    import docx
    d = docx.Document(str(path))
    lines: list[Line] = []
    rows: list[dict] = []
    body = d.element.body
    for child in body.iterchildren():
        tag = child.tag.rsplit("}", 1)[-1]
        if tag == "p":
            text = "".join(n.text or "" for n in child.iter() if n.tag.endswith("}t")).strip()
            if text:
                lines.append(Line(text))
        elif tag == "tbl":
            table = docx.table.Table(child, d)
            header = [c.text.strip() for c in table.rows[0].cells]
            for r in table.rows[1:]:
                cells = [c.text.strip() for c in r.cells]
                rows.append(dict(zip(header, cells)))
    return lines, rows


def read_text(path: Path) -> list[Line]:
    return [Line(t.rstrip()) for t in path.read_text(encoding="utf-8").splitlines() if t.strip()]


# --------------------------------------------------------------------------
# Cleaning (per-source rules from config/sources.yaml)
# --------------------------------------------------------------------------

def clean_lines(lines: list[Line], rules: dict | None) -> list[Line]:
    rules = rules or {}
    out = list(lines)
    for start, end in rules.get("drop_blocks", []):
        s_re = re.compile(start)
        e_re = None if end == "END" else re.compile(end)
        kept, dropping = [], False
        for ln in out:
            if not dropping and s_re.search(ln.text):
                dropping = True
                continue
            if dropping and e_re is not None and e_re.search(ln.text):
                dropping = False
            if not dropping:
                kept.append(ln)
        out = kept
    pats = [re.compile(p) for p in rules.get("drop_line_patterns", [])]
    out = [ln for ln in out if not any(p.search(ln.text) for p in pats)]
    return out


# --------------------------------------------------------------------------
# Sectioning and chunking
# --------------------------------------------------------------------------

SENT_END = re.compile(r"[.!?:;)\"”’]$")
NUMBERED = re.compile(r"^(\d{1,2})\.\s+(.+?)\.\s")        # "4. Corporate ... (CSRD) and ESRS. The EU's..."


def is_heading(line: str, prev: str | None) -> bool:
    if NUMBERED.match(line + " "):
        return True
    if len(line) > 60 or line.endswith(","):
        return False
    if SENT_END.search(line) and not line.endswith("?"):   # "What Are ESG Standards?" is a heading
        return False
    if not line[0].isupper() and not line[0].isdigit():
        return False
    # A short line that follows a finished sentence (or starts the document)
    # is a heading; a short line after an unfinished one is just a wrapped line.
    return prev is None or bool(SENT_END.search(prev))


def section_title(line: str) -> str:
    m = NUMBERED.match(line + " ")
    return f"{m.group(1)}. {m.group(2)}" if m else line


def join_lines(lines: list[Line]) -> tuple[str, list[tuple[int, int | None]]]:
    """Join wrapped lines into one string and remember where each line starts."""
    text, offsets = "", []
    for ln in lines:
        t = re.sub(r"\s+", " ", ln.text).strip()
        if not text:
            offsets.append((0, ln.page))
            text = t
        elif text.endswith("-") and t[:1].islower():
            offsets.append((len(text), ln.page))
            text += t                      # keep hyphenated compounds together
        else:
            offsets.append((len(text) + 1, ln.page))
            text += " " + t
    return text, offsets


SENT_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"“(])")


def split_sentences(text: str) -> list[str]:
    return [s for s in SENT_SPLIT.split(text) if s.strip()]


def pages_for_span(start: int, end: int, offsets: list[tuple[int, int | None]]) -> set:
    pages = set()
    for i, (off, page) in enumerate(offsets):
        nxt = offsets[i + 1][0] if i + 1 < len(offsets) else 10**12
        if off < end and nxt > start and page is not None:
            pages.add(page)
    return pages


def chunk_section(lines: list[Line], target: int, maximum: int, minimum: int) -> list[tuple[str, list[int]]]:
    """Split a section into passages near `target` words at sentence boundaries,
    keeping the page numbers each passage came from."""
    full, offsets = join_lines(lines)
    pieces: list[tuple[str, set]] = []
    pos = 0
    for s in split_sentences(full):
        start = full.find(s, pos)
        end = start + len(s)
        pos = end
        pieces.append((s, pages_for_span(start, end, offsets)))

    total = sum(len(s.split()) for s, _ in pieces)
    if total <= maximum:                     # short sections stay whole
        pages = sorted(set().union(*[pg for _, pg in pieces])) if pieces else []
        return [(" ".join(s for s, _ in pieces), pages)] if pieces else []

    chunks: list[tuple[str, list[int]]] = []
    cur, cur_pages, n = [], set(), 0
    for s, pg in pieces:
        w = len(s.split())
        if cur and (n + w > maximum or n >= target):
            chunks.append((" ".join(cur), sorted(cur_pages)))
            cur, cur_pages, n = [], set(), 0
        cur.append(s)
        cur_pages |= pg
        n += w
    if cur:
        if chunks and n < minimum:
            prev_text, prev_pages = chunks.pop()
            chunks.append((prev_text + " " + " ".join(cur), sorted(set(prev_pages) | cur_pages)))
        else:
            chunks.append((" ".join(cur), sorted(cur_pages)))
    return chunks


def passages_from_lines(lines: list[Line], source: dict, rel_path: str, kind: str,
                        chunking: dict, default_section: str = "") -> list[Passage]:
    sections: list[tuple[str, list[Line]]] = []
    current_title: str = default_section
    current: list[Line] = []
    prev = None
    for ln in lines:
        if is_heading(ln.text, prev):
            if current:
                sections.append((current_title, current))
            numbered = NUMBERED.match(ln.text + " ")
            current_title = section_title(ln.text)
            # A numbered heading line also carries body text; keep it.
            current = [ln] if numbered else []
        else:
            current.append(ln)
        prev = ln.text
    if current:
        sections.append((current_title, current))

    out: list[Passage] = []
    for si, (title, sec_lines) in enumerate(sections, start=1):
        for ci, (text, pages) in enumerate(
                chunk_section(sec_lines, chunking["target_words"], chunking["max_words"], chunking["min_words"]),
                start=1):
            out.append(Passage(
                id=f"{source['id']}:s{si:02d}c{ci}", source_id=source["id"], kind=kind,
                path=rel_path, title=source["title"], section=title, pages=pages, text=text))
    return out


def extract_source(path: Path, source: dict, rel_path: str, chunking: dict) -> list[Passage]:
    ext = path.suffix.lower()
    rules = source.get("clean")
    if ext == ".pdf":
        return passages_from_lines(clean_lines(read_pdf(path), rules), source, rel_path, "source", chunking)
    if ext == ".docx":
        lines, rows = read_docx(path)
        lines = clean_lines(lines, rules)
        out: list[Passage] = []
        for ri, row in enumerate(rows, start=1):
            vals = list(row.values())
            name = vals[0] if vals else f"row {ri}"
            text = ". ".join(f"{k}: {v}" for k, v in row.items() if v)
            out.append(Passage(id=f"{source['id']}:row{ri:02d}", source_id=source["id"], kind="source",
                               path=rel_path, title=source["title"], section=f"Table row: {name}",
                               pages=[], text=text))
        out += passages_from_lines(lines, source, rel_path, "source", chunking, default_section="Notes")
        return out
    if ext in {".md", ".txt"}:
        return passages_from_lines(clean_lines(read_text(path), rules), source, rel_path, "source", chunking)
    raise ValueError(f"Unsupported file type {ext} for {path.name}. Supported: {', '.join(sorted(SUPPORTED))}")


def passages_from_note(path: Path, rel_path: str, note_id: str, title: str) -> list[Passage]:
    """Index a generated wiki note by its '## ' sections (used by chat and search --wiki)."""
    text = path.read_text(encoding="utf-8")
    text = re.sub(r"^---\n.*?\n---\n", "", text, flags=re.S)
    out: list[Passage] = []
    section, buf = "Summary", []
    indexed = {"Summary", "Key details", "About this source"}

    def flush():
        body = re.sub(r"\s+", " ", " ".join(buf)).strip()
        # [[raw/file.pdf#page=2|Briefing p.2]] -> Briefing p.2 ; [[Note]] -> Note
        body = re.sub(r"\[\[([^\]|]+)\|([^\]]+)\]\]", r"\2", body)
        body = re.sub(r"\[\[([^\]]+)\]\]", r"\1", body)
        if body and section in indexed:
            out.append(Passage(id=f"wiki:{note_id}:{len(out)+1}", source_id=f"wiki:{note_id}", kind="wiki",
                               path=rel_path, title=title, section=section, pages=[], text=body))

    for line in text.splitlines():
        if line.startswith("# "):
            continue
        if line.startswith("## "):
            flush()
            section, buf = line[3:].strip(), []
        else:
            buf.append(line)
    flush()
    return out

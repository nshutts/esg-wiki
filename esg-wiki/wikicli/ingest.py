"""Ingest: sources in vault/raw/ -> retrieval index + Gemma-written wiki notes.

Steps
 1. Check the source catalog (config/sources.yaml); register new files.
 2. Extract located passages from every source (the raw files are only read).
 3. For each topic in config/topics.yaml, pick the passages that mention it,
    send them with ingest-instructions.md to local Gemma, and write the note.
    Each source also gets a source note. The harness (not Gemma) sets the
    filename, properties, related links and source references.
 4. Rebuild vault/index.md and vault/Source Catalog.md.
 5. Rebuild the retrieval index in data/ (source passages + note sections).

Re-ingesting is idempotent: filenames come from the topic map, and a note is only
rewritten when its evidence, model or instructions changed (or with --force).
Notes marked `reviewed: true` are never overwritten unless --overwrite-reviewed.
"""
from __future__ import annotations

import hashlib
import json
import re
import time
from pathlib import Path

import numpy as np
import yaml

from .app import App, bold, dim, green, red, yellow
from .config import load_sources, load_topics
from .extract import SUPPORTED, Passage, extract_source, passages_from_note, sha256
from .llm import LLMError, OllamaClient
from .prompts import format_passages, load_instructions
from .retrieval import Hit, embed_passages, load_passages, save_index
from .runinfo import (harness_peak_rss_mb, memory_snapshot, model_identity, network_state,
                      runtime_identity, save_evidence, stamp)

CITE = re.compile(r"\[(\d+)\]")
NUM = re.compile(r"(?<![\w\[])\d[\d,]*(?:\.\d+)?(?![\]\w])")


# --------------------------------------------------------------------------
# Catalog
# --------------------------------------------------------------------------

def register_new_files(app: App, files: list[Path], sources: list[dict]) -> list[dict]:
    known = {s["file"] for s in sources}
    added = []
    for f in files:
        if f.name in known:
            continue
        sid = re.sub(r"[^a-z0-9]+", "-", f.stem.lower()).strip("-")
        entry = {"id": sid, "file": f.name, "title": f.stem.replace("_", " ").replace("-", " ").strip(),
                 "short": f.stem[:20], "kind": f.suffix.lstrip(".") + " file", "author": "unknown",
                 "date": "unknown"}
        with open(app.paths.config / "sources.yaml", "a", encoding="utf-8") as fh:
            fh.write("\n  # added automatically by wiki ingest; edit the title and details\n")
            fh.write(yaml.safe_dump([entry], sort_keys=False, allow_unicode=True).replace("- ", "  - ", 1)
                     .replace("\n  ", "\n    ").rstrip() + "\n")
        added.append(entry)
    return added


# --------------------------------------------------------------------------
# Notes: helpers
# --------------------------------------------------------------------------

def read_frontmatter(path: Path) -> tuple[dict, str]:
    if not path.exists():
        return {}, ""
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        return {}, text
    try:
        return yaml.safe_load(m.group(1)) or {}, text[m.end():]
    except yaml.YAMLError:
        return {}, text[m.end():]


def my_notes_section(body: str) -> str:
    """Keep anything the user wrote under '## My notes'."""
    m = re.search(r"^## My notes\n(.*)\Z", body, re.S | re.M)
    return m.group(1).strip() if m else ""


def term_score(p: Passage, terms: list[str]) -> int:
    score = 0
    for t in terms:
        pat = re.compile(rf"(?<![\w-]){re.escape(t)}(?![\w-])", 0 if t.isupper() else re.I)
        score += 3 * len(pat.findall(p.section)) + len(pat.findall(p.text))
    return score


def select_passages(passages: list[Passage], terms: list[str], max_n: int, max_words: int) -> list[Passage]:
    scored = [(term_score(p, terms), p) for p in passages]
    scored = [x for x in scored if x[0] > 0]
    if not scored:
        return []
    # Drop passages that only mention the subject in passing (score far below the best match).
    top = max(x[0] for x in scored)
    scored = [x for x in scored if x[0] >= max(1, 0.25 * top)]
    scored.sort(key=lambda x: -x[0])
    out, words = [], 0
    for _, p in scored:
        w = len(p.text.split())
        if len(out) >= max_n or (out and words + w > max_words):
            break
        out.append(p)
        words += w
    return out


def fingerprint(*parts: str) -> str:
    h = hashlib.sha256()
    for p in parts:
        h.update(p.encode("utf-8"))
        h.update(b"\0")
    return h.hexdigest()[:16]


def parse_note(text: str) -> tuple[str, list[str], bool]:
    """Parse Gemma's 'SUMMARY: ... DETAILS: - ...' output. Returns (summary, bullets, followed_format)."""
    t = text.replace("**", "").strip()
    m = re.search(r"SUMMARY:\s*(.*?)(?:\n\s*DETAILS:|\Z)", t, re.S | re.I)
    d = re.search(r"DETAILS:\s*(.*)\Z", t, re.S | re.I)
    if not m:
        return t, [], False
    summary = " ".join(m.group(1).split())
    bullets = []
    if d:
        for line in d.group(1).splitlines():
            line = line.strip()
            if re.match(r"^[-*•]\s+", line):
                bullets.append(re.sub(r"^[-*•]\s+", "", line))
    return summary, bullets, bool(d and bullets)


def raw_link(p: Passage, src: dict, pages: list[int] | None = None) -> str:
    pages = sorted(set(pages if pages is not None else p.pages))
    target = f"raw/{src['file']}"
    if pages and target.lower().endswith(".pdf"):
        label = f"{src['short']} p.{pages[0]}" if len(pages) == 1 else f"{src['short']} pp.{pages[0]}-{pages[-1]}"
        return f"[[{target}#page={pages[0]}|{label}]]"
    if p.section.startswith("Table row: "):
        return f"[[{target}|{src['short']}, {p.section[11:]} row]]"
    return f"[[{target}|{src['short']}]]"


def render_citations(line: str, used: list[Passage], srcs: dict, flags: list[str], note_name: str) -> str:
    """Replace [n] markers with links to the original file and page; flag problems."""
    cites = [int(n) for n in CITE.findall(line)]
    clean = CITE.sub("", line).rstrip(" .;,") + "."
    clean = re.sub(r"\s+\.", ".", clean)
    links, cited_text = [], ""
    for n in dict.fromkeys(cites):
        if 1 <= n <= len(used):
            p = used[n - 1]
            links.append(raw_link(p, srcs[p.source_id]))
            cited_text += " " + p.text
        else:
            flags.append(f"citation [{n}] points to no passage: \"{clean[:80]}\"")
    if not links:
        flags.append(f"no citation: \"{clean[:80]}\"")
        return clean
    cited_nums = {x.replace(",", "") for x in NUM.findall(cited_text)}
    for x in NUM.findall(clean):
        if x.replace(",", "") not in cited_nums:
            flags.append(f"number {x} not in cited passage: \"{clean[:80]}\"")
    return f"{clean} ({', '.join(links)})"


def note_markdown(meta: dict, title: str, summary: str, bullets: list[str], related: list[str],
                  refs: list[str], my_notes: str, extra_sections: list[tuple[str, list[str]]] = ()) -> str:
    fm = yaml.safe_dump(meta, sort_keys=False, allow_unicode=True, width=1000).strip()
    parts = [f"---\n{fm}\n---", f"# {title}", "", summary, ""]
    if bullets:
        parts += ["## Key details", ""] + [f"- {b}" for b in bullets] + [""]
    for heading, lines in extra_sections:
        if lines:
            parts += [f"## {heading}", ""] + lines + [""]
    if related:
        parts += ["## Related notes", ""] + related + [""]
    parts += ["## Source references", ""] + refs + [""]
    parts += ["## My notes", "", my_notes or "_Your own comments go here. Ingest keeps this section._", ""]
    return "\n".join(parts)


# --------------------------------------------------------------------------
# Main ingest
# --------------------------------------------------------------------------

def run_ingest(app: App, target: str | None = None, force: bool = False, overwrite_reviewed: bool = False,
               skip_notes: bool = False, echo: bool = True) -> dict:
    s = app.settings
    P = app.paths
    t_start = time.perf_counter()
    net = network_state()
    log: list[dict] = []

    def say(msg: str):
        if echo:
            print(msg)

    # ---- 1. which files ----------------------------------------------------
    tpath = Path(target).expanduser() if target else P.raw
    if not tpath.is_absolute():
        tpath = (Path.cwd() / tpath).resolve()
    if not tpath.exists():
        raise FileNotFoundError(f"Path not found: {tpath}")
    if tpath.is_dir():
        files = sorted(f for f in tpath.iterdir() if f.suffix.lower() in SUPPORTED and not f.name.startswith("."))
    else:
        files = [tpath]
    for f in files:
        if f.resolve().parent != P.raw.resolve():
            raise ValueError(f"{f.name} is not in vault/raw/. Copy originals into vault/raw/ first, "
                             "so the wiki can link back to them.")
    if not files:
        raise FileNotFoundError(f"No supported files ({', '.join(sorted(SUPPORTED))}) in {tpath}")

    sources = load_sources(s)
    added = register_new_files(app, files, sources)
    if added:
        sources = load_sources(s)
        say(yellow(f"Registered {len(added)} new source(s) in config/sources.yaml: "
                   + ", ".join(a["file"] for a in added)))
    targeted_ids = {src["id"] for src in sources if src["file"] in {f.name for f in files}}
    srcs = {src["id"]: src for src in sources}

    say(bold(f"Ingest · local model {s.generator} · network: {net}"))
    say(dim(f"target: {app.rel(tpath)} ({len(files)} file(s))"))

    # ---- 2. extract passages from every catalogued source --------------------
    source_passages: list[Passage] = []
    hashes = {}
    for src in sources:
        f = P.raw / src["file"]
        if not f.exists():
            say(red(f"  missing in vault/raw/: {src['file']} (listed in sources.yaml); skipped"))
            continue
        hashes[src["id"]] = sha256(f)
        ps = extract_source(f, src, f"vault/raw/{src['file']}", s.chunking)
        src["_passages"] = len(ps)
        source_passages += ps
        say(dim(f"  extracted {len(ps):3d} passages from {src['file']}"))

    # ---- 3. notes --------------------------------------------------------------
    notes_written: list[str] = []
    if not skip_notes:
        topic_cfg = load_topics(s)
        ingest_sys = load_instructions(P.root, "ingest-instructions.md")
        instr_hash = fingerprint(ingest_sys)
        jobs = []
        for src in sources:
            if src["id"] in hashes:
                jobs.append(("source", src))
        for t in topic_cfg.get("topics", []):
            jobs.append(("topic", t))
        topic_names = {t["name"] for t in topic_cfg.get("topics", [])}
        topic_sources: dict[str, set] = {}

        say(bold(f"\nWriting wiki notes ({len(jobs)} candidates)"))
        for i, (kind, item) in enumerate(jobs, 1):
            if kind == "source":
                title, folder = item["title"], "Sources"
                used = [p for p in source_passages if p.source_id == item["id"]]
                budget, trimmed = s.ingest["source_note_words"], []
                wc = 0
                for p in used:
                    wc += len(p.text.split())
                    if wc > budget:
                        break
                    trimmed.append(p)
                used = trimmed
                affected = item["id"] in targeted_ids
            else:
                title, folder = item["name"], item["folder"]
                used = select_passages(source_passages, item.get("terms", []) + [item["name"]],
                                       s.ingest["topic_max_passages"], s.ingest["topic_passage_words"])
                affected = any(p.source_id in targeted_ids for p in used)
                topic_sources[title] = {p.source_id for p in used}

            path = P.wiki / folder / f"{title}.md"
            meta_old, body_old = read_frontmatter(path)
            fp = fingerprint(title, s.generator, instr_hash, *[p.id + p.text for p in used])
            label = f"[{i:2d}/{len(jobs)}] {folder}/{title}"
            entry = {"note": f"wiki/{folder}/{title}.md", "passages": [p.id for p in used]}

            if not used:
                entry["status"] = "no evidence in sources; not written"
                say(yellow(f"  {label}: no matching passages, skipped"))
                log.append(entry)
                continue
            if not affected and path.exists():
                entry["status"] = "not affected by this ingest"
                log.append(entry)
                continue
            if meta_old.get("reviewed") is True and not overwrite_reviewed:
                entry["status"] = "reviewed: kept as is"
                say(dim(f"  {label}: reviewed, kept"))
                log.append(entry)
                continue
            if meta_old.get("evidence_fingerprint") == fp and not force:
                entry["status"] = "unchanged"
                say(dim(f"  {label}: unchanged"))
                log.append(entry)
                continue

            hits = [Hit(passage=p, score=0.0) for p in used]
            desc = item.get("description", "") if kind == "topic" else f"a {item.get('kind', 'source')}"
            user = (f"Note title: {title}\nSubject: {desc}\n\nSource passages:\n\n{format_passages(hits)}\n\n"
                    f"Write the note body for \"{title}\" now, in the required format.")
            t0 = time.perf_counter()
            try:
                res = app.client.chat(s.generator, [{"role": "system", "content": ingest_sys},
                                                   {"role": "user", "content": user}],
                                      options=s.gen("ingest"), think=s.think)
            except LLMError as e:
                raise LLMError(f"{e}\n(Stopped while writing {title}; notes written so far are saved.)")
            secs = round(time.perf_counter() - t0, 1)
            summary, bullets, ok = parse_note(res["text"])
            flags: list[str] = []
            if not ok:
                flags.append("Gemma did not follow the SUMMARY/DETAILS format; raw output kept as summary")
            summary_linked = render_citations(summary, used, srcs, [], title) if CITE.search(summary) else summary
            bullets_linked = [render_citations(b, used, srcs, flags, title) for b in bullets]

            # related notes (curated) and source references (from the passages actually used)
            related = []
            if kind == "topic":
                for target_name, reason in item.get("related", []):
                    if target_name in topic_names:
                        related.append(f"- [[{target_name}]]: {reason}")
            refs = []
            by_source: dict[str, list[str]] = {}
            for p in used:
                sec = f' ("{p.section}")' if p.section else ""
                link = raw_link(p, srcs[p.source_id]) + sec
                if link not in by_source.setdefault(p.source_id, []):
                    by_source[p.source_id].append(link)
            for sid, links in by_source.items():
                if kind == "topic":
                    refs.append(f"- [[{srcs[sid]['title']}]]: " + "; ".join(links))
                else:
                    refs += [f"- {l}" for l in links]
            extra = []
            if kind == "source":
                refs = [f"- Original file: [[raw/{item['file']}]]"] + refs
                about = [f"- Author: {item.get('author', 'unknown')}", f"- Date: {item.get('date', 'unknown')}",
                         f"- Type: {item.get('kind', '')}"]
                if item.get("url"):
                    about.append(f"- URL: {item['url']}")
                if item.get("note"):
                    about.append(f"- Note: {item['note']}")
                extra.append(("About this source", about))

            meta = {
                "title": title,
                "id": item["id"],
                "type": "source note" if kind == "source" else "topic",
                "folder": folder,
                "aliases": [a for a in (item.get("terms", []) if kind == "topic" else [item.get("short", "")])
                            if a and a != title][:6],
                "sources": sorted({p.source_id for p in used}),
                "source_files": sorted({f"raw/{srcs[p.source_id]['file']}" for p in used}),
                "passages": [p.id for p in used],
                "generated_by": s.generator,
                "generated_at": stamp(),
                "evidence_fingerprint": fp,
                "reviewed": False,
                "review_flags": flags,
            }
            if kind == "source":
                meta["source_sha256"] = hashes.get(item["id"], "")[:16]
            md = note_markdown(meta, title, summary_linked, bullets_linked, related, refs,
                               my_notes_section(body_old), extra)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(md, encoding="utf-8")
            notes_written.append(str(path))
            status = "written" if not meta_old else "updated"
            entry.update(status=status, seconds=secs, review_flags=flags, stats=res["stats"])
            log.append(entry)
            fl = yellow(f" · {len(flags)} flag(s) to review") if flags else ""
            say(f"  {label}: {green(status)} in {secs}s{fl}")

        # source notes get a "Topics in this source" section after topics are known
        for src in sources:
            path = P.wiki / "Sources" / f"{src['title']}.md"
            if not path.exists():
                continue
            text = path.read_text(encoding="utf-8")
            topics_here = sorted(t for t, ids in topic_sources.items() if src["id"] in ids)
            block = "## Topics that draw on this source\n\n" + "\n".join(f"- [[{t}]]" for t in topics_here) + "\n\n"
            text = re.sub(r"## Topics that draw on this source\n\n.*?\n\n(?=## )", "", text, flags=re.S)
            text = text.replace("## Source references", block + "## Source references", 1)
            path.write_text(text, encoding="utf-8")

        write_index(app, topic_cfg, sources)
    write_catalog(app, sources, hashes)

    # unmanaged notes (never deleted automatically)
    managed = {f"{e['note']}" for e in log}
    unmanaged = [app.rel(p) for p in P.wiki.rglob("*.md")
                 if f"wiki/{p.relative_to(P.wiki)}" not in managed] if not skip_notes else []

    # ---- 5. retrieval index ---------------------------------------------------
    note_passages: list[Passage] = []
    for p in sorted(P.wiki.rglob("*.md")):
        meta, _ = read_frontmatter(p)
        note_passages += passages_from_note(p, app.rel(p), meta.get("id", p.stem), p.stem)
    all_passages = source_passages + note_passages
    emb, emb_status = build_embeddings(app.client, s.embedder, P.data, all_passages)
    save_index(P.data, all_passages, emb, {"embedder": s.embedder, "generator": s.generator,
                                           "source_hashes": hashes})
    app.reset_retriever()
    say(bold("\nRetrieval index") + dim(f": {len(source_passages)} source passages + {len(note_passages)} "
                                        f"note sections, embeddings: {emb_status}"))
    if unmanaged:
        say(yellow("Notes not in the topic map (left untouched; merge or delete by hand): " + ", ".join(unmanaged)))

    total = round(time.perf_counter() - t_start, 1)
    mem = memory_snapshot(app.client)
    record = {"mode": "ingest", "execution": "local", "network_at_run_time": net, "timestamp": stamp(),
              "target": app.rel(tpath), "files": [f.name for f in files], "force": force,
              "model": model_identity(app.client, s.generator),
              "embedding_model": model_identity(app.client, s.embedder),
              "runtime": runtime_identity(app.client), "notes": log, "unmanaged_notes": unmanaged,
              "index": {"source_passages": len(source_passages), "note_sections": len(note_passages),
                        "embeddings": emb_status},
              "total_seconds": total,
              "memory": {"ollama_loaded_models": mem, "harness_peak_rss_mb": harness_peak_rss_mb()}}
    name = time.strftime("%Y-%m-%d_%H%M%S") + "-ingest"
    path = save_evidence(P.evidence, "ingest", name, record, ingest_md(record))
    say(dim(f"total {total}s · saved: {app.rel(path)}"))
    return record


def build_embeddings(client: OllamaClient, model: str, data_dir: Path, passages: list[Passage]):
    """Embed passages, reusing vectors for passages whose text has not changed."""
    old = {}
    try:
        old_p = load_passages(data_dir)
        old_e = np.load(data_dir / "embeddings.npy") if (data_dir / "embeddings.npy").exists() else None
        meta = json.loads((data_dir / "index_meta.json").read_text()) if (data_dir / "index_meta.json").exists() else {}
        if old_e is not None and meta.get("embedder") == model and len(old_e) == len(old_p):
            old = {(p.section, p.text): old_e[i] for i, p in enumerate(old_p)}
    except Exception:
        old = {}
    need = [p for p in passages if (p.section, p.text) not in old]
    try:
        new = embed_passages(client, model, need) if need else np.zeros((0, 0), dtype=np.float32)
    except LLMError as e:
        return None, f"not built ({e.__class__.__name__}: {e}); search will use keywords only"
    vec = {}
    for p, v in zip(need, new):
        vec[(p.section, p.text)] = v
    rows = [old.get((p.section, p.text), vec.get((p.section, p.text))) for p in passages]
    return np.vstack(rows).astype(np.float32), f"{model} ({len(need)} new, {len(passages) - len(need)} reused)"


# --------------------------------------------------------------------------
# Vault landing pages
# --------------------------------------------------------------------------

def write_index(app: App, topic_cfg: dict, sources: list[dict]) -> None:
    P = app.paths
    lines = ["# ESG Reporting Wiki", "",
             "A personal wiki on ESG frameworks, standards and regulations, built from three sources "
             "and written by a local Gemma model. Start with a topic below, follow its related notes, "
             "and use each note's source references to open the original page.", "",
             "Notes are generated, then reviewed by hand; a note's `reviewed` property shows whether "
             "that has happened. Originals live unchanged in `raw/`.", ""]
    for folder in topic_cfg.get("folders", []):
        items = [t for t in topic_cfg.get("topics", []) if t["folder"] == folder["name"]
                 and (P.wiki / folder["name"] / f"{t['name']}.md").exists()]
        if not items:
            continue
        lines += [f"## {folder['name']}", "", f"_{folder['blurb']}_", ""]
        lines += [f"- [[{t['name']}]]: {t['description']}" for t in items] + [""]
    lines += ["## Sources", "", "_What each note is built from. Full details in [[Source Catalog]]._", ""]
    for src in sources:
        if (P.wiki / "Sources" / f"{src['title']}.md").exists():
            lines.append(f"- [[{src['title']}]]: {src.get('kind', '')}, {src.get('author', '')}, {src.get('date', '')}")
    lines += ["", f"_Index updated {stamp()} by `wiki ingest`._", ""]
    (P.vault / "index.md").write_text("\n".join(lines), encoding="utf-8")


def write_catalog(app: App, sources: list[dict], hashes: dict) -> None:
    P = app.paths
    lines = ["# Source Catalog", "",
             "Every original in `raw/`, unchanged. The ID is what the retrieval index and note "
             "properties use; the title is the readable name used in the wiki.", "",
             "| ID | Title (source note) | Original file | Author | Date | Type | Passages | SHA-256 (first 16) |",
             "|---|---|---|---|---|---|---|---|"]
    for src in sources:
        lines.append(f"| `{src['id']}` | [[{src['title']}]] | [[raw/{src['file']}\\|{src['file']}]] | "
                     f"{src.get('author', '')} | {src.get('date', '')} | {src.get('kind', '')} | "
                     f"{src.get('_passages', '?')} | `{hashes.get(src['id'], 'missing')[:16]}` |")
    lines += ["", "Back to [[index]].", ""]
    (P.vault / "Source Catalog.md").write_text("\n".join(lines), encoding="utf-8")


def ingest_md(r: dict) -> str:
    m = r["model"]
    lines = ["# Ingest run", "",
             f"- Execution: {r['execution']} via {r['runtime']['runtime']} {r['runtime']['version']} · "
             f"network: **{r['network_at_run_time']}** · {r['timestamp']}",
             f"- Model: `{m.get('name')}` (digest `{m.get('digest', '?')}`, {m.get('quantization', '?')})",
             f"- Target: `{r['target']}` ({', '.join(r['files'])}) · force: {r['force']}",
             f"- Index: {r['index']['source_passages']} source passages, {r['index']['note_sections']} note "
             f"sections, embeddings {r['index']['embeddings']}",
             f"- Total time: {r['total_seconds']} s · harness peak memory {r['memory']['harness_peak_rss_mb']} MB"]
    for mm in r["memory"]["ollama_loaded_models"]:
        lines.append(f"- Loaded in Ollama: `{mm['model']}` {mm['loaded_size_gb']} GB")
    lines += ["", "| Note | Status | Seconds | Review flags |", "|---|---|---|---|"]
    for n in r["notes"]:
        flags = "<br>".join(n.get("review_flags", [])) or ""
        lines.append(f"| {n['note']} | {n.get('status', '')} | {n.get('seconds', '')} | {flags} |")
    if r["unmanaged_notes"]:
        lines += ["", "Unmanaged notes: " + ", ".join(r["unmanaged_notes"])]
    return "\n".join(lines) + "\n"

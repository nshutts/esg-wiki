"""Search mode: show the original passages the retrieval tool finds.

No answer is generated and Gemma is never called. Only the embedding model is
used (for the semantic half); if Ollama is not running, search falls back to
keyword-only BM25 and still works.
"""
from __future__ import annotations

import textwrap
import time

from .app import App, bold, dim, yellow
from .runinfo import network_state, save_evidence, slugify, stamp


def run_search(app: App, query: str, k: int = 5, include_wiki: bool = False, method: str | None = None):
    kinds = ("source", "wiki") if include_wiki else ("source",)
    t0 = time.perf_counter()
    hits = app.retriever.search(query, k=k, kinds=kinds, method=method)
    return hits, round(time.perf_counter() - t0, 3)


def print_search(app: App, query: str, k: int = 5, include_wiki: bool = False, method: str | None = None,
                 save: bool = False) -> None:
    if not query:
        print("Usage: search <words>")
        return
    net = network_state()
    hits, secs = run_search(app, query, k, include_wiki, method)
    used = method or app.settings.retrieval["method"]
    print(dim(f"mode: search (no model answer) | method: {used} | network: {net} | {secs}s"))
    if app.retriever.notice:
        print(yellow(app.retriever.notice))
    if not hits:
        print("No matching passages.")
    for n, h in enumerate(hits, 1):
        p = h.passage
        tag = " [wiki note]" if p.kind == "wiki" else ""
        cos = "n/a" if h.cosine is None else f"{h.cosine:.3f}"
        print(bold(f"\n[{n}] {p.title}, {p.location or p.section}{tag}"))
        print(dim(f"    {p.path} · id {p.id} · keyword rank {h.bm25_rank} · meaning rank {h.vector_rank} "
                  f"(cosine {cos})"))
        for line in textwrap.wrap(p.text, 96):
            print("    " + line)
    if save:
        record = {"mode": "search", "execution": "local", "network_at_run_time": net, "timestamp": stamp(),
                  "query": query, "method": used, "notice": app.retriever.notice, "seconds": secs,
                  "results": [h.to_dict() for h in hits]}
        path = save_evidence(app.paths.evidence, "search", f"{time.strftime('%Y-%m-%d_%H%M%S')}-{slugify(query)}",
                             record, search_md(record))
        print(dim(f"\nsaved: {app.rel(path)}"))


def search_md(r: dict) -> str:
    lines = [f"# Search: {r['query']}", "",
             f"- Mode: search (passages only, no generated answer) · method: {r['method']} · "
             f"network: {r['network_at_run_time']} · {r['timestamp']}", ""]
    if r.get("notice"):
        lines += [f"_Note: {r['notice']}_", ""]
    for n, p in enumerate(r["results"], 1):
        lines += [f"## [{n}] {p['title']}, {p['location'] or p['section']}", "",
                  f"`{p['path']}` · id `{p['id']}` · BM25 rank {p['bm25_rank']} · vector rank {p['vector_rank']}",
                  "", "> " + p["text"], ""]
    return "\n".join(lines)

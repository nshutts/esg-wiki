"""Ask mode: standalone, neutral, cited answers (the RAG workflow).

question -> retrieve source passages -> wiki-instructions.md + passages + question
-> local Gemma -> citation checks -> display -> save evidence card.

Nothing from chat is used here: no history, no persona, no chat drafts. Only
original source passages (kind == "source") are retrieved as evidence.
"""
from __future__ import annotations

import textwrap
import time

from . import citations
from .app import App, bold, cyan, dim, green, red, stream_print, yellow
from .prompts import ask_messages, load_instructions
from .runinfo import (harness_peak_rss_mb, memory_snapshot, model_identity, network_state,
                      runtime_identity, save_evidence, slugify, stamp)


def run_ask(app: App, question: str, *, k: int | None = None, echo: bool = True,
            save: bool = True, evidence_kind: str = "ask", evidence_name: str | None = None,
            extra: dict | None = None) -> dict:
    s = app.settings
    k = k or s.retrieval["top_k"]
    net = network_state()

    # 1) retrieve (evidence = original sources only)
    t0 = time.perf_counter()
    hits = app.retriever.search(question, k=k, kinds=("source",))
    retrieval_seconds = round(time.perf_counter() - t0, 2)
    if echo:
        print(dim(f"mode: ask | execution: local (Ollama) | model: {s.generator} | network: {net}"))
        if app.retriever.notice:
            print(yellow(app.retriever.notice))
        print(dim(f"retrieved {len(hits)} passages in {retrieval_seconds}s "
                  f"({s.retrieval['method']} search):"))
        for n, h in enumerate(hits, 1):
            print(dim(f"  [{n}] {h.passage.path}  {h.passage.location}"))
        print()

    # 2) build prompt from the research rules + passages
    system = load_instructions(s.paths.root, "wiki-instructions.md")
    messages = ask_messages(system, question, hits)

    # 3) call local Gemma
    result = app.client.chat(s.generator, messages, options=s.gen("ask"), think=s.think,
                             on_token=stream_print if echo else None)
    answer = result["text"]
    mem = memory_snapshot(app.client)

    # 4) check citations
    chk = citations.check(answer, hits)
    if echo:
        print("\n")
        if chk["cited_sources"]:
            print(bold("Sources"))
            for c in chk["cited_sources"]:
                print(f"  [{c['n']}] {c['title']}, {c['location']}  {dim(c['path'])}")
        colour = green if chk["status"] in ("cited", "insufficient-evidence") else yellow
        print(colour(f"Citation check: {chk['status']} ({citations.STATUS_TEXT[chk['status']]})"))
        if chk["invalid_citations"]:
            print(red(f"  citations that point to no passage: {chk['invalid_citations']}"))
        if chk["numbers_not_in_retrieved_passages"]:
            print(red(f"  numbers not found in any retrieved passage: {chk['numbers_not_in_retrieved_passages']}"))
        st = result["stats"]
        print(dim(f"time: retrieval {retrieval_seconds}s, model {st['wall_seconds']}s "
                  f"({st['output_tokens']} tokens, {st['output_tokens_per_second']} tok/s, "
                  f"prompt {st['prompt_tokens']} tokens)"))

    record = {
        "mode": "ask", "execution": "local", "network_at_run_time": net, "timestamp": stamp(),
        "question": question,
        "model": model_identity(app.client, s.generator),
        "embedding_model": model_identity(app.client, s.embedder),
        "runtime": runtime_identity(app.client),
        "generation_options": s.gen("ask"),
        "retrieval": {"method": s.retrieval["method"], "top_k": k, "seconds": retrieval_seconds,
                      "notice": app.retriever.notice, "passages": [h.to_dict() for h in hits]},
        "prompt_words": sum(len(m["content"].split()) for m in messages),
        "answer": answer,
        "citation_check": chk,
        "timing": result["stats"],
        "memory": {"ollama_loaded_models": mem, "harness_peak_rss_mb": harness_peak_rss_mb()},
    }
    if extra:
        record.update(extra)
    if save:
        name = evidence_name or f"{time.strftime('%Y-%m-%d_%H%M%S')}-{slugify(question)}"
        path = save_evidence(app.paths.evidence, evidence_kind, name, record, ask_card(record))
        record["saved_to"] = app.rel(path)
        if echo:
            print(dim(f"saved: {record['saved_to']}"))
    return record


def _quote(text: str) -> str:
    return "\n".join("> " + line for line in textwrap.wrap(text, 100))


def ask_card(r: dict, heading: str | None = None, preface: str = "") -> str:
    m, rt, t = r["model"], r["runtime"], r["timing"]
    lines = [f"# {heading or 'Ask: ' + r['question']}", ""]
    if preface:
        lines += [preface, ""]
    lines += [
        "| Field | Value |", "|---|---|",
        f"| Question | {r['question']} |",
        f"| Mode | ask (standalone; no chat history, no persona) |",
        f"| Execution | {r['execution']} via {rt['runtime']} {rt['version']} |",
        f"| Network at run time | **{r['network_at_run_time']}** |",
        f"| Model | `{m.get('name')}` (digest `{m.get('digest', '?')}`, {m.get('parameter_size', '?')}, "
        f"{m.get('quantization', '?')}) |",
        f"| Embedding model | `{r['embedding_model'].get('name')}` (digest `{r['embedding_model'].get('digest', '?')}`) |",
        f"| Retrieval | {r['retrieval']['method']}, top {r['retrieval']['top_k']} source passages |",
        f"| Time | {r['timestamp']} |",
        "",
        "## Retrieved passages",
        "",
    ]
    if r["retrieval"].get("notice"):
        lines += [f"_Note: {r['retrieval']['notice']}_", ""]
    for n, p in enumerate(r["retrieval"]["passages"], 1):
        cos = "n/a" if p["cosine"] is None else p["cosine"]
        lines += [f"**[{n}] {p['title']}, {p['location']}**  ",
                  f"`{p['path']}` · id `{p['id']}` · BM25 rank {p['bm25_rank']} · vector rank "
                  f"{p['vector_rank']} (cosine {cos})", "", _quote(p["text"]), ""]
    lines += ["## Gemma's answer (verbatim)", "", r["answer"] or "_(empty)_", "", "## Citations", ""]
    cs = r["citation_check"]["cited_sources"]
    lines += [f"- [{c['n']}] {c['title']}, {c['location']} → `{c['path']}`" for c in cs] or ["- none"]
    chk = r["citation_check"]
    lines += ["", "## Automatic checks", "",
              f"- Status: **{chk['status']}** ({citations.STATUS_TEXT[chk['status']]})",
              f"- Citations that point to no passage: {chk['invalid_citations'] or 'none'}",
              f"- Sentences without a citation: {len(chk['uncited_sentences'])}"]
    for s in chk["uncited_sentences"]:
        lines.append(f"  - \"{s}\"")
    if chk["numbers"]:
        lines.append("- Numbers in the answer:")
        for x in chk["numbers"]:
            where = ("in a cited passage" if x["in_cited_passages"] else
                     "only in an uncited retrieved passage" if x["in_any_retrieved_passage"] else
                     "**not in any retrieved passage**")
            lines.append(f"  - {x['number']}: {where}")
    lines += ["", "## Timing and memory", "",
              f"- Retrieval: {r['retrieval']['seconds']} s",
              f"- Model: {t['wall_seconds']} s total, first token after {t['time_to_first_token_seconds']} s, "
              f"model load {t['load_seconds']} s",
              f"- Tokens: {t['prompt_tokens']} prompt, {t['output_tokens']} output "
              f"({t['output_tokens_per_second']} tokens/s)",
              f"- Prompt size: {r['prompt_words']} words"]
    for mm in r["memory"]["ollama_loaded_models"]:
        lines.append(f"- Loaded in Ollama: `{mm['model']}` {mm['loaded_size_gb']} GB "
                     f"({mm['in_gpu_memory_gb']} GB in GPU memory, context {mm['context_length']})")
    lines.append(f"- Harness process peak memory: {r['memory']['harness_peak_rss_mb']} MB")
    return "\n".join(lines) + "\n"

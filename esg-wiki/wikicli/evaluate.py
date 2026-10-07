"""Evaluation commands: the four ask-mode tests and the mode-boundary checks.

Each test is run in ask mode exactly as `wiki ask` would run it (fresh, no chat
history). Retrieval is scored separately from the answer: did the expected
passage appear, and at what rank? The final judgement is left for a human to
write in each evidence card.
"""
from __future__ import annotations

import time

from .app import App, bold, dim, green, red, yellow
from .ask import ask_card, run_ask
from .chat import ChatSession, transcript_md
from .config import load_yaml
from .runinfo import network_state, save_evidence, stamp
from .search import run_search, search_md


def run_tests(app: App, only: list[int] | None = None) -> list[dict]:
    spec = load_yaml(app.paths.tests / "questions.yaml")
    results = []
    for t in spec["tests"]:
        if only and t["id"] not in only:
            continue
        print(bold(f"\n=== Test {t['id']}: {t['name']} ({t['type']}) ==="))
        print(f"Q: {t['question']}\n")
        expected = t.get("expected_passages", [])
        r = run_ask(app, t["question"], echo=True, save=False)
        got = [p["id"] for p in r["retrieval"]["passages"]]
        found = {e: (got.index(e) + 1 if e in got else None) for e in expected}
        cited_ids = [c["passage_id"] for c in r["citation_check"]["cited_sources"]]
        retrieval_ok = all(v is not None for v in found.values()) if expected else None
        answer_status = r["citation_check"]["status"]
        if t["id"] == 4 or not expected:
            behaviour_ok = answer_status == "insufficient-evidence"
        else:
            behaviour_ok = answer_status in ("cited", "partly-cited") and any(e in cited_ids for e in expected)
        r["test"] = {"id": t["id"], "name": t["name"], "type": t["type"],
                     "expected_behavior": t["expected_behavior"], "expected_answer": t["expected_answer"],
                     "expected_sources": t.get("expected_sources", []), "expected_passages": expected,
                     "expected_passage_ranks": found, "retrieval_found_expected": retrieval_ok,
                     "expected_passage_cited": [e for e in expected if e in cited_ids],
                     "automatic_answer_check": behaviour_ok}
        verdict = []
        if expected:
            verdict.append(green("retrieval: expected passage(s) found " + str(found)) if retrieval_ok
                           else red(f"retrieval: expected passage missing {found}"))
        verdict.append(green("answer: meets automatic check") if behaviour_ok
                       else yellow("answer: fails automatic check, inspect by hand"))
        print("\n" + " | ".join(verdict))

        name = f"Test {t['id']} - {t['name']}"
        preface = test_preface(r["test"])
        path = save_evidence(app.paths.evidence, "ask-tests", name, r,
                             ask_card(r, heading=name, preface=preface) + ASSESSMENT)
        print(dim(f"saved: {app.rel(path)}"))
        results.append(r)
    if results:
        write_summary(app, results)
    return results


ASSESSMENT = """
## Assessment (written by hand after opening the cited pages)

- Retrieval: did the right passage appear?
- Answer: does each claim follow from the cited passage?
- Citations: do they point to the right file and page?
- Verdict: pass / partial / fail, and why.
"""


def test_preface(t: dict) -> str:
    lines = [f"**Test type:** {t['type']}  ", f"**Expected behavior:** {t['expected_behavior']}  ",
             f"**Expected answer (written before running):** {t['expected_answer']}  "]
    for s in t["expected_sources"]:
        lines.append(f"**Expected source:** `{s['file']}`, {s['location']}  ")
    if t["expected_passages"]:
        ranks = ", ".join(f"`{k}` → rank {v if v else 'not retrieved'}" for k, v in t["expected_passage_ranks"].items())
        lines.append(f"**Expected passage(s) in retrieval:** {ranks}  ")
        lines.append(f"**Expected passage cited in answer:** {', '.join(t['expected_passage_cited']) or 'no'}  ")
    lines.append(f"**Automatic answer check:** {'pass' if t['automatic_answer_check'] else 'fail'} "
                 "(citation status and expected-passage citation only; the human assessment below decides)")
    return "\n".join(lines)


def write_summary(app: App, results: list[dict]) -> None:
    lines = ["# Ask-mode test results", "",
             f"Run {stamp()} · model `{results[0]['model'].get('name')}` · network "
             f"**{results[0]['network_at_run_time']}**", "",
             "| Test | Question | Expected passage rank | Citation status | Automatic check | Card |",
             "|---|---|---|---|---|---|"]
    for r in results:
        t = r["test"]
        ranks = ", ".join(str(v) if v else "missing" for v in t["expected_passage_ranks"].values()) or "n/a"
        card = f"Test {t['id']} - {t['name']}.md".replace(" ", "%20").replace("(", "%28").replace(")", "%29")
        lines.append(f"| {t['id']} | {r['question']} | {ranks} | {r['citation_check']['status']} | "
                     f"{'pass' if t['automatic_answer_check'] else 'fail'} | [card]({card}) |")
    (app.paths.evidence / "ask-tests" / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_modecheck(app: App) -> str:
    spec = load_yaml(app.paths.tests / "mode_checks.yaml")
    net = network_state()
    out = ["# Mode-boundary checks", "", f"Run {stamp()} · model `{app.settings.generator}` · "
           f"execution local · network **{net}**", ""]

    print(bold("\n=== Chat checks ==="))
    session = ChatSession(app)
    for c in spec["chat"]:
        print(bold(f"\nyou> {c['message']}"))
        session.respond(c["message"], echo=True)
    rec = {"mode": "chat", "execution": "local", "network_at_start": session.network,
           "network_at_save": network_state(), "timestamp": stamp(), "model": app.settings.generator,
           "turns": session.log}
    out.append(transcript_md(rec, "Chat").replace("# Chat", "## Chat", 1).replace("\n## Turn", "\n### Turn"))
    out += ["", "Expected:", ""] + [f"- \"{c['message']}\": {c['expect']}" for c in spec["chat"]] + [""]

    print(bold("\n=== Search check ==="))
    for s in spec["search"]:
        from .search import print_search
        print_search(app, s["query"], k=5)
        hits, secs = run_search(app, s["query"], k=5)
        srec = {"query": s["query"], "method": app.settings.retrieval["method"], "network_at_run_time": net,
                "timestamp": stamp(), "notice": app.retriever.notice, "results": [h.to_dict() for h in hits]}
        out += [search_md(srec).replace("# Search", "## Search", 1).replace("\n## [", "\n### ["),
                f"Expected: {s['expect']}", ""]

    print(bold("\n=== Ask check (separate from chat) ==="))
    for a in spec["ask"]:
        print(f"Q: {a['question']}\n")
        r = run_ask(app, a["question"], echo=True, save=False)
        out += [ask_card(r, heading="Ask: " + a["question"]).replace("\n## ", "\n### ").replace("# Ask", "## Ask", 1),
                f"Expected: {a['expect']}", ""]
    out += ["## Assessment (written by hand)", "",
            "- Chat capability questions answered without a notes lookup? ",
            "- \"make that shorter\" used the conversation? ",
            "- Search showed original passages with no generated answer? ",
            "- Ask ignored the claim made only in chat? ", ""]
    name = time.strftime("%Y-%m-%d_%H%M%S") + "-mode-checks"
    folder = app.paths.evidence / "mode-checks"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{name}.md"
    path.write_text("\n".join(out), encoding="utf-8")
    print(dim(f"\nsaved: {app.rel(path)}"))
    return str(path)

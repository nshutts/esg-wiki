"""Citation checks run on every generated answer.

These are mechanical checks, not proof: a human still opens the cited source.
  - every [n] must refer to a passage that was actually given to the model
  - sentences with factual content should carry a citation
  - every number in the answer should appear in at least one cited passage
"""
from __future__ import annotations

import re

from .retrieval import Hit

CITE = re.compile(r"\[(\d+)\]")
INSUFFICIENT = re.compile(r"insufficient evidence|do(es)? not (contain|include|mention|cover|say)|"
                          r"no (information|passage|evidence)|not (covered|mentioned|addressed)", re.I)
NUMBER = re.compile(r"(?<![\w\[])(?:[$€£]|EUR |A\$)?\d[\d,]*(?:\.\d+)?(?:\s?(?:%|bn|m|billion|million))?(?![\]\w])")
SENT = re.compile(r"(?<=[.!?])\s+")


def _norm_num(s: str) -> str:
    s = s.lower().replace(",", "").replace("eur ", "").replace("a$", "").replace("$", "").replace("€", "")
    s = s.replace(" billion", "bn").replace(" million", "m").replace(" ", "")
    return s


def check(answer: str, hits: list[Hit]) -> dict:
    cited = [int(n) for n in CITE.findall(answer)]
    valid = sorted({n for n in cited if 1 <= n <= len(hits)})
    invalid = sorted({n for n in cited if not 1 <= n <= len(hits)})
    insufficient = answer.strip().upper().startswith("INSUFFICIENT EVIDENCE") or bool(
        INSUFFICIENT.search(answer) and not valid)

    sentences = [s for s in SENT.split(answer.strip()) if len(s.split()) >= 4]
    uncited = [s for s in sentences if not CITE.search(s) and not INSUFFICIENT.search(s)]

    cited_text = " ".join(hits[n - 1].passage.text for n in valid)
    cited_nums = {_norm_num(m) for m in NUMBER.findall(cited_text)}
    all_text = " ".join(h.passage.text for h in hits)
    all_nums = {_norm_num(m) for m in NUMBER.findall(all_text)}
    answer_wo_cites = CITE.sub("", answer)
    numbers = []
    for m in NUMBER.findall(answer_wo_cites):
        n = _norm_num(m)
        numbers.append({"number": m.strip(), "in_cited_passages": n in cited_nums,
                        "in_any_retrieved_passage": n in all_nums})
    unsupported_numbers = [x["number"] for x in numbers if not x["in_any_retrieved_passage"]]

    if insufficient and not valid:
        status = "insufficient-evidence"
    elif invalid or unsupported_numbers:
        status = "citation-problem"
    elif not valid:
        status = "uncited"
    elif uncited:
        status = "partly-cited"
    else:
        status = "cited"

    return {
        "status": status,
        "citations_used": valid,
        "invalid_citations": invalid,
        "uncited_sentences": uncited,
        "numbers": numbers,
        "numbers_not_in_retrieved_passages": unsupported_numbers,
        "cited_sources": [
            {"n": n, "passage_id": hits[n - 1].passage.id, "path": hits[n - 1].passage.path,
             "location": hits[n - 1].passage.location, "title": hits[n - 1].passage.title}
            for n in valid
        ],
    }


STATUS_TEXT = {
    "cited": "every factual sentence cites a retrieved passage",
    "partly-cited": "some sentences have no citation",
    "uncited": "no valid citations; treat the answer as unsupported",
    "citation-problem": "a citation points to nothing, or a number is not in any retrieved passage",
    "insufficient-evidence": "model reported that the sources do not contain the answer",
}

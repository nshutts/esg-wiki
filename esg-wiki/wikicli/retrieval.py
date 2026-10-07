"""The retrieval tool: a local index plus hybrid (keyword + semantic) search.

Index files live in data/ (outside the Obsidian vault):
  data/passages.jsonl   one passage per line (original source passages + wiki note sections)
  data/embeddings.npy   one normalized EmbeddingGemma vector per passage (same order)
  data/index_meta.json  models, hashes, and build time

Search = BM25 ranking + cosine-similarity ranking, merged with Reciprocal Rank
Fusion (RRF). If the embedding model is unavailable, search falls back to BM25
only and says so.
"""
from __future__ import annotations

import json
import math
import re
import time
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .extract import Passage
from .llm import LLMError, OllamaClient, embed_doc_text, embed_query_text

STOPWORDS = set("""
a an and are as at be by can do does for from has have how i in is it its of on or that the
their them there these this to was what when where which who why will with within would you your
about into than then they we our us may must also any all each other such so if not no
""".split())

TOKEN = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    return [t for t in TOKEN.findall(text.lower()) if t not in STOPWORDS]


class BM25:
    """Okapi BM25, written out so the scoring is easy to follow."""

    def __init__(self, docs: list[list[str]], k1: float = 1.5, b: float = 0.75):
        self.k1, self.b = k1, b
        self.docs = [Counter(d) for d in docs]
        self.lens = [len(d) for d in docs]
        self.avg = (sum(self.lens) / len(self.lens)) if self.lens else 0.0
        df = Counter()
        for d in self.docs:
            df.update(d.keys())
        n = len(docs)
        self.idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}

    def scores(self, query: list[str]) -> np.ndarray:
        out = np.zeros(len(self.docs), dtype=np.float32)
        for i, (tf, dl) in enumerate(zip(self.docs, self.lens)):
            s = 0.0
            for t in query:
                f = tf.get(t)
                if not f:
                    continue
                s += self.idf[t] * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * dl / self.avg))
            out[i] = s
        return out


@dataclass
class Hit:
    passage: Passage
    score: float                  # fused RRF score (or single-method score)
    bm25_score: float = 0.0
    bm25_rank: int | None = None
    cosine: float | None = None
    vector_rank: int | None = None

    def to_dict(self) -> dict:
        d = self.passage.to_dict()
        d.update(location=self.passage.location, score=round(float(self.score), 5),
                 bm25_score=round(float(self.bm25_score), 3), bm25_rank=self.bm25_rank,
                 cosine=None if self.cosine is None else round(float(self.cosine), 4),
                 vector_rank=self.vector_rank)
        return d


def index_text(p: Passage) -> str:
    """What the retrievers see: section heading + passage text."""
    return f"{p.section}. {p.text}" if p.section else p.text


# --------------------------------------------------------------------------
# Index storage
# --------------------------------------------------------------------------

def save_index(data_dir: Path, passages: list[Passage], embeddings: np.ndarray | None, meta: dict) -> None:
    data_dir.mkdir(parents=True, exist_ok=True)
    with open(data_dir / "passages.jsonl", "w", encoding="utf-8") as f:
        for p in passages:
            f.write(json.dumps(p.to_dict(), ensure_ascii=False) + "\n")
    emb_path = data_dir / "embeddings.npy"
    if embeddings is not None:
        np.save(emb_path, embeddings)
    elif emb_path.exists():
        emb_path.unlink()
    meta = dict(meta, built_at=time.strftime("%Y-%m-%d %H:%M:%S"), passages=len(passages),
                has_embeddings=embeddings is not None)
    (data_dir / "index_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")


def load_passages(data_dir: Path) -> list[Passage]:
    path = data_dir / "passages.jsonl"
    if not path.exists():
        return []
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            out.append(Passage(**json.loads(line)))
    return out


def embed_passages(client: OllamaClient, model: str, passages: list[Passage]) -> np.ndarray:
    return client.embed(model, [embed_doc_text(p.section or p.title, p.text) for p in passages])


# --------------------------------------------------------------------------
# Retriever
# --------------------------------------------------------------------------

class Retriever:
    def __init__(self, data_dir: Path, settings, client: OllamaClient | None):
        self.settings = settings
        self.client = client
        self.passages = load_passages(data_dir)
        if not self.passages:
            raise FileNotFoundError("No retrieval index found. Run:  wiki ingest")
        meta_path = data_dir / "index_meta.json"
        self.meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
        emb_path = data_dir / "embeddings.npy"
        self.embeddings = np.load(emb_path) if emb_path.exists() else None
        r = settings.retrieval
        self.bm25 = BM25([tokenize(index_text(p)) for p in self.passages], r["bm25_k1"], r["bm25_b"])
        self.notice = ""

    def search(self, query: str, k: int, kinds=("source",), method: str | None = None) -> list[Hit]:
        r = self.settings.retrieval
        method = method or r["method"]
        self.notice = ""
        allowed = [i for i, p in enumerate(self.passages) if p.kind in kinds]
        if not allowed:
            return []
        n_cand = r["candidates"]

        # 1) keyword ranking
        bm = self.bm25.scores(tokenize(query))
        bm_order = [i for i in sorted(allowed, key=lambda i: -bm[i]) if bm[i] > 0][:n_cand]
        bm_rank = {i: rank for rank, i in enumerate(bm_order, start=1)}

        # 2) semantic ranking
        cos = None
        vec_rank: dict[int, int] = {}
        if method in ("hybrid", "semantic"):
            if self.embeddings is None:
                self.notice = "No embeddings in the index; using keyword search only."
            else:
                try:
                    q = self.client.embed(self.settings.embedder, [embed_query_text(query)])[0]
                    cos = self.embeddings @ q
                    vec_order = sorted(allowed, key=lambda i: -cos[i])[:n_cand]
                    vec_rank = {i: rank for rank, i in enumerate(vec_order, start=1)}
                except (LLMError, AttributeError) as e:
                    self.notice = f"Embedding model unavailable ({e.__class__.__name__}); using keyword search only."
                    cos = None

        # 3) fuse
        if cos is None or method == "keyword":
            ranked = [(i, float(bm[i])) for i in bm_order]
        elif method == "semantic":
            ranked = [(i, float(cos[i])) for i in sorted(vec_rank, key=vec_rank.get)]
        else:
            kk = r["rrf_k"]
            fused: dict[int, float] = {}
            for ranks in (bm_rank, vec_rank):
                for i, rank in ranks.items():
                    fused[i] = fused.get(i, 0.0) + 1.0 / (kk + rank)
            ranked = sorted(fused.items(), key=lambda x: -x[1])

        hits = []
        for i, score in ranked[:k]:
            hits.append(Hit(passage=self.passages[i], score=score, bm25_score=float(bm[i]),
                            bm25_rank=bm_rank.get(i), cosine=None if cos is None else float(cos[i]),
                            vector_rank=vec_rank.get(i)))
        return hits

    def best_keyword_score(self, query: str) -> float:
        s = self.bm25.scores(tokenize(query))
        return float(s.max()) if len(s) else 0.0

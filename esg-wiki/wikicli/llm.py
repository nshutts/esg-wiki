"""Thin client for the local Ollama server (generation + embeddings).

Only the Python standard library is used for HTTP, so the calls are easy to
trace: every request is a JSON POST to http://127.0.0.1:11434/api/...
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from typing import Callable, Iterable

import numpy as np


class LLMError(Exception):
    pass


class OllamaUnavailable(LLMError):
    pass


class ModelMissing(LLMError):
    pass


class OllamaClient:
    def __init__(self, base_url: str, timeout: int = 600):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    # --- low level ---------------------------------------------------------
    def _request(self, path: str, payload: dict | None = None, stream: bool = False, timeout: float | None = None):
        url = f"{self.base_url}{path}"
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, method="POST" if data else "GET",
                                     headers={"Content-Type": "application/json"})
        try:
            resp = urllib.request.urlopen(req, timeout=timeout or self.timeout)
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")
            model = (payload or {}).get("model", "")
            if e.code == 404 and "not found" in body.lower():
                raise ModelMissing(
                    f"Model '{model}' is not installed in Ollama. While online, run:  ollama pull {model}"
                ) from None
            raise LLMError(f"Ollama returned HTTP {e.code} for {path}: {body[:300]}") from None
        except (urllib.error.URLError, ConnectionError, TimeoutError) as e:
            raise OllamaUnavailable(
                f"Cannot reach Ollama at {self.base_url} ({getattr(e, 'reason', e)}). "
                "Start it by opening the Ollama app or running:  ollama serve"
            ) from None
        if stream:
            return resp
        with resp:
            return json.loads(resp.read().decode("utf-8"))

    # --- info --------------------------------------------------------------
    def version(self) -> str:
        return self._request("/api/version", timeout=5).get("version", "?")

    def list_models(self) -> list[dict]:
        return self._request("/api/tags", timeout=10).get("models", [])

    def loaded_models(self) -> list[dict]:
        return self._request("/api/ps", timeout=10).get("models", [])

    def show(self, model: str) -> dict:
        return self._request("/api/show", {"model": model}, timeout=30)

    def is_up(self) -> bool:
        try:
            self.version()
            return True
        except LLMError:
            return False

    # --- generation --------------------------------------------------------
    def chat(self, model: str, messages: list[dict], options: dict | None = None,
             think: bool = False, on_token: Callable[[str], None] | None = None) -> dict:
        """Send a chat request. Streams tokens to on_token if given.

        Returns {"text", "stats"} where stats holds Ollama's timing counters.
        """
        options = dict(options or {})
        payload = {"model": model, "messages": messages, "stream": True,
                   "options": options, "think": think}
        t0 = time.perf_counter()
        resp = self._request("/api/chat", payload, stream=True)
        parts: list[str] = []
        final: dict = {}
        first_token_at = None
        with resp:
            for raw_line in resp:
                line = raw_line.decode("utf-8").strip()
                if not line:
                    continue
                msg = json.loads(line)
                if "error" in msg:
                    raise LLMError(f"Ollama error: {msg['error']}")
                piece = (msg.get("message") or {}).get("content", "")
                if piece:
                    if first_token_at is None:
                        first_token_at = time.perf_counter()
                    parts.append(piece)
                    if on_token:
                        on_token(piece)
                if msg.get("done"):
                    final = msg
                    break
        wall = time.perf_counter() - t0
        ns = 1e9
        eval_count = final.get("eval_count", 0) or 0
        eval_dur = (final.get("eval_duration", 0) or 0) / ns
        stats = {
            "wall_seconds": round(wall, 2),
            "time_to_first_token_seconds": round((first_token_at - t0), 2) if first_token_at else None,
            "load_seconds": round((final.get("load_duration", 0) or 0) / ns, 2),
            "prompt_tokens": final.get("prompt_eval_count"),
            "prompt_eval_seconds": round((final.get("prompt_eval_duration", 0) or 0) / ns, 2),
            "output_tokens": eval_count,
            "output_tokens_per_second": round(eval_count / eval_dur, 1) if eval_dur else None,
            "done_reason": final.get("done_reason"),
        }
        return {"text": "".join(parts).strip(), "stats": stats}

    # --- embeddings --------------------------------------------------------
    def embed(self, model: str, texts: Iterable[str], batch_size: int = 16) -> np.ndarray:
        texts = list(texts)
        out: list[list[float]] = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            res = self._request("/api/embed", {"model": model, "input": batch})
            out.extend(res["embeddings"])
        arr = np.asarray(out, dtype=np.float32)
        norms = np.linalg.norm(arr, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return arr / norms


# EmbeddingGemma was trained with task prefixes; using them improves retrieval.
def embed_query_text(q: str) -> str:
    return f"task: search result | query: {q}"


def embed_doc_text(title: str, text: str) -> str:
    return f"title: {title or 'none'} | text: {text}"

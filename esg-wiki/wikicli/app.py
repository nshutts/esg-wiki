"""Shared harness state: settings, the local model client, the retriever, and
small terminal helpers. Every CLI command gets one App."""
from __future__ import annotations

import os
import sys

from .config import load_settings
from .llm import OllamaClient
from .retrieval import Retriever


class App:
    def __init__(self):
        self.settings = load_settings()
        self.paths = self.settings.paths
        self.client = OllamaClient(self.settings.ollama_url, self.settings.timeout)
        self._retriever: Retriever | None = None

    @property
    def retriever(self) -> Retriever:
        if self._retriever is None:
            self._retriever = Retriever(self.paths.data, self.settings, self.client)
        return self._retriever

    def reset_retriever(self):
        self._retriever = None

    def rel(self, path) -> str:
        try:
            return str(path.relative_to(self.paths.root))
        except ValueError:
            return str(path)


# ---- terminal helpers ------------------------------------------------------

_COLOR = sys.stdout.isatty() and os.environ.get("NO_COLOR") is None


def style(text: str, code: str) -> str:
    return f"\033[{code}m{text}\033[0m" if _COLOR else text


def dim(t: str) -> str:
    return style(t, "2")


def bold(t: str) -> str:
    return style(t, "1")


def green(t: str) -> str:
    return style(t, "32")


def yellow(t: str) -> str:
    return style(t, "33")


def red(t: str) -> str:
    return style(t, "31")


def cyan(t: str) -> str:
    return style(t, "36")


def stream_print(piece: str) -> None:
    sys.stdout.write(piece)
    sys.stdout.flush()

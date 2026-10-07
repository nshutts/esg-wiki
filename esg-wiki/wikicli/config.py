"""Project paths and settings.

Everything the harness reads or writes is located relative to the project root,
so the CLI works from any directory inside the project (or with WIKI_HOME set).
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse

import yaml


class ConfigError(Exception):
    pass


def find_root() -> Path:
    env = os.environ.get("WIKI_HOME")
    if env:
        return Path(env).expanduser().resolve()
    here = Path.cwd().resolve()
    for p in [here, *here.parents]:
        if (p / "config" / "settings.yaml").exists():
            return p
    # Fall back to the folder that contains this package.
    pkg_root = Path(__file__).resolve().parent.parent
    if (pkg_root / "config" / "settings.yaml").exists():
        return pkg_root
    raise ConfigError(
        "Could not find the project folder (config/settings.yaml). "
        "Run wiki from inside the project, or set WIKI_HOME to its path."
    )


@dataclass
class Paths:
    root: Path
    config: Path = field(init=False)
    vault: Path = field(init=False)
    raw: Path = field(init=False)
    wiki: Path = field(init=False)
    data: Path = field(init=False)
    evidence: Path = field(init=False)
    drafts: Path = field(init=False)
    tests: Path = field(init=False)

    def __post_init__(self):
        r = self.root
        self.config = r / "config"
        self.vault = r / "vault"
        self.raw = self.vault / "raw"
        self.wiki = self.vault / "wiki"
        self.data = r / "data"            # retrieval index: outside the vault on purpose
        self.evidence = r / "evidence"    # saved runs: outside the vault on purpose
        self.drafts = r / "drafts"        # chat /save output: never treated as evidence
        self.tests = r / "tests"


@dataclass
class Settings:
    paths: Paths
    raw: dict

    # convenience accessors -------------------------------------------------
    @property
    def ollama_url(self) -> str:
        return self.raw["ollama"]["url"].rstrip("/")

    @property
    def timeout(self) -> int:
        return int(self.raw["ollama"].get("timeout_seconds", 600))

    @property
    def generator(self) -> str:
        return self.raw["models"]["generator"]

    @property
    def embedder(self) -> str:
        return self.raw["models"]["embedder"]

    @property
    def think(self) -> bool:
        return bool(self.raw["models"].get("think", False))

    def gen(self, mode: str) -> dict:
        return dict(self.raw["generation"][mode])

    @property
    def retrieval(self) -> dict:
        return self.raw["retrieval"]

    @property
    def chunking(self) -> dict:
        return self.raw["chunking"]

    @property
    def chat(self) -> dict:
        return self.raw["chat"]

    @property
    def ingest(self) -> dict:
        return self.raw["ingest"]


LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1", "0.0.0.0"}


def load_settings(root: Path | None = None) -> Settings:
    paths = Paths(root or find_root())
    with open(paths.config / "settings.yaml", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    s = Settings(paths=paths, raw=raw)
    host = urlparse(s.ollama_url).hostname or ""
    if host not in LOCAL_HOSTS:
        raise ConfigError(
            f"ollama.url is {s.ollama_url}, which is not on this computer. "
            "Local mode only talks to a local Ollama server."
        )
    return s


def load_yaml(path: Path) -> dict:
    if not path.exists():
        raise ConfigError(f"Missing file: {path}")
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_sources(s: Settings) -> list[dict]:
    return load_yaml(s.paths.config / "sources.yaml").get("sources", [])


def load_topics(s: Settings) -> dict:
    return load_yaml(s.paths.config / "topics.yaml")

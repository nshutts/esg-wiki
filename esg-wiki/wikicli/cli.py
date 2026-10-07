"""Command-line entry point: `wiki <command>`.

This is the only place that reads the user's command and picks a mode:
  ingest -> ingest.run_ingest     search -> search.print_search (no model)
  ask    -> ask.run_ask (RAG)     chat   -> chat.interactive
  test / modecheck -> evaluate    status -> device, network, model check
"""
from __future__ import annotations

import argparse
import sys
import time

from .config import ConfigError

DESCRIPTION = """Personal ESG wiki: a local Gemma model + your own sources, fully offline.

Commands
  ingest    read sources in vault/raw/, write linked wiki notes, rebuild the index
  search    show original passages that match (no model answer)
  ask       standalone factual answer with citations, or "insufficient evidence"
  chat      talk with Ledger, the assistant; it looks up notes only when needed
  test      run the four ask-mode test questions and save evidence cards
  modecheck run the chat/search/ask boundary checks and save a transcript
  status    device specs, network state, Ollama and model check

Configuration: config/settings.yaml (models, retrieval, context sizes),
config/sources.yaml (source catalog), config/topics.yaml (wiki topic map),
persona.md (chat voice), wiki-instructions.md (ask rules),
ingest-instructions.md (note-writing rules).
Required: Ollama running locally with the models in settings.yaml pulled."""

EPILOG = """Examples
  wiki status
  wiki ingest                         # all of vault/raw/
  wiki ingest vault/raw/Novata_news.pdf --force
  wiki search "double materiality"
  wiki ask "What revenue threshold puts a company in scope of California SB 253?"
  wiki chat
  wiki test
  wiki modecheck"""


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="wiki", description=DESCRIPTION, epilog=EPILOG,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="command", metavar="<command>")

    g = sub.add_parser("ingest", help="build wiki notes and the index from vault/raw/")
    g.add_argument("path", nargs="?", help="a file or folder inside vault/raw/ (default: vault/raw/)")
    g.add_argument("--force", action="store_true", help="rewrite notes even if their evidence is unchanged")
    g.add_argument("--overwrite-reviewed", action="store_true", help="also rewrite notes marked reviewed: true")
    g.add_argument("--index-only", action="store_true", help="skip note writing; only rebuild the index")

    g = sub.add_parser("search", help="show matching original passages (no model answer)")
    g.add_argument("query", nargs="+")
    g.add_argument("-k", type=int, default=5, help="number of passages (default 5)")
    g.add_argument("--wiki", action="store_true", help="include generated wiki note sections")
    g.add_argument("--method", choices=["hybrid", "keyword", "semantic"], help="override retrieval method")
    g.add_argument("--save", action="store_true", help="save the results to evidence/search/")

    g = sub.add_parser("ask", help="cited answer from your sources")
    g.add_argument("question", nargs="+")
    g.add_argument("--mode", choices=["local", "online"], default="local",
                   help="where the model runs (only local is implemented; it is the default)")
    g.add_argument("-k", type=int, help="number of passages to give the model")
    g.add_argument("--no-save", action="store_true", help="do not save an evidence card")

    g = sub.add_parser("chat", help="talk with the assistant")
    g.add_argument("--mode", choices=["local", "online"], default="local")

    g = sub.add_parser("test", help="run the ask-mode test set in tests/questions.yaml")
    g.add_argument("--only", type=int, nargs="*", help="test numbers to run, e.g. --only 1 4")

    sub.add_parser("modecheck", help="run the chat/search/ask boundary checks")

    g = sub.add_parser("status", help="device, network, runtime and model check")
    g.add_argument("--save", action="store_true", help="save to evidence/status/")

    sub.add_parser("help", help="show this help")
    return p


def cmd_status(app, save: bool) -> None:
    from .app import bold, green, red, yellow
    from .runinfo import (device_info, memory_snapshot, model_identity, network_state,
                          runtime_identity, save_evidence, stamp)
    s = app.settings
    net = network_state()
    dev = device_info(app.paths.root)
    rt = runtime_identity(app.client)
    gen = model_identity(app.client, s.generator)
    emb = model_identity(app.client, s.embedder)
    print(bold("Device"))
    for k, v in dev.items():
        print(f"  {k}: {v}")
    print(bold("Network"))
    print("  internet: " + (yellow("online") if net == "online" else green("offline")))
    print(bold("Runtime"))
    ok = rt["version"] != "not reachable"
    print(f"  {rt['runtime']} {rt['version']} at {rt['url']} " + (green("[ok]") if ok else red("[not running]")))
    print(bold("Models"))
    for m in (gen, emb):
        if m.get("installed") is False:
            print(red(f"  {m['name']}: not installed. While online:  ollama pull {m['name']}"))
        else:
            print(f"  {m['name']}: {m.get('parameter_size')} {m.get('quantization')} "
                  f"{m.get('size_gb')} GB digest {m.get('digest')}")
    loaded = memory_snapshot(app.client)
    for m in loaded:
        print(f"  loaded now: {m['model']} {m['loaded_size_gb']} GB (GPU {m['in_gpu_memory_gb']} GB)")
    idx = app.paths.data / "index_meta.json"
    print(bold("Index"))
    if idx.exists():
        import json
        meta = json.loads(idx.read_text())
        print(f"  {meta.get('passages')} passages, embeddings: {meta.get('has_embeddings')}, built {meta.get('built_at')}")
    else:
        print(yellow("  not built yet: run  wiki ingest"))
    if save:
        rec = {"timestamp": stamp(), "network": net, "device": dev, "runtime": rt,
               "generator": gen, "embedder": emb, "loaded": loaded}
        md = ["# Status", "", f"- Time: {rec['timestamp']}", f"- Network: **{net}**",
              f"- Runtime: {rt['runtime']} {rt['version']}", ""]
        md += [f"- {k}: {v}" for k, v in dev.items()]
        md += ["", f"- Generator: `{gen}`", f"- Embedder: `{emb}`", f"- Loaded: {loaded}", ""]
        path = save_evidence(app.paths.evidence, "status", time.strftime("%Y-%m-%d_%H%M%S") + "-status",
                             rec, "\n".join(md))
        print(f"saved: {app.rel(path)}")


def main(argv: list[str] | None = None) -> int:
    import signal
    if hasattr(signal, "SIGPIPE"):
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)   # quiet exit when piped into `head`
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command in (None, "help"):
        parser.print_help()
        return 0
    if getattr(args, "mode", "local") == "online":
        print("Online mode is not implemented. Local mode is the default and runs fully offline.",
              file=sys.stderr)
        return 2

    from .app import App, red
    from .llm import LLMError
    try:
        app = App()
        if args.command == "status":
            cmd_status(app, args.save)
        elif args.command == "ingest":
            from .ingest import run_ingest
            run_ingest(app, args.path, force=args.force, overwrite_reviewed=args.overwrite_reviewed,
                       skip_notes=args.index_only)
        elif args.command == "search":
            from .search import print_search
            print_search(app, " ".join(args.query), k=args.k, include_wiki=args.wiki, method=args.method,
                         save=args.save)
        elif args.command == "ask":
            from .ask import run_ask
            run_ask(app, " ".join(args.question), k=args.k, save=not args.no_save)
        elif args.command == "chat":
            from .chat import interactive
            interactive(app)
        elif args.command == "test":
            from .evaluate import run_tests
            run_tests(app, args.only)
        elif args.command == "modecheck":
            from .evaluate import run_modecheck
            run_modecheck(app)
    except (ConfigError, LLMError, FileNotFoundError, ValueError) as e:
        print(red(f"error: {e}"), file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\ninterrupted", file=sys.stderr)
        return 130
    return 0


if __name__ == "__main__":
    sys.exit(main())

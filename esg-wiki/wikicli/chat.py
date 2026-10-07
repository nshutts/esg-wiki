"""Chat mode: the personal assistant ("Ledger").

Differences from ask mode, all enforced here:
  - system prompt = persona.md + the real command list (not the research rules)
  - conversation history is kept and sent, trimmed to a word budget
  - retrieval happens only when the router decides the message needs notes
  - retrieved passages are attached to that one turn only; history keeps the
    reply and a short source list, not the passages
  - drafts are saved only on /save, into drafts/ (never the vault, never evidence)
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass, field

from . import citations
from .app import App, bold, cyan, dim, stream_print, yellow
from .config import load_topics
from .prompts import format_passages, load_instructions
from .runinfo import network_state, save_evidence, slugify, stamp

COMMANDS = """Chat commands:
  /notes <question>   force a notes lookup for this message
  /search <words>     show matching original passages (no answer generated)
  /save [name]        save the last reply to drafts/ (kept apart from evidence)
  /reset              clear the conversation
  /help               show this list
  /exit               end the chat (the transcript is saved to evidence/chat/)"""

# --------------------------------------------------------------------------
# Router: does this message need the notes?
# --------------------------------------------------------------------------

CONVERSATIONAL = re.compile(
    r"^\s*(hi|hello|hey|thanks|thank you|ok|okay|cool|great|good (morning|afternoon|evening))\b"
    r"|what can (you|we) (do|help)|what do you do|who are you|how (can|do) (you|i) (help|use)"
    r"|help me with\??$|what are you able", re.I)
FOLLOW_UP = re.compile(
    r"\b(make|keep) (that|it|this|them)\b|\b(shorter|longer|simpler|more formal|less formal|punchier)\b"
    r"|\b(rephrase|reword|rewrite|shorten|condense|expand|simplify|summari[sz]e) (that|this|it)\b"
    r"|\b(turn|convert|put) (that|this|it) into\b|\bas (bullets|a table|an email)\b|^\s*(again|another one)\b",
    re.I)
FACT_CUES = re.compile(
    r"\b(what|when|which|who|how many|how much|does|do|is|are|threshold|deadline|penalt|scope|apply|"
    r"require|difference|compare|explain|define)\b", re.I)


@dataclass
class Decision:
    retrieve: bool
    reason: str
    query: str = ""


class Router:
    def __init__(self, app: App):
        topics = load_topics(app.settings).get("topics", [])
        terms = set()
        for t in topics:
            terms.add(t["name"])
            terms.update(t.get("terms", []))
        # longest first so "IFRS S2" wins over "IFRS"
        self.terms = sorted(terms, key=len, reverse=True)
        self.app = app

    def domain_terms(self, text: str) -> list[str]:
        found = []
        for t in self.terms:
            if re.search(rf"(?<![\w-]){re.escape(t)}(?![\w-])", text, re.I if not t.isupper() else 0):
                found.append(t)
        return found

    def decide(self, message: str, has_history: bool) -> Decision:
        if message.lower().startswith("/notes"):
            q = message[6:].strip()
            return Decision(True, "you asked for a notes lookup (/notes)", q)
        if CONVERSATIONAL.search(message):
            return Decision(False, "conversational or about my capabilities")
        if has_history and FOLLOW_UP.search(message):
            return Decision(False, "follow-up on the previous reply; using the conversation")
        terms = self.domain_terms(message)
        if terms:
            return Decision(True, f"mentions {', '.join(terms[:3])}", message)
        if FACT_CUES.search(message) and self.app.retriever.best_keyword_score(message) > 4.0:
            return Decision(True, "factual question with strong keyword matches in the notes", message)
        return Decision(False, "no ESG topic detected; answering from the conversation")


# --------------------------------------------------------------------------
# Session
# --------------------------------------------------------------------------

@dataclass
class Turn:
    role: str
    content: str
    meta: dict = field(default_factory=dict)


class ChatSession:
    def __init__(self, app: App):
        self.app = app
        s = app.settings
        self.system = load_instructions(s.paths.root, "persona.md") + "\n\n## Commands the user can type\n\n" + COMMANDS
        self.router = Router(app)
        self.history: list[Turn] = []
        self.log: list[dict] = []          # full transcript for evidence
        self.last_reply = ""
        self.started = time.strftime("%Y-%m-%d_%H%M%S")
        self.network = network_state()

    # history trimming: keep the newest turns within the word budget
    def _history_messages(self) -> list[dict]:
        budget = self.app.settings.chat["history_word_budget"]
        kept, used = [], 0
        for t in reversed(self.history):
            w = len(t.content.split())
            if used + w > budget and kept:
                break
            kept.append({"role": t.role, "content": t.content})
            used += w
        return list(reversed(kept))

    def respond(self, message: str, echo: bool = True) -> dict:
        s = self.app.settings
        decision = self.router.decide(message, bool(self.history))
        user_text = decision.query if message.lower().startswith("/notes") else message
        hits = []
        if decision.retrieve and decision.query:
            hits = self.app.retriever.search(decision.query, k=s.retrieval["chat_top_k"],
                                             kinds=("source", "wiki"))
        if echo:
            if hits:
                print(dim(f"[notes: retrieved {len(hits)} passages, {decision.reason}]"))
                for n, h in enumerate(hits, 1):
                    print(dim(f"  [{n}] {h.passage.title}, {h.passage.location or h.passage.section}"))
            else:
                print(dim(f"[notes: not searched, {decision.reason}]"))

        turn_content = user_text
        if hits:
            turn_content = (
                f"{user_text}\n\n---\nNotes retrieved for this message (cite as [n]; wiki notes are "
                f"generated summaries, sources are originals):\n\n{format_passages(hits)}"
            )
        messages = [{"role": "system", "content": self.system}] + self._history_messages() + \
                   [{"role": "user", "content": turn_content}]

        if echo:
            print(cyan("Ledger: "), end="")
        result = self.app.client.chat(s.generator, messages, options=s.gen("chat"), think=s.think,
                                      on_token=stream_print if echo else None)
        reply = result["text"]
        if echo:
            print()

        chk = citations.check(reply, hits) if hits else None
        source_note = ""
        if hits and chk and chk["cited_sources"]:
            source_note = "\n\nSources: " + "; ".join(
                f"[{c['n']}] {c['title']}, {c['location']}" for c in chk["cited_sources"])
            if echo:
                print(dim(source_note.strip()))
        if echo and hits and chk and chk["invalid_citations"]:
            print(yellow(f"(citation check: {chk['invalid_citations']} point to no retrieved passage)"))

        # History keeps what was said, not the retrieved passages.
        self.history.append(Turn("user", user_text))
        self.history.append(Turn("assistant", reply + source_note))
        self.last_reply = reply + source_note
        entry = {"user": message, "retrieval": {"retrieved": bool(hits), "reason": decision.reason,
                                                "passages": [h.to_dict() for h in hits]},
                 "reply": reply, "citation_check": chk, "timing": result["stats"],
                 "history_messages_sent": len(messages) - 2}
        self.log.append(entry)
        return entry

    def save_draft(self, name: str = "") -> str:
        if not self.last_reply:
            return "Nothing to save yet."
        d = self.app.paths.drafts
        d.mkdir(parents=True, exist_ok=True)
        fname = f"{time.strftime('%Y-%m-%d_%H%M%S')}-{slugify(name or 'chat-draft')}.md"
        (d / fname).write_text(
            f"<!-- chat draft saved by the user; generated text, NOT source evidence -->\n\n{self.last_reply}\n",
            encoding="utf-8")
        return f"Saved to drafts/{fname} (drafts are not indexed and never used as evidence)."

    def save_transcript(self, kind: str = "chat", name: str | None = None) -> str | None:
        if not self.log:
            return None
        s = self.app.settings
        record = {"mode": "chat", "execution": "local", "network_at_start": self.network,
                  "network_at_save": network_state(), "timestamp": stamp(), "model": s.generator,
                  "turns": self.log}
        path = save_evidence(self.app.paths.evidence, kind, name or f"{self.started}-chat", record,
                             transcript_md(record))
        return self.app.rel(path)


def transcript_md(r: dict, title: str = "Chat transcript") -> str:
    lines = [f"# {title}", "",
             f"- Mode: chat · execution: {r['execution']} · model `{r['model']}`",
             f"- Network: {r['network_at_start']} at start, {r['network_at_save']} at save · {r['timestamp']}", ""]
    for i, t in enumerate(r["turns"], 1):
        ret = t["retrieval"]
        lines += [f"## Turn {i}", "", f"**You:** {t['user']}", "",
                  f"_Notes lookup: {'yes' if ret['retrieved'] else 'no'} ({ret['reason']})._", ""]
        for n, p in enumerate(ret["passages"], 1):
            lines.append(f"- [{n}] {p['title']}, {p['location'] or p['section']} (`{p['path']}`)")
        if ret["passages"]:
            lines.append("")
        lines += [f"**Ledger:** {t['reply']}", ""]
        if t.get("citation_check"):
            c = t["citation_check"]
            lines += [f"_Citation check: {c['status']}; invalid citations: {c['invalid_citations'] or 'none'}._", ""]
        lines += [f"_History messages sent: {t['history_messages_sent']} · model time "
                  f"{t['timing']['wall_seconds']} s_", ""]
    return "\n".join(lines)


def interactive(app: App) -> None:
    session = ChatSession(app)
    print(bold("Ledger") + dim(f" · chat mode · local model {app.settings.generator} · network: {session.network}"))
    print(dim("Type /help for commands, /exit to leave.\n"))
    try:
        while True:
            try:
                msg = input(bold("you> ")).strip()
            except EOFError:
                break
            if not msg:
                continue
            low = msg.lower()
            if low in ("/exit", "/quit", "exit", "quit"):
                break
            if low == "/help":
                print(COMMANDS)
                continue
            if low == "/reset":
                session.history.clear()
                print(dim("Conversation cleared."))
                continue
            if low.startswith("/save"):
                print(session.save_draft(msg[5:].strip()))
                continue
            if low.startswith("/search"):
                from .search import print_search
                print_search(app, msg[7:].strip(), k=5)
                continue
            session.respond(msg)
            print()
    except KeyboardInterrupt:
        print()
    path = session.save_transcript()
    if path:
        print(dim(f"Transcript saved: {path}"))

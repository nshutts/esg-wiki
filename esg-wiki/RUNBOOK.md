# Runbook: from zero to submitted

The order to run things on the Mac. Steps 1 to 4 happen while online. Step 6 is
the offline demonstration.

## 1. Install (online, about 15 minutes)

1. Download Ollama for macOS from https://ollama.com/download, move it to
   Applications, and open it once. A llama icon appears in the menu bar.
2. In Terminal:
   ```bash
   ollama --version
   ollama pull gemma4:e2b-it-qat     # 4.3 GB
   ollama pull embeddinggemma        # 622 MB
   ollama list                       # both should be listed
   ```
   If `pull` says the model needs a newer Ollama, update the app and retry.
3. In the project folder:
   ```bash
   cd ~/esg-wiki
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -e .
   wiki --help
   wiki status
   ```
   `wiki status` should show both models, their digests, and Ollama `[ok]`.

Close memory-heavy apps (browsers with many tabs, Slack) before running Gemma.
With 8 GB, the model needs the room.

## 2. First ingest (online or offline, about 10 to 20 minutes)

```bash
wiki ingest
```
The command writes 26 notes (3 source notes and 23 topic notes), `vault/index.md`,
`vault/Source Catalog.md` and the index in `data/`. It prints how long each note
took and how many flags it raised.

## 3. Review the wiki in Obsidian (the assignment requires this)

1. In Obsidian, choose "Open folder as vault" and select `vault/`. Do not open the whole project.
2. Open each note and check it against the original. Click the source links; they
   open the PDF at the right page. Pay special attention to anything listed under
   `review_flags` in the note's properties.
3. Fix any wrong statement **in the note**. Never change the originals.
4. When a note is right, set `reviewed: true` in its properties. Re-ingesting will
   then leave it alone.
5. Check that the graph uses the filter `path:wiki/` with attachments off. Take the
   three screenshots (an open note, index and page list, graph) and save them in
   `evidence/screenshots/`.

Then confirm re-ingest does not duplicate anything:
```bash
wiki ingest                 # every note should say "unchanged" or "reviewed, kept"
ls vault/wiki/*/            # same 26 files, same names
```

## 4. Dry run of the tests (online is fine)

```bash
wiki search "double materiality" --save
wiki test
wiki modecheck
```
Read the cards in `evidence/ask-tests/`. If retrieval misses an expected passage,
fix the retrieval before blaming the model (the assignment says so). Keep the
first result as evidence of what changed.

## 5. Record measurements

- Memory: every ask card lists what Ollama has loaded and the harness's peak memory.
  An Activity Monitor screenshot (Memory tab, "Memory Used" and the Ollama
  processes) during an answer is a good extra.
- Time: ask cards show model seconds and tokens per second. The ingest report shows
  total and per-note seconds.
- Copy these into the README tables.

## 6. Offline demonstration (the graded run)

1. Turn Wi-Fi off (and unplug Ethernet). Quit Terminal completely, then reopen it.
2. Start a recorded session:
   ```bash
   cd ~/esg-wiki && source .venv/bin/activate
   mkdir -p evidence/offline-demo
   script -q evidence/offline-demo/terminal-session.txt
   ```
3. Inside the recording:
   ```bash
   wiki status --save                                   # must show "internet: offline"
   wiki --help
   wiki ingest vault/raw/Global_Sustainability_Reporting_Standards_Executive_Briefing.pdf --force   # CLI ingestion, offline
   wiki test                                            # all four ask tests
   wiki modecheck                                       # chat, search and ask checks
   wiki search "supply chain human rights" --save
   wiki chat                                            # try: what can you help me with? / a short plan / make that shorter / /exit
   exit                                                 # ends the recording
   ```
   `--force` still skips notes marked `reviewed: true`, and it only touches notes
   built from that source. To show Gemma writing a note offline, untick `reviewed`
   on SEC Climate Rule first, then ingest the briefing it comes from:
   `wiki ingest vault/raw/Global_Sustainability_Reporting_Standards_Executive_Briefing.pdf --force`
4. Also record the screen (Cmd+Shift+5) or take screenshots showing Wi-Fi off and
   the commands running.
5. Turn Wi-Fi back on.

## 7. Write up and submit

1. Fill every ⟨fill in⟩ in the README from the evidence files.
2. In each test card, write the "Assessment" section by hand after opening the
   cited pages.
3. Write the Reflection section about one real failure or limitation.
4. Push to a public GitHub repo. `data/`, `drafts/` and `.venv/` are ignored; the
   model weights are not in the repo. Open the repo signed out to check that the links work.

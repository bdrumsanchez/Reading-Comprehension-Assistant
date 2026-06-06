# Reading Comprehension Assistant

A Python CLI that helps you understand complex concepts, vocabulary, and character developments in ebooks (`.txt` / `.md`). Uses OpenCode Zen for generation, local sentence-transformers for embeddings, and ChromaDB for retrieval.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

The app reads your Zen API key from `~/.local/share/opencode/auth.json` automatically. To override, set `OPENCODE_API_KEY` in `.env`.

> **Note:** The default model is `deepseek-v4-flash-free`, which is free on OpenCode Zen — no payment method required. To use a paid model, set `RCA_LLM_MODEL` in `.env` (e.g. `gpt-5-nano`) and add a payment method at <https://opencode.ai/workspace> if you see `CreditsError`.

## Usage

```bash
python main.py data/books/my_book/                  # index whole book
python main.py data/books/my_book/01_intro.md       # index single file
```

Interactive commands inside the REPL:

- `ask <question>` — answer grounded in the text
- `summarize` — chapter summary
- `notes` — bulleted study notes (concepts / vocab / characters)
- `define <term>` — vocabulary breakdown
- `eli5 <concept>` — simplified explanation
- `sources` — list the indexed books
- `help` — show commands
- `exit` — quit

## Layout

```
assistant/
  config.py     paths + tunables
  auth.py       Zen API key loader
  prompts.py    prompt templates
  loader.py     .txt / .md readers
  chunker.py    token-aware splitter
  embedder.py   local sentence-transformers + cache
  store.py      ChromaDB persistent store
  retriever.py  semantic search
  llm.py        OpenAI-compatible client → Zen
  qa.py         context-grounded Q&A
  summarizer.py summaries / notes / definitions
main.py         CLI entry
data/books/     your chapter files
data/cache/     embeddings + vector store
tests/          unit tests
```

## Adding a book

Drop files into `data/books/<book_name>/` with numeric prefixes for chapter order:

```
data/books/dune/
  01_arrakis.md
  02_bene_gesserit.md
```

Re-run `python main.py data/books/dune/` to (re)index — unchanged files are skipped.

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.patch_stdout import patch_stdout

from assistant.chunker import chunk_documents
from assistant.config import HISTORY_FILE, SETTINGS
from assistant.embedder import Embedder
from assistant.llm import LLM
from assistant.loader import discover_inputs, load_file
from assistant.qa import QA
from assistant.retriever import Retriever
from assistant.store import VectorStore
from assistant.summarizer import Summarizer

console = Console()


HELP_TEXT = """\
[bold]Commands[/bold]
  ask <question>        Answer a question grounded in the text
  summarize [chapter]   Summarize a chapter (default: first indexed)
  notes [chapter]       Bulleted study notes (concepts / vocab / plot)
  define <term>         Define a term as it is used in the text
  eli5 <concept>        Explain a concept in plain language
  sources               List indexed books & chapters
  help                  Show this help
  clear                 Clear the screen
  exit / quit           Leave the assistant
"""


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="reading-comprehension-assistant",
        description="Ask questions and get summaries of your ebooks.",
    )
    p.add_argument(
        "path",
        nargs="?",
        default="data/books",
        help="File or folder to index (default: data/books).",
    )
    p.add_argument(
        "--reindex",
        action="store_true",
        help="Drop existing index for affected books and rebuild.",
    )
    return p.parse_args()


def index_inputs(paths: list[Path], store: VectorStore, embedder: Embedder, force: bool = False) -> dict[str, int]:
    counts: dict[str, int] = {}
    for p in paths:
        try:
            doc = load_file(p)
        except (FileNotFoundError, ValueError) as e:
            console.print(f"[yellow]skip[/yellow] {p}: {e}")
            continue

        if force:
            store.delete_book(doc.book)
            existing: dict[str, str] = {}
        else:
            existing = store.file_hashes(doc.book)

        if doc.file_path in existing and existing[doc.file_path] == doc.content_hash:
            counts[doc.book] = counts.get(doc.book, 0)
            console.print(f"[dim]unchanged[/dim] {doc.book} / {doc.chapter}")
            continue

        chunks = chunk_documents([doc])
        if not chunks:
            console.print(f"[yellow]empty[/yellow] {p}")
            continue

        meta = {**chunks[0].metadata, "content_hash": doc.content_hash}
        chunks[0].metadata.update(meta)

        embeddings = embedder.embed_cached([c.text for c in chunks])
        store.add_chunks(doc.book, chunks, embeddings)
        counts[doc.book] = counts.get(doc.book, 0) + len(chunks)
        console.print(f"[green]indexed[/green] {doc.book} / {doc.chapter} ({len(chunks)} chunks)")
    return counts


def find_chapter_doc(book: str, chapter: str | None, store: VectorStore) -> tuple[str, str] | None:
    collection = store.get_or_create(book)
    res = collection.get(include=["metadatas", "documents"])
    metas = res.get("metadatas") or []
    chapters: dict[str, dict] = {}
    for meta, doc in zip(metas, res.get("documents") or []):
        ch = meta.get("chapter", "?")
        if ch not in chapters:
            chapters[ch] = {"meta": meta, "doc_text": doc}
    if not chapters:
        return None
    if chapter and chapter in chapters:
        return chapter, chapters[chapter]["doc_text"]
    chosen = sorted(chapters.keys())[0]
    return chosen, chapters[chosen]["doc_text"]


def render_sources(sources: list[dict]) -> None:
    if not sources:
        return
    table = Table(title="Sources", show_lines=False, header_style="bold")
    table.add_column("#", style="dim", width=3)
    table.add_column("Book")
    table.add_column("Chapter")
    table.add_column("Score", justify="right")
    for i, s in enumerate(sources, start=1):
        m = s["metadata"]
        table.add_row(
            str(i),
            str(m.get("book", "?")),
            str(m.get("chapter", "?")),
            f"{s.get('score', 0):.3f}",
        )
    console.print(table)


def render_sources_for_book(book: str, store: VectorStore) -> None:
    collection = store.get_or_create(book)
    res = collection.get(include=["metadatas"])
    chapters = sorted({(m.get("chapter") or "?") for m in (res.get("metadatas") or [])})
    if not chapters:
        console.print(f"[yellow]No chapters indexed for '{book}'.[/yellow]")
        return
    table = Table(title=f"Book: {book}", show_lines=False)
    table.add_column("#", style="dim", width=3)
    table.add_column("Chapter")
    n = collection.count()
    table.add_row(str(n), f"({n} chunks total)")
    for i, ch in enumerate(chapters, start=1):
        table.add_row(str(i), ch)
    console.print(table)


def main() -> int:
    args = parse_args()

    target = Path(args.path)
    try:
        paths = discover_inputs(target)
    except FileNotFoundError as e:
        console.print(f"[red]{e}[/red]")
        return 1

    console.print(Panel.fit("[bold]Reading Comprehension Assistant[/bold]", subtitle="indexing…"))

    store = VectorStore()
    embedder = Embedder()
    llm = LLM()
    retriever = Retriever(store, embedder)
    qa = QA(retriever, llm)
    summarizer = Summarizer(llm, retriever)

    counts = index_inputs(paths, store, embedder, force=args.reindex)
    if not counts:
        console.print("[red]Nothing was indexed.[/red]")
        return 1

    books = sorted(counts.keys())
    current_book = books[0]
    total = sum(counts.values())
    console.print(
        f"[green]Ready[/green] {len(books)} book(s), {total} new chunk(s). Current: [bold]{current_book}[/bold]"
    )

    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    session: PromptSession = PromptSession(history=FileHistory(str(HISTORY_FILE)))

    def run_command(line: str) -> bool:
        nonlocal current_book
        line = line.strip()
        if not line:
            return True
        parts = line.split(maxsplit=1)
        cmd = parts[0].lower()
        rest = parts[1].strip() if len(parts) > 1 else ""

        if cmd in {"exit", "quit", ":q"}:
            return False
        if cmd == "help":
            console.print(HELP_TEXT)
            return True
        if cmd == "clear":
            console.clear()
            return True
        if cmd == "sources":
            if rest:
                render_sources_for_book(rest, store)
            else:
                console.print(
                    "Indexed books: " + ", ".join(f"[bold]{b}[/bold]" for b in store.list_books())
                )
                console.print("Use `sources <book>` for chapter list, or `use <book>` to switch.")
            return True
        if cmd == "use":
            if not rest:
                console.print("[yellow]Usage:[/yellow] use <book>")
            elif rest not in store.list_books():
                console.print(f"[red]Not indexed:[/red] {rest}")
            else:
                current_book = rest
                console.print(f"Switched to [bold]{current_book}[/bold]")
            return True
        if cmd == "ask":
            if not rest:
                console.print("[yellow]Usage:[/yellow] ask <question>")
                return True
            with console.status("thinking…"):
                ans = qa.ask(current_book, rest)
            console.print(Markdown(ans.text))
            render_sources(ans.sources)
            return True
        if cmd == "summarize":
            chosen = find_chapter_doc(current_book, rest or None, store)
            if not chosen:
                console.print("[yellow]No chapters found.[/yellow]")
                return True
            chapter_name, _ = chosen
            doc = _doc_from_store(current_book, chapter_name, store)
            with console.status(f"summarizing {chapter_name}…"):
                result = summarizer.summarize(doc)
            console.print(
                Panel(
                    Markdown(result.text),
                    title=f"{doc.book} / {doc.chapter}" + (" (cached)" if result.cached else ""),
                )
            )
            return True
        if cmd == "notes":
            chosen = find_chapter_doc(current_book, rest or None, store)
            if not chosen:
                console.print("[yellow]No chapters found.[/yellow]")
                return True
            chapter_name, _ = chosen
            doc = _doc_from_store(current_book, chapter_name, store)
            with console.status(f"extracting notes for {chapter_name}…"):
                result = summarizer.notes(doc)
            console.print(
                Panel(
                    Markdown(result.text),
                    title=f"Notes — {doc.book} / {doc.chapter}" + (" (cached)" if result.cached else ""),
                )
            )
            return True
        if cmd == "define":
            if not rest:
                console.print("[yellow]Usage:[/yellow] define <term>")
                return True
            with console.status(f"looking up '{rest}'…"):
                result = summarizer.define(current_book, rest)
            console.print(Markdown(result.text) if result.text.startswith("#") else result.text)
            return True
        if cmd == "eli5":
            if not rest:
                console.print("[yellow]Usage:[/yellow] eli5 <concept>")
                return True
            with console.status(f"simplifying '{rest}'…"):
                result = summarizer.eli5(current_book, rest)
            console.print(Markdown(result.text) if result.text.startswith("#") else result.text)
            return True

        console.print(f"[red]Unknown command:[/red] {cmd}. Type `help`.")
        return True

    console.print(HELP_TEXT)
    try:
        while True:
            try:
                with patch_stdout():
                    line = session.prompt(f"📖 [{current_book}] > ")
            except KeyboardInterrupt:
                continue
            except EOFError:
                break
            if not run_command(line):
                break
    finally:
        console.print("[dim]bye[/dim]")
    return 0


def _doc_from_store(book: str, chapter: str, store: VectorStore) -> "Document":
    from assistant.loader import Document

    collection = store.get_or_create(book)
    res = collection.get(include=["metadatas", "documents"], where={"chapter": chapter})
    docs = res.get("documents") or []
    metas = res.get("metadatas") or []
    if not docs:
        return Document(
            book=book,
            chapter=chapter,
            title=chapter,
            author="",
            content="",
            file_path="",
            content_hash=chapter,
        )
    parts = []
    first_meta = metas[0] if metas else {}
    for d, m in zip(docs, metas):
        parts.append(d)
    return Document(
        book=book,
        chapter=chapter,
        title=first_meta.get("title", chapter),
        author=first_meta.get("author", ""),
        content="\n\n".join(parts),
        file_path=first_meta.get("file_path", ""),
        content_hash=first_meta.get("content_hash", chapter),
    )


if __name__ == "__main__":
    sys.exit(main())

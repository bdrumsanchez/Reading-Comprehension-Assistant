from assistant.chunker import chunk_document
from assistant.loader import Document


def _doc(content: str, chapter: str = "test", book: str = "book") -> Document:
    return Document(
        book=book,
        chapter=chapter,
        title=chapter,
        author="",
        content=content,
        file_path="",
        content_hash="h",
    )


def test_chunks_short_text_single() -> None:
    doc = _doc("Hello world. This is a short paragraph.")
    chunks = chunk_document(doc, target=100, overlap=10)
    assert len(chunks) == 1
    assert "Hello world" in chunks[0].text
    assert chunks[0].metadata["book"] == "book"
    assert chunks[0].metadata["chapter"] == "test"
    assert chunks[0].chunk_id


def test_chunks_long_text_multiple() -> None:
    paragraphs = [f"Paragraph {i}. " + ("word " * 200) for i in range(10)]
    doc = _doc("\n\n".join(paragraphs))
    chunks = chunk_document(doc, target=120, overlap=30)
    assert len(chunks) > 1
    for c in chunks:
        assert c.tokens <= 250
        assert c.text.strip()


def test_chunks_respect_paragraph_boundaries() -> None:
    content = "First paragraph here.\n\nSecond paragraph here.\n\nThird paragraph here."
    doc = _doc(content)
    chunks = chunk_document(doc, target=10, overlap=2)
    assert all("paragraph here." in c.text for c in chunks)


def test_chunks_have_stable_ids() -> None:
    doc = _doc("Alpha. Beta. Gamma." * 50)
    a = chunk_document(doc, target=50, overlap=10)
    b = chunk_document(doc, target=50, overlap=10)
    assert [c.chunk_id for c in a] == [c.chunk_id for c in b]

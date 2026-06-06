from pathlib import Path

import pytest

from assistant.loader import discover_inputs, load_file


def test_load_txt(tmp_path: Path) -> None:
    p = tmp_path / "book_one" / "01_intro.txt"
    p.parent.mkdir(parents=True)
    p.write_text("It was a dark and stormy night.", encoding="utf-8")

    doc = load_file(p)
    assert doc.book == "book_one"
    assert doc.chapter == "intro"
    assert "stormy night" in doc.content
    assert doc.content_hash
    assert doc.file_path.endswith("01_intro.txt")


def test_load_md_with_frontmatter(tmp_path: Path) -> None:
    p = tmp_path / "library" / "02_chapter.md"
    p.parent.mkdir(parents=True)
    p.write_text(
        "---\n"
        "title: A Custom Title\n"
        "author: Tester\n"
        "book: mybook\n"
        "chapter: Two\n"
        "---\n\n"
        "# Heading\n\nBody text here.\n",
        encoding="utf-8",
    )

    doc = load_file(p)
    assert doc.title == "A Custom Title"
    assert doc.author == "Tester"
    assert doc.book == "mybook"
    assert doc.chapter == "Two"
    assert "Body text here." in doc.content
    assert "# Heading" in doc.content


def test_discover_inputs(tmp_path: Path) -> None:
    (tmp_path / "a").mkdir()
    (tmp_path / "a" / "01.md").write_text("x", encoding="utf-8")
    (tmp_path / "a" / "02.txt").write_text("y", encoding="utf-8")
    (tmp_path / "a" / "notes.docx").write_text("ignore", encoding="utf-8")

    found = discover_inputs(tmp_path / "a")
    names = [p.name for p in found]
    assert names == ["01.md", "02.txt"]


def test_unsupported_extension(tmp_path: Path) -> None:
    p = tmp_path / "weird.docx"
    p.write_text("x", encoding="utf-8")
    with pytest.raises(ValueError):
        load_file(p)

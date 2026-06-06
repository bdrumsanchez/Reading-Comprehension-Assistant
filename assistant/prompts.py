from __future__ import annotations


SYSTEM_QA = (
    "You are a reading comprehension assistant. You answer questions strictly "
    "based on the provided passages from the user's ebook. Be clear, concise, "
    "and use simple language. If the answer is not in the passages, say so. "
    "When helpful, cite chapter or section names from the metadata."
)


SYSTEM_SUMMARIZER = (
    "You are a reading comprehension assistant. Produce a faithful, well-organized "
    "summary of the provided chapter text. Use simple language, preserve key terms, "
    "and stay grounded in the source. Do not invent details."
)


SYSTEM_NOTES = (
    "You are a reading comprehension assistant. From the provided chapter, extract "
    "concise study notes. Use three sections: 'Key Concepts', 'Vocabulary' "
    "(brief definitions of important or unusual terms), and 'Character & Plot "
    "Developments'. Use bullet points. Stay grounded in the source text."
)


SYSTEM_DEFINE = (
    "You are a reading comprehension assistant. Define the given term as it is used "
    "in the provided passages. Give a short, plain-language definition, then a brief "
    "excerpt or paraphrase of how the term is used in context. If the term is not "
    "present in the passages, say so and offer a general definition."
)


SYSTEM_ELI5 = (
    "You are a reading comprehension assistant. Explain the given concept from the "
    "passages as if to a curious beginner. Use a short analogy, plain words, and "
    "keep it to a few sentences. Stay grounded in the source text."
)


def qa_user_prompt(question: str, passages: list[dict]) -> str:
    blocks = []
    for i, p in enumerate(passages, start=1):
        meta = p["metadata"]
        header = f"[{i}] {meta.get('book', '?')} / {meta.get('chapter', '?')}"
        blocks.append(f"{header}\n{p['text']}")
    context = "\n\n---\n\n".join(blocks)
    return (
        f"Question: {question.strip()}\n\n"
        f"Passages (cite by [n] when relevant):\n\n{context}"
    )


def chapter_user_prompt(mode: str, chapter_label: str, content: str) -> str:
    return (
        f"Chapter: {chapter_label}\n\n"
        f"Text:\n{content}\n\n"
        f"Task: {mode}"
    )


def term_user_prompt(term: str, passages: list[dict]) -> str:
    blocks = []
    for i, p in enumerate(passages, start=1):
        meta = p["metadata"]
        header = f"[{i}] {meta.get('book', '?')} / {meta.get('chapter', '?')}"
        blocks.append(f"{header}\n{p['text']}")
    context = "\n\n---\n\n".join(blocks)
    return (
        f"Term: {term.strip()}\n\n"
        f"Passages:\n\n{context}"
    )


def concept_user_prompt(concept: str, passages: list[dict]) -> str:
    blocks = []
    for i, p in enumerate(passages, start=1):
        meta = p["metadata"]
        header = f"[{i}] {meta.get('book', '?')} / {meta.get('chapter', '?')}"
        blocks.append(f"{header}\n{p['text']}")
    context = "\n\n---\n\n".join(blocks)
    return (
        f"Concept: {concept.strip()}\n\n"
        f"Passages:\n\n{context}"
    )

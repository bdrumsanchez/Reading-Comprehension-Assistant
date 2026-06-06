from __future__ import annotations

from dataclasses import dataclass

from .llm import LLM
from .prompts import SYSTEM_QA, qa_user_prompt
from .retriever import Retriever


@dataclass
class Answer:
    text: str
    sources: list[dict]


class QA:
    def __init__(self, retriever: Retriever, llm: LLM) -> None:
        self.retriever = retriever
        self.llm = llm

    def ask(self, book: str, question: str, top_k: int | None = None) -> Answer:
        passages = self.retriever.retrieve(book, question, top_k=top_k)
        if not passages:
            return Answer(
                text=(
                    "I couldn't find any relevant passages in this book. "
                    "Have you indexed it? Try running the indexer again."
                ),
                sources=[],
            )
        user_prompt = qa_user_prompt(question, passages)
        text = self.llm.complete(SYSTEM_QA, user_prompt)
        return Answer(text=text, sources=passages)

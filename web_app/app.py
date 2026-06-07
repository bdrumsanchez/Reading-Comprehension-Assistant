from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

load_dotenv()

from assistant.llm import LLM

app = Flask(__name__)

SYSTEM_PROMPT = (
    "You are a reading comprehension assistant. The user has highlighted a passage "
    "from a book and may ask a question about it.\n\n"
    "Use the highlighted passage as your primary source. Be clear, concise, and use "
    "simple language. If the question cannot be answered from the passage, say so "
    "briefly — but you may also draw on general knowledge to clarify references, "
    "unfamiliar terms, or historical context. Keep the focus on helping the reader "
    "understand what the passage means."
)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/ask", methods=["POST"])
def ask():
    body = request.get_json(silent=True)
    if not body:
        return jsonify({"error": "Request body is required"}), 400

    passage = (body.get("passage") or "").strip()
    question = (body.get("question") or "").strip()

    if not passage:
        return jsonify({"error": "Passage is required"}), 400
    if not question:
        return jsonify({"error": "Question is required"}), 400

    user_prompt = (
        f"Highlighted passage:\n\"\"\"\n{passage}\n\"\"\"\n\n"
        f"Question: {question}\n"
    )

    try:
        llm = LLM()
        answer = llm.complete(SYSTEM_PROMPT, user_prompt)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500

    return jsonify({"answer": answer})


def main() -> None:
    app.run(host="0.0.0.0", port=5000, debug=True)


if __name__ == "__main__":
    main()

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from PySide6.QtCore import Qt, QEvent, QRect, QTimer, QObject, Signal, QThread, QSettings
from PySide6.QtGui import QAction, QCloseEvent, QColor, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSystemTrayIcon,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from assistant.llm import LLM
from assistant.store import VectorStore
from assistant.embedder import Embedder
from assistant.retriever import Retriever


SYSTEM_PROMPT = (
    "You are a reading comprehension assistant. The user has highlighted a passage "
    "from a book and may ask a question about it.\n\n"
    "Use the highlighted passage as your primary source. Be clear, concise, and use "
    "simple language. If the question cannot be answered from the passage, say so "
    "briefly — but you may also draw on general knowledge to clarify references, "
    "unfamiliar terms, or historical context. Keep the focus on helping the reader "
    "understand what the passage means."
)

MIN_SNIPPET_LEN = 3
POLL_INTERVAL_MS = 400


def build_snippet_prompt(snippet: str, question: str) -> str:
    return (
        f"Highlighted passage:\n\"\"\"\n{snippet.strip()}\n\"\"\"\n\n"
        f"Question: {question.strip()}\n"
    )


def build_grounded_prompt(snippet: str, question: str, passages: list[dict]) -> str:
    if passages:
        blocks = []
        for i, p in enumerate(passages, start=1):
            meta = p.get("metadata", {})
            header = f"[{i}] {meta.get('book', '?')} / {meta.get('chapter', '?')}"
            blocks.append(f"{header}\n{p['text']}")
        context = "\n\n---\n\n".join(blocks)
    else:
        context = "(no matching passages found in the indexed book)"
    return (
        f"Highlighted passage from the user:\n\"\"\"\n{snippet.strip()}\n\"\"\"\n\n"
        f"Retrieved passages from the indexed book:\n\n{context}\n\n"
        f"Question: {question.strip()}\n"
    )


def _build_tray_icon(active: bool) -> QIcon:
    pixmap = QPixmap(22, 18)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    color = QColor("#1c1c1c")
    painter.setPen(QPen(color, 1.4))
    painter.setBrush(color if active else Qt.NoBrush)
    painter.drawRoundedRect(QRect(3, 2, 16, 14), 1.5, 1.5)
    spine_color = QColor("#ffffff") if active else color
    painter.setPen(QPen(spine_color, 1.2))
    painter.drawLine(6, 3, 6, 15)
    if not active:
        painter.setPen(QPen(color, 1.6))
        painter.drawLine(4, 15, 20, 3)
    painter.end()
    icon = QIcon(pixmap)
    icon.setIsMask(True)
    return icon


class LLMWorker(QObject):
    finished = Signal(str)
    failed = Signal(str)

    def __init__(self, llm: LLM, system: str, user: str) -> None:
        super().__init__()
        self.llm = llm
        self.system = system
        self.user = user

    def run(self) -> None:
        try:
            text = self.llm.complete(self.system, self.user)
        except Exception as exc:
            self.failed.emit(str(exc))
            return
        self.finished.emit(text)


class ClipboardMonitor(QObject):
    newText = Signal(str)

    def __init__(self, app: QApplication, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._app = app
        self._clip = app.clipboard()
        try:
            self._last = self._clip.text() or ""
        except Exception:
            self._last = ""
        self._timer = QTimer(self)
        self._timer.setInterval(POLL_INTERVAL_MS)
        self._timer.timeout.connect(self._poll)
        self._active = False

    @property
    def is_active(self) -> bool:
        return self._active

    def start(self) -> None:
        if self._active:
            return
        try:
            self._last = self._clip.text() or ""
        except Exception:
            self._last = ""
        self._timer.start()
        self._active = True

    def stop(self) -> None:
        if not self._active:
            return
        self._timer.stop()
        self._active = False

    def _poll(self) -> None:
        try:
            text = self._clip.text()
        except Exception:
            return
        if not text or text == self._last:
            return
        if not text.strip():
            return
        self._last = text
        self.newText.emit(text)

    def mark_seen(self, text: str) -> None:
        self._last = text or ""


class PopupWindow(QWidget):
    visibility_changed = Signal(bool)

    def __init__(self, llm: LLM) -> None:
        super().__init__()
        self.llm = llm
        self._store: VectorStore | None = None
        self._embedder: Embedder | None = None
        self._retriever: Retriever | None = None
        self._current_snippet = ""
        self._thread: QThread | None = None
        self._worker: LLMWorker | None = None
        self._app_quitting = False

        self._settings = QSettings("ReadingAssistant", "FloatingPopup")

        self.setWindowTitle("Reading Assistant")
        self.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint)
        self.setMinimumSize(420, 460)
        self._build_ui()
        self._apply_style()
        self._restore_geometry()

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 12, 12, 12)
        outer.setSpacing(8)

        header_row = QHBoxLayout()
        title = QLabel("📖 Reading Assistant")
        title_font = title.font()
        title_font.setBold(True)
        title_font.setPointSize(title_font.pointSize() + 1)
        title.setFont(title_font)
        header_row.addWidget(title)
        header_row.addStretch(1)
        self.reset_btn = QPushButton("Reset")
        self.reset_btn.clicked.connect(self._on_reset)
        header_row.addWidget(self.reset_btn)
        outer.addLayout(header_row)

        book_row = QHBoxLayout()
        book_row.addWidget(QLabel("Ground in:"))
        self.book_combo = QComboBox()
        self.book_combo.addItem("Snippet only", userData=None)
        self.book_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        book_row.addWidget(self.book_combo, 1)
        self.refresh_btn = QPushButton("⟳")
        self.refresh_btn.setToolTip("Reload indexed books")
        self.refresh_btn.setFixedWidth(28)
        self.refresh_btn.clicked.connect(self._refresh_books)
        book_row.addWidget(self.refresh_btn)
        outer.addLayout(book_row)

        outer.addWidget(QLabel("Copied text:"))
        self.snippet_view = QTextEdit()
        self.snippet_view.setReadOnly(True)
        self.snippet_view.setPlaceholderText("Copy text from any app to start…")
        self.snippet_view.setMaximumHeight(160)
        outer.addWidget(self.snippet_view, 1)

        outer.addWidget(QLabel("Your question:"))
        ask_row = QHBoxLayout()
        self.question_input = QLineEdit()
        self.question_input.setPlaceholderText("e.g. What does this mean?")
        self.question_input.returnPressed.connect(self._on_ask)
        ask_row.addWidget(self.question_input, 1)
        self.ask_btn = QPushButton("Ask")
        self.ask_btn.clicked.connect(self._on_ask)
        ask_row.addWidget(self.ask_btn)
        outer.addLayout(ask_row)

        outer.addWidget(QLabel("Response:"))
        self.response_view = QTextEdit()
        self.response_view.setReadOnly(True)
        self.response_view.setPlaceholderText("The explanation will appear here.")
        outer.addWidget(self.response_view, 2)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #666;")
        outer.addWidget(self.status_label)

    def _apply_style(self) -> None:
        self.setStyleSheet(
            """
            QWidget { font-size: 13px; }
            QTextEdit {
                background: #fafafa;
                border: 1px solid #ccc;
                border-radius: 6px;
                padding: 6px;
            }
            QLineEdit {
                border: 1px solid #ccc;
                border-radius: 6px;
                padding: 6px;
                background: white;
            }
            QPushButton {
                border: 1px solid #bbb;
                border-radius: 6px;
                padding: 6px 12px;
                background: #f3f3f3;
            }
            QPushButton:hover { background: #e9e9e9; }
            QPushButton:pressed { background: #ddd; }
            QPushButton:disabled { color: #999; background: #f7f7f7; }
            QComboBox {
                border: 1px solid #ccc;
                border-radius: 6px;
                padding: 4px 8px;
                background: white;
            }
            """
        )

    def _restore_geometry(self) -> None:
        geom = self._settings.value("geometry")
        if geom is not None:
            self.restoreGeometry(geom)
        else:
            self.resize(460, 520)

    def _save_geometry(self) -> None:
        self._settings.setValue("geometry", self.saveGeometry())

    def _refresh_books(self) -> None:
        current = self.book_combo.currentData()
        self.book_combo.blockSignals(True)
        self.book_combo.clear()
        self.book_combo.addItem("Snippet only", userData=None)
        store = self._get_store()
        if store is not None:
            for b in store.list_books():
                self.book_combo.addItem(b, userData=b)
        if current is not None:
            idx = self.book_combo.findData(current)
            if idx >= 0:
                self.book_combo.setCurrentIndex(idx)
        self.book_combo.blockSignals(False)

    def _get_store(self) -> VectorStore | None:
        if self._store is None:
            try:
                self._store = VectorStore()
            except Exception as exc:
                self.status_label.setText(f"Index unavailable: {exc}")
                return None
        return self._store

    def _get_retriever(self) -> Retriever | None:
        if self._retriever is not None:
            return self._retriever
        store = self._get_store()
        if store is None:
            return None
        try:
            self._embedder = Embedder()
            self._retriever = Retriever(store, self._embedder)
        except Exception as exc:
            self.status_label.setText(f"Embedder unavailable: {exc}")
            return None
        return self._retriever

    def set_snippet(self, text: str) -> None:
        self._current_snippet = text
        self.snippet_view.setPlainText(text)
        self.response_view.clear()
        self.status_label.clear()

    def _on_reset(self) -> None:
        self._current_snippet = ""
        self.snippet_view.clear()
        self.response_view.clear()
        self.question_input.clear()
        self.status_label.clear()

    def _on_ask(self) -> None:
        if self._thread is not None:
            return
        snippet = self._current_snippet.strip()
        if not snippet:
            self.status_label.setText("No copied text to ask about.")
            return
        question = self.question_input.text().strip()
        if not question:
            question = "Explain this passage in plain language."
            self.question_input.setText(question)

        book = self.book_combo.currentData()
        if book:
            retriever = self._get_retriever()
            if retriever is not None:
                try:
                    passages = retriever.retrieve(book, question)
                except Exception as exc:
                    passages = []
                    self.status_label.setText(f"Retrieval failed: {exc}")
                user_prompt = build_grounded_prompt(snippet, question, passages)
            else:
                user_prompt = build_snippet_prompt(snippet, question)
        else:
            user_prompt = build_snippet_prompt(snippet, question)

        self.response_view.clear()
        self.status_label.setText("Thinking…")
        self.ask_btn.setEnabled(False)
        self.question_input.setEnabled(False)
        self.reset_btn.setEnabled(False)

        self._thread = QThread(self)
        self._worker = LLMWorker(self.llm, SYSTEM_PROMPT, user_prompt)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_llm_done)
        self._worker.failed.connect(self._on_llm_failed)
        self._worker.finished.connect(self._thread.quit)
        self._worker.failed.connect(self._thread.quit)
        self._thread.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.finished.connect(self._on_thread_finished)
        self._thread.start()

    def _on_llm_done(self, text: str) -> None:
        self.response_view.setPlainText(text)
        self.status_label.setText("Done.")

    def _on_llm_failed(self, err: str) -> None:
        self.response_view.setPlainText(f"Error: {err}")
        self.status_label.setText("Failed.")

    def _on_thread_finished(self) -> None:
        self._thread = None
        self._worker = None
        self.ask_btn.setEnabled(True)
        self.question_input.setEnabled(True)
        self.reset_btn.setEnabled(True)

    def handle_clipboard_text(self, text: str) -> None:
        text = text.strip()
        if len(text) < MIN_SNIPPET_LEN:
            return
        if text == self._current_snippet:
            return
        self.set_snippet(text)
        if not self.isVisible():
            self.show()
            self.raise_()
        else:
            self.raise_()

    def show_and_raise(self) -> None:
        if not self.isVisible():
            self.show()
        self.raise_()

    def prepare_to_quit(self) -> None:
        self._app_quitting = True
        self._save_geometry()
        if self._thread is not None and self._thread.isRunning():
            if not self._thread.wait(5000):
                self._thread.terminate()
                self._thread.wait(1000)

    def showEvent(self, event: QEvent) -> None:  # noqa: N802
        super().showEvent(event)
        self.visibility_changed.emit(True)

    def hideEvent(self, event: QEvent) -> None:  # noqa: N802
        super().hideEvent(event)
        self.visibility_changed.emit(False)

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        if not self._app_quitting:
            self._save_geometry()
            event.ignore()
            self.hide()
            return
        self._save_geometry()
        if self._thread is not None and self._thread.isRunning():
            if not self._thread.wait(5000):
                self._thread.terminate()
                self._thread.wait(1000)
        event.accept()


def main() -> int:
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setApplicationName("Reading Assistant")
    app.setOrganizationName("ReadingAssistant")

    settings = QSettings("ReadingAssistant", "FloatingPopup")
    initial_monitoring = bool(settings.value("monitoring", True, type=bool))

    try:
        llm = LLM()
    except Exception as exc:
        QMessageBox.critical(
            None,
            "Reading Assistant",
            "Could not initialize the LLM client.\n\n"
            f"{exc}\n\n"
            "Set OPENCODE_API_KEY in your environment or .env, "
            "or ensure ~/.local/share/opencode/auth.json exists.",
        )
        return 1

    popup = PopupWindow(llm)
    popup._refresh_books()
    if settings.value("geometry") is None:
        screen = app.primaryScreen().availableGeometry()
        popup.resize(460, 520)
        popup.move(screen.right() - popup.width() - 20, screen.top() + 60)

    monitor = ClipboardMonitor(app)

    tray = QSystemTrayIcon(app)
    menu = QMenu()
    show_act = QAction("Show Window", menu)
    hide_act = QAction("Hide Window", menu)
    monitor_act = QAction("Monitor Clipboard", menu)
    monitor_act.setCheckable(True)
    quit_act = QAction("Quit", menu)
    menu.addAction(show_act)
    menu.addAction(hide_act)
    menu.addSeparator()
    menu.addAction(monitor_act)
    menu.addSeparator()
    menu.addAction(quit_act)
    tray.setContextMenu(menu)

    def update_window_actions() -> None:
        if monitor.is_active:
            show_act.setEnabled(not popup.isVisible())
            hide_act.setEnabled(popup.isVisible())
        else:
            show_act.setEnabled(False)
            hide_act.setEnabled(False)

    def set_monitoring(active: bool) -> None:
        if active:
            monitor.start()
            popup.show_and_raise()
        else:
            monitor.stop()
            if popup.isVisible():
                popup.hide()
        tray.setIcon(_build_tray_icon(active))
        tray.setToolTip(
            "Reading Assistant — monitoring" if active else "Reading Assistant — paused"
        )
        monitor_act.blockSignals(True)
        monitor_act.setChecked(active)
        monitor_act.blockSignals(False)
        settings.setValue("monitoring", active)
        update_window_actions()

    set_monitoring(initial_monitoring)
    tray.show()

    show_act.triggered.connect(popup.show_and_raise)
    hide_act.triggered.connect(popup.hide)
    monitor_act.toggled.connect(set_monitoring)
    quit_act.triggered.connect(app.quit)
    app.aboutToQuit.connect(popup.prepare_to_quit)

    def on_tray_activated(reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason != QSystemTrayIcon.Trigger:
            return
        if monitor.is_active:
            popup.show_and_raise()
        else:
            menu.popup(tray.geometry().bottomLeft())

    tray.activated.connect(on_tray_activated)
    monitor.newText.connect(popup.handle_clipboard_text)
    popup.visibility_changed.connect(update_window_actions)

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())

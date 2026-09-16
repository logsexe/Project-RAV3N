from __future__ import annotations

import os
import sys
from concurrent.futures import Future

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .knowledge import KnowledgeEntry, KnowledgeIndex
from .offline_ai import OfflineAI
from .qt_app import _display_summary
from .qt_field_app import FieldOSWindow as V29FieldOSWindow, V29_STYLE


V3_APPS = (
    ("RADIO", "◉", "RX / SPECTRUM"),
    ("NAVIGATION", "⌖", "MAP / GPS"),
    ("MESH", "⌁", "NODES / MESSAGES"),
    ("NETWORK", "◎", "LOCAL / DEVICES"),
    ("OPS", "◇", "MISSION / EVIDENCE"),
    ("LIBRARY", "▤", "OFFLINE KNOWLEDGE"),
    ("ASSIST", "✦", "LOCAL AI / RAG"),
    ("FILES", "▱", "LOCAL STORAGE"),
    ("TERMINAL", ">_", "OPERATOR SHELL"),
    ("RVN-01", "◆", "SYSTEM / HARDWARE"),
)

V3_STYLE = V29_STYLE + """
QComboBox, QListWidget {
    background:#020503;
    color:#d7f7df;
    border:1px solid #284b31;
    padding:6px;
}
QListWidget::item { padding:5px; }
QListWidget::item:selected { background:#12341c; color:#ffffff; }
QLabel#assistStatus { color:#8cf5a7; font-size:11px; font-weight:700; }
"""


class FieldOSWindow(V29FieldOSWindow):
    """FIELD//OS V3 — offline knowledge + local ASSIST UI."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("RAVEN // FIELD//OS V3")

        self.knowledge: KnowledgeIndex | None = None
        self.knowledge_entries: list[KnowledgeEntry] = []
        self.knowledge_future: Future = self.executor.submit(KnowledgeIndex.load_default)
        self.assist = OfflineAI()
        self.assist_status_future: Future | None = self.executor.submit(self.assist.status)
        self.assist_future: Future | None = None
        self.assist_sources: list[KnowledgeEntry] = []

        # Replace the legacy LIBRARY status-only page with a usable browser.
        self._replace_page("LIBRARY", self._library_page())
        self.pages["ASSIST"] = self._assist_page()
        self.stack.addWidget(self.pages["ASSIST"])

        self.v3_timer = QTimer(self)
        self.v3_timer.timeout.connect(self._collect_v3_work)
        self.v3_timer.start(150)

    def _field_launcher(self) -> QWidget:
        page = QWidget()
        page.setObjectName("fieldLauncher")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(12, 7, 12, 7)
        layout.setSpacing(4)

        header = QLabel("RAVEN // RVN-01")
        header.setObjectName("launcherBrand")
        layout.addWidget(header)
        meta = QLabel("FIELD//OS V3   •   OFFLINE FIELD COMPUTER   •   SELECT APPLICATION")
        meta.setObjectName("launcherMeta")
        layout.addWidget(meta)

        grid = QGridLayout()
        grid.setHorizontalSpacing(6)
        grid.setVerticalSpacing(6)
        self.buttons = []
        for i, (name, glyph, desc) in enumerate(V3_APPS):
            button = QPushButton(f"{glyph}  {name}\n    {desc}")
            button.setObjectName("appCard")
            button.setMinimumHeight(66)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(lambda checked=False, n=name: self.open_app(n))
            grid.addWidget(button, i // 4, i % 4)
            self.buttons.append(button)
        layout.addLayout(grid, 1)

        hint = QLabel("TOUCH / ENTER OPEN   •   ESC APPLICATIONS   •   CTRL+Q EXIT")
        hint.setObjectName("launcherHint")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(hint)
        return page

    def _library_page(self) -> QWidget:
        page, layout = self._shell("LIBRARY", "Offline knowledge // categories // local search")

        search_row = QHBoxLayout()
        self.library_category = QComboBox()
        self.library_category.addItem("ALL")
        self.library_category.currentTextChanged.connect(self._refresh_library_results)
        search_row.addWidget(self.library_category)

        self.library_search = QLineEdit()
        self.library_search.setPlaceholderText("Search local knowledge")
        self.library_search.returnPressed.connect(self._refresh_library_results)
        search_row.addWidget(self.library_search, 1)
        search = QPushButton("SEARCH")
        search.clicked.connect(self._refresh_library_results)
        search_row.addWidget(search)
        layout.addLayout(search_row)

        body = QHBoxLayout()
        self.library_list = QListWidget()
        self.library_list.setMinimumWidth(285)
        self.library_list.currentRowChanged.connect(self._show_library_entry)
        body.addWidget(self.library_list, 2)

        self.library_detail = QTextEdit()
        self.library_detail.setReadOnly(True)
        self.library_detail.setPlainText("INDEXING LOCAL KNOWLEDGE...")
        body.addWidget(self.library_detail, 3)
        layout.addLayout(body, 1)

        self.library_meta = QLabel("INDEX   LOADING")
        self.library_meta.setObjectName("subtitle")
        layout.addWidget(self.library_meta)
        self._back(layout)
        return page

    def _assist_page(self) -> QWidget:
        page, layout = self._shell("ASSIST", "Local AI // source-backed offline answers")
        self.assist_status = QLabel("MODEL       PROBING\nKNOWLEDGE   INDEXING\nNETWORK     LOCAL ONLY")
        self.assist_status.setObjectName("assistStatus")
        layout.addWidget(self.assist_status)

        self.assist_output = QTextEdit()
        self.assist_output.setReadOnly(True)
        self.assist_output.setPlainText(
            "FIELD//OS ASSIST // READY\n\n"
            "Questions are answered by the configured local model. Relevant local knowledge is supplied as context when available.\n"
            "Model output is never executed automatically."
        )
        layout.addWidget(self.assist_output, 1)

        row = QHBoxLayout()
        self.assist_input = QLineEdit()
        self.assist_input.setPlaceholderText("Ask RVN-01 offline...")
        self.assist_input.returnPressed.connect(self._ask_assist)
        row.addWidget(self.assist_input, 1)
        ask = QPushButton("ASK")
        ask.setObjectName("primary")
        ask.clicked.connect(self._ask_assist)
        row.addWidget(ask)
        clear = QPushButton("CLEAR")
        clear.clicked.connect(self.assist_output.clear)
        row.addWidget(clear)
        layout.addLayout(row)
        self._back(layout)
        return page

    def _refresh_library_results(self) -> None:
        if self.knowledge is None:
            return
        query = self.library_search.text().strip()
        category = self.library_category.currentText().strip()
        category_filter = None if category == "ALL" else category
        self.knowledge_entries = self.knowledge.search(query, limit=80, category=category_filter)
        self.library_list.clear()
        for entry in self.knowledge_entries:
            self.library_list.addItem(f"[{entry.category.upper()}] {entry.title}")
        self.library_meta.setText(
            f"INDEX   {len(self.knowledge.all)} DOCS   •   CATEGORIES {len(self.knowledge.categories)}   •   RESULTS {len(self.knowledge_entries)}"
        )
        if self.knowledge_entries:
            self.library_list.setCurrentRow(0)
        else:
            self.library_detail.setPlainText("NO MATCHING LOCAL KNOWLEDGE")

    def _show_library_entry(self, row: int) -> None:
        if row < 0 or row >= len(self.knowledge_entries):
            return
        entry = self.knowledge_entries[row]
        path = f"\nPATH       {entry.path}" if entry.path else ""
        command = f"\nCOMMAND    {entry.command}" if entry.command else ""
        self.library_detail.setPlainText(
            f"{entry.title}\n\nCATEGORY   {entry.category.upper()}\nSOURCE     {entry.source}{path}{command}\n\n"
            f"{entry.summary}\n\n{entry.body}"
        )

    def _ask_assist(self) -> None:
        question = self.assist_input.text().strip()
        if not question:
            return
        if self.assist_future is not None and not self.assist_future.done():
            self.footer.setText("RVN-01 // ASSIST // BUSY")
            return

        self.assist_input.clear()
        self.assist_output.append(f"\n\nOPERATOR > {question}\n")
        context = ""
        self.assist_sources = []
        if self.knowledge is not None:
            self.assist_sources = self.knowledge.search(question, limit=5)
            context = self.knowledge.context(question, limit=5, max_chars=10000)
        if self.assist_sources:
            names = "\n".join(f"  • [{entry.category.upper()}] {entry.title}" for entry in self.assist_sources)
            self.assist_output.append("LOCAL SOURCES\n" + names + "\n")
        else:
            self.assist_output.append("LOCAL SOURCES\n  • none matched\n")
        self.assist_output.append("ASSIST > thinking locally...")
        self.footer.setText("RVN-01 // ASSIST // LOCAL INFERENCE")
        self.assist_future = self.executor.submit(self.assist.ask, question, context)

    def _collect_v3_work(self) -> None:
        if self.knowledge is None and self.knowledge_future.done():
            try:
                self.knowledge = self.knowledge_future.result()
            except Exception as exc:
                self.library_detail.setPlainText(f"KNOWLEDGE INDEX ERROR // {type(exc).__name__}")
            else:
                self.library_category.blockSignals(True)
                self.library_category.clear()
                self.library_category.addItem("ALL")
                for category in self.knowledge.categories:
                    self.library_category.addItem(category.upper())
                self.library_category.blockSignals(False)
                self._refresh_library_results()
                self._update_assist_status()

        if self.assist_status_future is not None and self.assist_status_future.done():
            try:
                status = self.assist_status_future.result()
            except Exception as exc:
                self.assist_status.setText(f"MODEL       ERROR // {type(exc).__name__}\nKNOWLEDGE   LOCAL\nNETWORK     LOCAL ONLY")
            else:
                self.assist_status.setText(
                    f"MODEL       {status.model} // {status.detail}\n"
                    f"KNOWLEDGE   {len(self.knowledge.all) if self.knowledge else 'INDEXING'}\n"
                    "NETWORK     LOCAL ONLY"
                )
            self.assist_status_future = None

        if self.assist_future is not None and self.assist_future.done():
            try:
                answer = self.assist_future.result()
            except Exception as exc:
                answer = f"ASSIST unavailable: {type(exc).__name__}"
            # Replace the temporary thinking line with the completed answer.
            text = self.assist_output.toPlainText()
            marker = "ASSIST > thinking locally..."
            if text.endswith(marker):
                text = text[: -len(marker)] + "ASSIST > " + answer
                self.assist_output.setPlainText(text)
            else:
                self.assist_output.append("ASSIST > " + answer)
            self.assist_output.moveCursor(self.assist_output.textCursor().MoveOperation.End)
            self.footer.setText("RVN-01 // ASSIST // COMPLETE // LOCAL MODEL")
            self.assist_future = None

    def _update_assist_status(self) -> None:
        if self.assist_status_future is None:
            self.assist_status_future = self.executor.submit(self.assist.status)

    def open_app(self, name: str) -> None:
        if name == "LIBRARY":
            self.stack.setCurrentWidget(self.pages["LIBRARY"])
            self.footer.setText("RVN-01 // LIBRARY // OFFLINE KNOWLEDGE")
            self._refresh_library_results()
            self.library_search.setFocus()
            return
        if name == "ASSIST":
            self.stack.setCurrentWidget(self.pages["ASSIST"])
            self.footer.setText("RVN-01 // ASSIST // LOCAL ONLY")
            self._update_assist_status()
            self.assist_input.setFocus()
            return
        super().open_app(name)

    def _tick(self) -> None:
        from datetime import datetime
        self.top.setText(
            f"RAVEN // RVN-01     FIELD//OS V3     GPS • MESH • NET • SDR • AI •     {datetime.now().strftime('%H:%M:%S')}"
        )


def main() -> int:
    print("FIELD//OS V3 // library + local ASSIST", flush=True)
    print(_display_summary(), flush=True)
    if sys.platform.startswith("linux") and not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
        print("FIELD//OS: no graphical display is available in this shell.", file=sys.stderr, flush=True)
        return 2
    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyleSheet(V3_STYLE)
    window = FieldOSWindow()
    window.show() if "--windowed" in sys.argv else window.showFullScreen()
    print("FIELD//OS: V3 graphical window created", flush=True)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

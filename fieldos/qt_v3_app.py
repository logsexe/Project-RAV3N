from __future__ import annotations

import os
import sys
from concurrent.futures import Future
from datetime import datetime

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QApplication,
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
from .qt_app import _display_summary
from .qt_field_app import FieldOSWindow as V29FieldOSWindow, V29_STYLE


V3_APPS = (
    ("RADIO", "◉", "RX / SPECTRUM"),
    ("NAVIGATION", "⌖", "MAP / GPS"),
    ("MESH", "⌁", "NODES / MESSAGES"),
    ("NETWORK", "◎", "LOCAL / DEVICES"),
    ("OPS", "◇", "MISSION / EVIDENCE"),
    ("LIBRARY", "▤", "OFFLINE KNOWLEDGE"),
    ("FILES", "▱", "LOCAL STORAGE"),
    ("TERMINAL", ">_", "OPERATOR SHELL"),
    ("RVN-01", "◆", "SYSTEM / HARDWARE"),
)

# Stable operator-facing sections. A section may group several lower-level
# knowledge categories so bundled FIELD//OS notes and user collections appear
# together without forcing the filesystem taxonomy onto the UI.
KNOWLEDGE_SECTIONS = (
    ("RAVEN", {"raven", "knowledge"}),
    ("RADIO", {"radio", "rf"}),
    ("NAVIGATION", {"navigation", "maps", "field"}),
    ("COMMS", {"comms", "communications", "mesh"}),
    ("CYBER", {"cyber", "security", "network", "blue", "forensics"}),
    ("COMPUTING", {"computing", "linux", "utilities"}),
    ("EMERGENCY", {"emergency", "preparedness"}),
    ("MEDICAL", {"medical", "first-aid", "first_aid"}),
    ("REPAIR", {"repair", "maintenance", "hardware"}),
    ("SURVIVAL", {"survival"}),
    ("TRAVEL", {"travel"}),
    ("GENERAL", {"general", "reference"}),
)

V3_STYLE = V29_STYLE + """
QListWidget {
    background:#020503;
    color:#d7f7df;
    border:1px solid #284b31;
    padding:4px;
}
QListWidget::item { padding:5px; }
QListWidget::item:selected { background:#12341c; color:#ffffff; }
QPushButton#knowledgeSection {
    min-height:34px;
    padding:5px 7px;
    font-size:11px;
    text-align:center;
}
QPushButton#knowledgeSection:checked {
    background:#12341c;
    border:2px solid #63ff88;
    color:#ffffff;
}
"""


class FieldOSWindow(V29FieldOSWindow):
    """FIELD//OS V3 — nine-tile launcher with an offline knowledge library."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("RAVEN // FIELD//OS V3")

        self.knowledge: KnowledgeIndex | None = None
        self.knowledge_entries: list[KnowledgeEntry] = []
        self.knowledge_future: Future = self.executor.submit(KnowledgeIndex.load_default)
        self.active_knowledge_section: str | None = None
        self.section_buttons: dict[str, QPushButton] = {}

        self._replace_page("LIBRARY", self._library_page())

        # Replace the inherited V2.9 launcher with the locked nine-tile V3 grid.
        old_launcher = self.launcher
        index = self.stack.indexOf(old_launcher)
        self.stack.removeWidget(old_launcher)
        old_launcher.deleteLater()
        self.launcher = self._field_launcher()
        self.stack.insertWidget(index, self.launcher)

        self.v3_timer = QTimer(self)
        self.v3_timer.timeout.connect(self._collect_v3_work)
        self.v3_timer.start(150)

    def _replace_page(self, name: str, page: QWidget) -> None:
        old = self.pages.get(name)
        if old is not None:
            index = self.stack.indexOf(old)
            self.stack.removeWidget(old)
            old.deleteLater()
            self.pages[name] = page
            self.stack.insertWidget(index, page)
        else:
            self.pages[name] = page
            self.stack.addWidget(page)

    def _field_launcher(self) -> QWidget:
        page = QWidget()
        page.setObjectName("fieldLauncher")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(14, 8, 14, 8)
        layout.setSpacing(5)

        header = QLabel("RAVEN // RVN-01")
        header.setObjectName("launcherBrand")
        layout.addWidget(header)
        meta = QLabel("FIELD//OS V3   •   OFFLINE FIELD COMPUTER   •   SELECT APPLICATION")
        meta.setObjectName("launcherMeta")
        layout.addWidget(meta)

        grid = QGridLayout()
        grid.setHorizontalSpacing(7)
        grid.setVerticalSpacing(7)
        self.buttons = []
        for i, (name, glyph, desc) in enumerate(V3_APPS):
            button = QPushButton(f"{glyph}   {name}\n      {desc}")
            button.setObjectName("appCard")
            button.setMinimumHeight(88)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
            button.clicked.connect(lambda checked=False, n=name: self.open_app(n))
            grid.addWidget(button, i // 3, i % 3)
            self.buttons.append(button)
        layout.addLayout(grid, 1)

        hint = QLabel("TOUCH / ENTER OPEN   •   ESC APPLICATIONS   •   CTRL+Q EXIT")
        hint.setObjectName("launcherHint")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(hint)
        return page

    def _library_page(self) -> QWidget:
        page, layout = self._shell("LIBRARY", "Offline knowledge // field references // local collections")

        section_grid = QGridLayout()
        section_grid.setSpacing(4)
        for i, (name, _) in enumerate(KNOWLEDGE_SECTIONS):
            button = QPushButton(name)
            button.setObjectName("knowledgeSection")
            button.setCheckable(True)
            button.clicked.connect(lambda checked=False, n=name: self._select_knowledge_section(n))
            section_grid.addWidget(button, i // 4, i % 4)
            self.section_buttons[name] = button
        layout.addLayout(section_grid)

        search_row = QHBoxLayout()
        self.library_search = QLineEdit()
        self.library_search.setPlaceholderText("Search all offline knowledge")
        self.library_search.returnPressed.connect(self._refresh_library_results)
        search_row.addWidget(self.library_search, 1)
        search = QPushButton("SEARCH")
        search.clicked.connect(self._refresh_library_results)
        search_row.addWidget(search)
        clear = QPushButton("ALL")
        clear.clicked.connect(self._clear_knowledge_section)
        search_row.addWidget(clear)
        layout.addLayout(search_row)

        body = QHBoxLayout()
        self.library_list = QListWidget()
        self.library_list.setMinimumWidth(300)
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

    def _section_categories(self, name: str | None) -> set[str] | None:
        if name is None:
            return None
        for section, categories in KNOWLEDGE_SECTIONS:
            if section == name:
                return categories
        return set()

    def _select_knowledge_section(self, name: str) -> None:
        self.active_knowledge_section = name
        for section, button in self.section_buttons.items():
            button.setChecked(section == name)
        self._refresh_library_results()

    def _clear_knowledge_section(self) -> None:
        self.active_knowledge_section = None
        for button in self.section_buttons.values():
            button.setChecked(False)
        self._refresh_library_results()

    def _matches_section(self, entry: KnowledgeEntry) -> bool:
        categories = self._section_categories(self.active_knowledge_section)
        return categories is None or entry.category.lower() in categories

    def _refresh_library_results(self) -> None:
        if self.knowledge is None:
            return
        query = self.library_search.text().strip()
        candidates = self.knowledge.search(query, limit=250)
        self.knowledge_entries = [entry for entry in candidates if self._matches_section(entry)][:80]

        self.library_list.clear()
        for entry in self.knowledge_entries:
            self.library_list.addItem(f"[{entry.category.upper()}] {entry.title}")

        section = self.active_knowledge_section or "ALL"
        self.library_meta.setText(
            f"SECTION {section}   •   INDEX {len(self.knowledge.all)} DOCS   •   RESULTS {len(self.knowledge_entries)}"
        )
        self._update_section_counts()
        if self.knowledge_entries:
            self.library_list.setCurrentRow(0)
        else:
            self.library_detail.setPlainText("NO MATCHING LOCAL KNOWLEDGE")

    def _update_section_counts(self) -> None:
        if self.knowledge is None:
            return
        entries = self.knowledge.all
        for name, categories in KNOWLEDGE_SECTIONS:
            count = sum(1 for entry in entries if entry.category.lower() in categories)
            self.section_buttons[name].setText(f"{name}  {count}")

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

    def _collect_v3_work(self) -> None:
        if self.knowledge is not None or not self.knowledge_future.done():
            return
        try:
            self.knowledge = self.knowledge_future.result()
        except Exception as exc:
            self.library_detail.setPlainText(f"KNOWLEDGE INDEX ERROR // {type(exc).__name__}")
            self.library_meta.setText("INDEX   ERROR")
            return
        self._refresh_library_results()

    def open_app(self, name: str) -> None:
        if name == "LIBRARY":
            self.stack.setCurrentWidget(self.pages["LIBRARY"])
            self.footer.setText("RVN-01 // LIBRARY // OFFLINE KNOWLEDGE")
            self._refresh_library_results()
            self.library_search.setFocus()
            return
        super().open_app(name)

    def _tick(self) -> None:
        self.top.setText(
            f"RAVEN // RVN-01     FIELD//OS V3     GPS • MESH • NET • SDR • LIBRARY •     {datetime.now().strftime('%H:%M:%S')}"
        )


def main() -> int:
    print("FIELD//OS V3 // offline knowledge library", flush=True)
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

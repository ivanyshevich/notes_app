# views/main_window.py

import os
import sys
import uuid
from datetime import datetime

# Allow running this module directly from views/
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QListWidget, QListWidgetItem, QTextEdit,
    QPushButton, QLineEdit, QSplitter, QToolButton,
    QScrollArea, QFileDialog, QInputDialog, QSizePolicy
)
from PyQt6.QtGui import (
    QIcon, QTextDocument, QTextCharFormat,
    QTextCursor, QFont
)
from PyQt6.QtCore import Qt, QSize

from models import Note
from repository import NoteRepository


# Resolve icons folder (one level up)
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ICON_DIR = os.path.join(BASE_DIR, "icons")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Нотатки")
        self.repo = NoteRepository()
        self.current_note = None
        self._build_ui()
        self._load_all()

    def _icon(self, key: str) -> QIcon:
        """
        Load the first icon file in icons/ starting with `key + "_24dp"`.
        """
        for fname in os.listdir(ICON_DIR):
            if fname.startswith(f"{key}_24dp"):
                return QIcon(os.path.join(ICON_DIR, fname))
        return QIcon()

    def _build_ui(self):
        outer = QSplitter(Qt.Orientation.Horizontal)
        outer.setHandleWidth(1)

        # ─── NAVIGATION ───
        nav = QWidget()
        nav_lyt = QVBoxLayout(nav)
        nav_lyt.setContentsMargins(8, 8, 8, 8)

        # Title
        lbl_title = QLabel("Нотатки")
        lbl_title.setStyleSheet("font-size:18px; font-weight:bold;")
        nav_lyt.addWidget(lbl_title)

        # Search
        self.search = QLineEdit()
        self.search.setPlaceholderText("Пошук…")
        self.search.textChanged.connect(self._filter_center)
        nav_lyt.addWidget(self.search)

        # New note (rectangle-shaped, lighter)
        btn_new = QPushButton("+ Новий запис")
        btn_new.setObjectName("newNoteButton")
        btn_new.setFixedHeight(28)
        btn_new.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed
        )

        btn_new.setStyleSheet("""
            background-color: #2a2a2a;
            border: none;
            border-radius: 4px;
            color: #E0E0E0;
            font-size: 14px;
        """)
        btn_new.clicked.connect(self._create_note)
        nav_lyt.addWidget(btn_new)


        # Recent
        nav_lyt.addSpacing(12)
        nav_lyt.addWidget(QLabel("Нещодавні"))
        self.recent_list = QListWidget()
        self.recent_list.currentItemChanged.connect(self._on_select)
        # Increase icon and font size
        self.recent_list.setIconSize(QSize(24, 24))
        self.recent_list.setStyleSheet("font-size:14px;")
        nav_lyt.addWidget(self.recent_list, stretch=1)

        # Folders header + add-folder
        nav_lyt.addSpacing(12)
        hdr = QHBoxLayout()
        hdr.addWidget(QLabel("Папки"))
        btn_add_f = QToolButton()
        btn_add_f.setIcon(self._icon("create_new_folder"))
        btn_add_f.setAutoRaise(True)
        hdr.addWidget(btn_add_f)
        hdr.addStretch()
        nav_lyt.addLayout(hdr)

        # Folder list
        self.folder_list = QListWidget()
        for name in ["Усі", "Особисті", "Робота", "Подорожі", "Фінанси"]:
            item = QListWidgetItem(self._icon("folder"), name)
            self.folder_list.addItem(item)
        self.folder_list.currentTextChanged.connect(self._load_center)
        # Increase icon and font size
        self.folder_list.setIconSize(QSize(24, 24))
        self.folder_list.setStyleSheet("font-size:14px;")
        nav_lyt.addWidget(self.folder_list, stretch=1)

        # More
        nav_lyt.addSpacing(12)
        nav_lyt.addWidget(QLabel("More"))
        more_list = QListWidget()
        for name, key in [("Збережене", "bookmark"),
                          ("Корзина", "delete"),
                          ("Архів", "archive")]:
            itm = QListWidgetItem(self._icon(key), name)
            more_list.addItem(itm)
        # Increase icon and font size
        more_list.setIconSize(QSize(24, 24))
        more_list.setStyleSheet("font-size:14px;")
        nav_lyt.addWidget(more_list)

        outer.addWidget(nav)

        # ─── CONTENT SPLIT ───
        content = QSplitter(Qt.Orientation.Horizontal)
        content.setHandleWidth(1)

        # Center column: notes list
        center = QWidget()
        clyt = QVBoxLayout(center)
        clyt.setContentsMargins(8, 8, 8, 8)
        self.center_header = QLabel()
        self.center_header.setStyleSheet("font-size:16px; font-weight:600;")
        clyt.addWidget(self.center_header)
        self.note_list = QListWidget()
        self.note_list.currentItemChanged.connect(self._on_select)
        clyt.addWidget(self.note_list)
        content.addWidget(center)

        # Right column: detail pane + editor
        detail = QWidget()
        detail.setStyleSheet("background-color: #121212;")
        dlyt = QVBoxLayout(detail)
        dlyt.setContentsMargins(8, 8, 8, 8)

        # Metadata row
        meta = QHBoxLayout()
        date_icon = QLabel()
        date_icon.setPixmap(self._icon("calendar_today").pixmap(16, 16))
        meta.addWidget(date_icon)
        self.lbl_date = QLabel()
        meta.addWidget(self.lbl_date)

        folder_icon = QLabel()
        folder_icon.setPixmap(self._icon("folder").pixmap(16, 16))
        meta.addSpacing(12)
        meta.addWidget(folder_icon)
        self.lbl_folder = QLabel()
        meta.addWidget(self.lbl_folder)

        meta.addStretch()
        more_btn = QToolButton()
        more_btn.setText("⋯")
        more_btn.setAutoRaise(True)
        meta.addWidget(more_btn)
        dlyt.addLayout(meta)

        # ── Scrollable formatting bar ──
        scroll = QScrollArea()
        scroll.setStyleSheet("background-color: #121212; border: none;")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidgetResizable(True)
        scroll.setFixedHeight(48)

        bar = QWidget()
        bar.setStyleSheet("background: transparent;")
        bl = QHBoxLayout(bar)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.setSpacing(8)

        def add_btn(icon_key=None, text=None, tip="", slot=None):
            btn = QToolButton()
            if icon_key:
                btn.setIcon(self._icon(icon_key))
            else:
                btn.setText(text)
            btn.setToolTip(tip)
            btn.setAutoRaise(True)
            btn.setIconSize(QSize(20, 20))
            if slot:
                btn.clicked.connect(slot)
            bl.addWidget(btn)
            return btn

        # Paragraph style
        add_btn(icon_key="format_paragraph", tip="Стиль абзацу",
                slot=self._change_paragraph_style)
        # Font size
        add_btn(icon_key="arrow_drop_down", text="16", tip="Розмір шрифту",
                slot=self._change_font_size)
        # Text formatting toggles
        add_btn(icon_key="format_bold", tip="Жирний", slot=self._toggle_bold)
        add_btn(icon_key="format_italic", tip="Курсив", slot=self._toggle_italic)
        add_btn(icon_key="format_underlined", tip="Підкресл.", slot=self._toggle_underline)
        # Bullet list: manual HTML insertion
        add_btn(icon_key="format_list_bulleted", tip="Список", slot=self._insert_list)
        # Insert elements
        add_btn(icon_key="imagesmode", tip="Зображення", slot=self._insert_image)
        add_btn(icon_key="link", tip="Посилання", slot=self._insert_link)
        add_btn(icon_key="table_chart", tip="Таблиця", slot=self._insert_table)

        scroll.setWidget(bar)
        dlyt.addWidget(scroll)

        # Editor
        self.editor = QTextEdit()
        dlyt.addWidget(self.editor, stretch=1)

        content.addWidget(detail)
        outer.addWidget(content)

        outer.setSizes([180, 300, 600])
        self.setCentralWidget(outer)

    # ... rest of methods (_load_all, _load_center, etc.) unchanged ...
    def _load_all(self):
        """Populate the Recent list and load the default folder."""
        self.recent_list.clear()
        recents = sorted(self.repo.notes, key=lambda n: n.date, reverse=True)[:5]
        for note in recents:
            item = QListWidgetItem(self._icon("description"), note.title)
            item.setData(Qt.ItemDataRole.UserRole, note)
            self.recent_list.addItem(item)

        # Select “Усі” by default
        self.folder_list.setCurrentRow(0)
        self._load_center()

    def _load_center(self, folder=None):
        """Display notes in the center column for the given folder."""
        folder = folder or self.folder_list.currentItem().text()
        self.center_header.setText(folder)
        self.note_list.clear()

        for note in self.repo.notes:
            if folder == "Усі" or note.folder == folder:
                doc = QTextDocument()
                doc.setHtml(note.content)
                snippet = doc.toPlainText().replace("\n", " ")[:40] + "…"
                date_str = note.date.strftime("%d.%m.%Y")
                text = f"{date_str}  {note.title}\n{snippet}"
                item = QListWidgetItem(self._icon("description"), text)
                item.setData(Qt.ItemDataRole.UserRole, note)
                self.note_list.addItem(item)

    def _filter_center(self, text):
        """Filter the center note list by title substring."""
        text = text.lower()
        for i in range(self.note_list.count()):
            item = self.note_list.item(i)
            note: Note = item.data(Qt.ItemDataRole.UserRole)
            item.setHidden(text not in note.title.lower())

    def _on_select(self, current, previous):
        """Load note details into the editor when a list item is selected."""
        if current:
            note: Note = current.data(Qt.ItemDataRole.UserRole)
            self.current_note = note
            self.lbl_date.setText(note.date.strftime("%d %b %Y"))
            self.lbl_folder.setText(note.folder)
            self.editor.blockSignals(True)
            self.editor.setHtml(note.content)
            self.editor.blockSignals(False)

    def _create_note(self):
        """Add a new blank note to the repository and refresh UI."""
        note = Note(
            id=str(uuid.uuid4()),
            title="Новий запис",
            content="",
            date=datetime.now(),
            folder="Особисті"
        )
        self.repo.add(note)
        self._load_all()
        self.recent_list.setCurrentRow(0)

    def _toggle_bold(self):
        fmt = QTextCharFormat()
        weight = QFont.Weight.Normal if self.editor.fontWeight() == QFont.Weight.Bold else QFont.Weight.Bold
        fmt.setFontWeight(weight)
        self._merge_format_on_selection(fmt)

    def _toggle_italic(self):
        fmt = QTextCharFormat()
        fmt.setFontItalic(not self.editor.fontItalic())
        self._merge_format_on_selection(fmt)

    def _toggle_underline(self):
        fmt = QTextCharFormat()
        fmt.setFontUnderline(not self.editor.fontUnderline())
        self._merge_format_on_selection(fmt)

    def _insert_list(self):
        """Insert a simple unordered list around the selection."""
        cursor = self.editor.textCursor()
        selected = cursor.selectedText()
        html = f"<ul><li>{selected}</li></ul>" if selected else "<ul><li></li></ul>"
        cursor.insertHtml(html)

    def _merge_format_on_selection(self, fmt: QTextCharFormat):
        """Apply a character format to the current selection or word under the cursor."""
        cursor = self.editor.textCursor()
        if not cursor.hasSelection():
            cursor.select(QTextCursor.SelectionType.WordUnderCursor)
        cursor.mergeCharFormat(fmt)
        self.editor.mergeCurrentCharFormat(fmt)

    def _change_font_size(self):
        sizes = ["10", "12", "14", "16", "18", "20", "24", "28"]
        size, ok = QInputDialog.getItem(self, "Розмір шрифту", "Виберіть розмір:", sizes, 3, False)
        if ok:
            cursor = self.editor.textCursor()
            cf = QTextCharFormat()
            cf.setFontPointSize(float(size))
            cursor.mergeCharFormat(cf)

    def _change_paragraph_style(self):
        styles = ["Paragraph", "Heading 1", "Heading 2", "Heading 3"]
        choice, ok = QInputDialog.getItem(self, "Стиль абзацу", "Виберіть стиль:", styles, 0, False)
        if ok:
            cursor = self.editor.textCursor()
            if choice == "Paragraph":
                cf = QTextCharFormat()
                cf.setFontWeight(QFont.Weight.Normal)
                cf.setFontPointSize(self.editor.font().pointSize())
                cursor.mergeCharFormat(cf)
            else:
                mapping = {"Heading 1": 24, "Heading 2": 18, "Heading 3": 14}
                size = mapping.get(choice, 16)
                self._apply_heading(size)

    def _insert_image(self):
        path, _ = QFileDialog.getOpenFileName(self, "Вставити зображення", "", "Images (*.png *.jpg *.bmp *.svg)")
        if path:
            self.editor.textCursor().insertImage(path)

    def _insert_link(self):
        cursor = self.editor.textCursor()
        selected = cursor.selectedText() or "link"
        url, ok = QInputDialog.getText(self, "Вставити посилання", "URL:")
        if ok and url:
            cursor.insertHtml(f'<a href="{url}">{selected}</a>')

    def _insert_table(self):
        html = (
            '<table border="1" cellspacing="0" cellpadding="4">'
            '<tr><td></td><td></td></tr>'
            '<tr><td></td><td></td></tr>'
            '</table><br>'
        )
        self.editor.textCursor().insertHtml(html)

    def _apply_heading(self, size: int):
        cursor = self.editor.textCursor()
        selected = cursor.selectedText()
        cursor.insertHtml(f'<h1 style="font-size:{size}px;">{selected}</h1>')
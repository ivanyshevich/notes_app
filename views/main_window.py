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
        """Load the first icon file in icons/ starting with `key + "_24dp"`. """
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

        lbl_title = QLabel("Нотатки")
        lbl_title.setStyleSheet("font-size:18px; font-weight:bold; color:#E0E0E0;")
        nav_lyt.addWidget(lbl_title)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Пошук…")
        self.search.textChanged.connect(self._filter_center)
        nav_lyt.addWidget(self.search)

        btn_new = QPushButton("+ Новий запис")
        btn_new.setObjectName("newNoteButton")
        btn_new.setFixedHeight(28)
        btn_new.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        btn_new.setStyleSheet("""
            background-color: #2a2a2a;
            border: none; border-radius: 4px;
            color: #E0E0E0; font-size: 14px;
        """)
        btn_new.clicked.connect(self._create_note)
        nav_lyt.addWidget(btn_new)

        nav_lyt.addSpacing(12)
        nav_lyt.addWidget(QLabel("Нещодавні"))
        self.recent_list = QListWidget()
        self.recent_list.currentItemChanged.connect(self._on_select)
        self.recent_list.setIconSize(QSize(24, 24))
        self.recent_list.setStyleSheet("font-size:14px;")
        nav_lyt.addWidget(self.recent_list, stretch=1)

        nav_lyt.addSpacing(12)
        hdr = QHBoxLayout()
        hdr.addWidget(QLabel("Папки"))
        btn_add_f = QToolButton()
        btn_add_f.setIcon(self._icon("create_new_folder"))
        btn_add_f.setAutoRaise(True)
        hdr.addWidget(btn_add_f)
        hdr.addStretch()
        nav_lyt.addLayout(hdr)

        self.folder_list = QListWidget()
        for name in ["Усі", "Особисті", "Робота", "Подорожі", "Фінанси"]:
            item = QListWidgetItem(self._icon("folder"), name)
            self.folder_list.addItem(item)
        self.folder_list.currentTextChanged.connect(self._load_center)
        self.folder_list.setIconSize(QSize(24, 24))
        self.folder_list.setStyleSheet("font-size:14px;")
        nav_lyt.addWidget(self.folder_list, stretch=1)

        nav_lyt.addSpacing(12)
        nav_lyt.addWidget(QLabel("More"))
        more_list = QListWidget()
        for name, key in [("Збережене", "bookmark"),
                          ("Корзина", "delete"),
                          ("Архів", "archive")]:
            itm = QListWidgetItem(self._icon(key), name)
            more_list.addItem(itm)
        more_list.setIconSize(QSize(24, 24))
        more_list.setStyleSheet("font-size:14px;")
        nav_lyt.addWidget(more_list)

        outer.addWidget(nav)

        # ─── CONTENT SPLIT ───
        content = QSplitter(Qt.Orientation.Horizontal)
        content.setHandleWidth(1)

        # Center column (note titles)
        center = QWidget()
        clyt = QVBoxLayout(center)
        clyt.setContentsMargins(8, 8, 8, 8)
        self.center_header = QLabel()
        self.center_header.setStyleSheet("font-size:16px; font-weight:600; color:#E0E0E0;")
        clyt.addWidget(self.center_header)
        self.note_list = QListWidget()
        self.note_list.currentItemChanged.connect(self._on_select)
        clyt.addWidget(self.note_list)
        content.addWidget(center)

        # Right column (note detail)
        detail = QWidget()
        detail.setStyleSheet("background-color: #121212;")
        dlyt = QVBoxLayout(detail)
        dlyt.setContentsMargins(8, 8, 8, 8)

        # ─── Note Title Row ───
        title_row = QHBoxLayout()
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Title")
        self.title_edit.setStyleSheet(
            "font-size:20px; font-weight:bold; color:#E0E0E0;"
            "background:#121212; border:none;"
        )
        self.title_edit.textEdited.connect(self._update_title)
        title_row.addWidget(self.title_edit, stretch=1)

        title_more = QToolButton()
        title_more.setText("⋯")
        title_more.setAutoRaise(True)
        title_row.addWidget(title_more)

        title_delete = QToolButton()
        title_delete.setIcon(self._icon("delete"))
        title_delete.setIconSize(QSize(24, 24))
        title_delete.setFixedSize(32, 32)
        title_delete.setToolTip("Видалити запис")
        title_delete.setAutoRaise(True)
        title_delete.clicked.connect(self._delete_note)
        title_row.addWidget(title_delete)

        dlyt.addLayout(title_row)

        # ─── Date Row ───
        date_row = QHBoxLayout()
        date_icon = QLabel()
        date_icon.setPixmap(self._icon("calendar_today").pixmap(16, 16))
        date_row.addWidget(date_icon)

        lbl_date_static = QLabel("Дата")
        lbl_date_static.setStyleSheet("color: #AAAAAA;")
        date_row.addWidget(lbl_date_static)

        self.lbl_date = QLabel()
        self.lbl_date.setStyleSheet("text-decoration: underline; color:#E0E0E0;")
        date_row.addWidget(self.lbl_date)

        date_row.addStretch()
        dlyt.addLayout(date_row)

        # ─── Folder Row ───
        folder_row = QHBoxLayout()
        folder_icon = QLabel()
        folder_icon.setPixmap(self._icon("folder").pixmap(16, 16))
        folder_row.addWidget(folder_icon)

        lbl_folder_static = QLabel("Папка")
        lbl_folder_static.setStyleSheet("color: #AAAAAA;")
        folder_row.addWidget(lbl_folder_static)

        self.lbl_folder = QLabel()
        self.lbl_folder.setStyleSheet("text-decoration: underline; color:#E0E0E0;")
        folder_row.addWidget(self.lbl_folder)

        folder_row.addStretch()
        dlyt.addLayout(folder_row)

        # ── Scrollable formatting bar ──
        scroll = QScrollArea()
        scroll.setStyleSheet("background-color: #121212; border:none;")
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

        add_btn(icon_key="format_paragraph", text="Paragraph", tip="Стиль абзацу", slot=self._change_paragraph_style)
        add_btn(icon_key="arrow_drop_down",   text="16", tip="Розмір шрифту", slot=self._change_font_size)
        add_btn(icon_key="format_bold",       tip="Жирний", slot=self._toggle_bold)
        add_btn(icon_key="format_italic",     tip="Курсив", slot=self._toggle_italic)
        add_btn(icon_key="format_underlined", tip="Підкресл.", slot=self._toggle_underline)
        add_btn(icon_key="format_list_bulleted", tip="Список", slot=self._insert_list)
        add_btn(icon_key="imagesmode",        tip="Зображення", slot=self._insert_image)
        add_btn(icon_key="link",              tip="Посилання", slot=self._insert_link)
        add_btn(icon_key="table_chart",       tip="Таблиця", slot=self._insert_table)

        scroll.setWidget(bar)
        dlyt.addWidget(scroll)

        # Editor area
        self.editor = QTextEdit()
        dlyt.addWidget(self.editor, stretch=1)

        content.addWidget(detail)
        outer.addWidget(content)
        outer.setSizes([180, 300, 600])
        self.setCentralWidget(outer)

    # ─── Helpers ───

    def _save_current(self):
        if self.current_note:
            self.current_note.content = self.editor.toHtml()
            try:
                self.repo.update(self.current_note)
            except AttributeError:
                self.repo.add(self.current_note)

    # ─── Data Loading & Selection ───

    def _load_all(self):
        self.recent_list.clear()
        recents = sorted(self.repo.notes, key=lambda n: n.date, reverse=True)[:5]
        for note in recents:
            item = QListWidgetItem(self._icon("description"), note.title)
            item.setData(Qt.ItemDataRole.UserRole, note)
            self.recent_list.addItem(item)
        self.folder_list.setCurrentRow(0)
        self._load_center()

    def _load_center(self, folder=None):
        self.note_list.clear()
        fld = folder or self.folder_list.currentItem().text()
        self.center_header.setText(fld)
        for note in self.repo.notes:
            if fld == "Усі" or note.folder == fld:
                doc = QTextDocument(); doc.setHtml(note.content)
                snippet = doc.toPlainText().replace("\n"," ")[:40] + "…"
                date = note.date.strftime("%d.%m.%Y")
                text = f"{date}  {note.title}\n{snippet}"
                itm = QListWidgetItem(self._icon("description"), text)
                itm.setData(Qt.ItemDataRole.UserRole, note)
                self.note_list.addItem(itm)

    def _filter_center(self, txt):
        t = txt.lower()
        for i in range(self.note_list.count()):
            itm = self.note_list.item(i)
            note = itm.data(Qt.ItemDataRole.UserRole)
            itm.setHidden(t not in note.title.lower())

    def _on_select(self, current, previous):
        if previous:
            self._save_current()
        if current:
            note: Note = current.data(Qt.ItemDataRole.UserRole)
            self.current_note = note
            self.title_edit.setText(note.title)
            self.lbl_date.setText(note.date.strftime("%d %b %Y"))
            self.lbl_folder.setText(note.folder)
            self.editor.blockSignals(True)
            self.editor.setHtml(note.content)
            self.editor.blockSignals(False)

    # ─── Actions ───

    def _create_note(self):
        self._save_current()
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

    def _update_title(self, new_title: str):
        if self.current_note:
            self.current_note.title = new_title
            try:
                self.repo.update(self.current_note)
            except AttributeError:
                self.repo.add(self.current_note)
            self._load_all()
            for i in range(self.recent_list.count()):
                itm = self.recent_list.item(i)
                if itm.data(Qt.ItemDataRole.UserRole) == self.current_note:
                    self.recent_list.setCurrentItem(itm)
                    break

    def _delete_note(self):
        if not self.current_note:
            return
        try:
            self.repo.delete(self.current_note.id)
        except AttributeError:
            self.repo.notes.remove(self.current_note)
        self.current_note = None
        self.title_edit.clear()
        self.editor.clear()
        self._load_all()

    # ─── Formatting methods ───

    def _toggle_bold(self):
        fmt = QTextCharFormat()
        weight = QFont.Weight.Normal if self.editor.fontWeight() == QFont.Weight.Bold else QFont.Weight.Bold
        fmt.setFontWeight(weight)
        self._merge_format_on_selection(fmt)

    def _toggle_italic(self):
        fmt = QTextCharFormat(); fmt.setFontItalic(not self.editor.fontItalic())
        self._merge_format_on_selection(fmt)

    def _toggle_underline(self):
        fmt = QTextCharFormat(); fmt.setFontUnderline(not self.editor.fontUnderline())
        self._merge_format_on_selection(fmt)

    def _insert_list(self):
        cur = self.editor.textCursor()
        sel = cur.selectedText()
        html = f"<ul><li>{sel}</li></ul>" if sel else "<ul><li></li></ul>"
        cur.insertHtml(html)

    def _merge_format_on_selection(self, fmt: QTextCharFormat):
        cur = self.editor.textCursor()
        if not cur.hasSelection():
            cur.select(QTextCursor.SelectionType.WordUnderCursor)
        cur.mergeCharFormat(fmt)
        self.editor.mergeCurrentCharFormat(fmt)

    def _change_font_size(self, text="16"):
        try:
            size = float(text)
        except ValueError:
            size = 16.0
        cur = self.editor.textCursor()
        cf = QTextCharFormat(); cf.setFontPointSize(size)
        cur.mergeCharFormat(cf)

    def _change_paragraph_style(self, text="Paragraph"):
        cur = self.editor.textCursor()
        if text == "Paragraph":
            cf = QTextCharFormat()
            cf.setFontWeight(QFont.Weight.Normal)
            cf.setFontPointSize(self.editor.font().pointSize())
            cur.mergeCharFormat(cf)
        else:
            mapping = {"Heading 1": 24, "Heading 2": 18, "Heading 3": 14}
            size = mapping.get(text, 16)
            self._apply_heading(size)

    def _insert_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Вставити зображення", "", "Images (*.png *.jpg *.bmp *.svg)"
        )
        if path:
            self.editor.textCursor().insertImage(path)

    def _insert_link(self):
        cur = self.editor.textCursor()
        sel = cur.selectedText() or "link"
        url, ok = QInputDialog.getText(self, "Вставити посилання", "URL:")
        if ok and url:
            cur.insertHtml(f'<a href="{url}">{sel}</a>')

    def _insert_table(self):
        html = (
            '<table border="1" cellspacing="0" cellpadding="4">'
            '<tr><td></td><td></td></tr>'
            '<tr><td></td><td></td></tr>'
            '</table><br>'
        )
        self.editor.textCursor().insertHtml(html)

    def _apply_heading(self, size: int):
        cur = self.editor.textCursor()
        sel = cur.selectedText()
        cur.insertHtml(f'<h1 style="font-size:{size}px;">{sel}</h1>')
"""Редактор таблиц -- «Создать таблицу»/«Редактировать таблицу» из ПКМ на
чипе плейсхолдера в реквизитах конструктора документов (см.
src/ui/main_window.py, _show_chip_context_menu()/_open_table_editor()).

Портирован из JS-мокапа (docs/design/вводная_часть.html, tableModal +
соседние function table*()), той же моделью, что и редактор формул
(FormulaEditorDialog) -- активная область + позиция курсора внутри неё
(см. TableEditorDialog._set_active_cell()), только область здесь не
произвольная вложенная зона (числитель/знаменатель дроби), а ровно одна
ячейка сетки: активная ячейка всегда одна и однозначно определяется
(_active_r, _active_c), поэтому отдельного "activeZone"-указателя не нужно
-- сама ссылка на список токенов этой ячейки и есть активная зона.

Ячейка -- смешанный контент: свободный текст вперемешку с чипами ДРУГИХ
плейсхолдеров каталога (сама таблица не может ссылаться на своё же поле --
то же правило, что и у формул). В отличие от формулы, набор токенов ровно
два: {"type": "text", "value": ...} | {"type": "placeholder", "id": ...} --
без операторов/дробей/чисел (числа в таблице -- обычный текст).

Настоящая привязка к спискам ({% for %}/{%tr for %} из CLAUDE.md, повтор
строки на элемент списка) -- вне охвата: таблица тут фиксированного
размера, не строка на элемент списка. Сама таблица при этом РЕАЛЬНО
попадает в готовый .docx -- get_form_data() подставляет вместо значения
поля маркер (_table_field_marker() в src/ui/main_window.py), а уже
ПОСЛЕ tpl.render() _splice_table_placeholders() меняет этот маркер на
настоящую .docx-таблицу, построенную из rows/has_header этого диалога
(см. докстринги обеих функций)."""

from typing import Callable, Dict, List, Optional

from PyQt6.QtCore import Qt, QSize
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QWidget, QLabel, QPushButton,
    QToolButton, QMenu, QCheckBox, QLineEdit, QScrollArea, QFrame, QInputDialog,
)

from . import icons
from .flow_layout import FlowLayout

_QSS = """
QDialog { background: #2c2c2e; }
QDialog QLabel { color: #c7c7cc; font-size: 12px; }
QLabel#tableTitle { color: #e5e5e7; font-size: 13px; font-weight: 600; }
QLabel#tableSubtitle { color: #8e8e93; font-size: 11.5px; }
QCheckBox { color: #8e8e93; font-size: 11.5px; }
QScrollArea#tableGridScroll { border: 0.5px solid #38383a; border-radius: 8px; background: #1c1c1e; }
QWidget#tableEditorCell {
    background: #1c1c1e; border: 0.5px solid #38383a; color: #e5e5e7; font-size: 11.5px;
}
QWidget#tableEditorCell[tableCellHeader="true"] { background: #232325; }
QWidget#tableEditorCell[tableCellActive="true"] { border: 1.5px solid #0a84ff; background: rgba(10, 132, 255, 20); }
QLabel[tableToken="placeholder"] {
    background: rgba(100, 210, 255, 40); color: #64d2ff;
    border: 1px solid rgba(100, 210, 255, 100); border-radius: 5px; padding: 2px 7px; font-size: 11px;
}
QLabel[tableToken="text"] { color: #e5e5e7; font-size: 11.5px; }
QFrame#tableCaret { background: #0a84ff; }
QLineEdit#tableTextInput {
    background: #1c1c1e; border: 0.5px solid #48484a; border-radius: 6px;
    padding: 6px 7px; font-size: 12px; color: #e5e5e7;
}
"""

_OP_BTN_QSS = (
    "QPushButton{background:#242426; border:0.5px solid #38383a; color:#c7c7cc; "
    "font-size:12px; padding:5px 10px; border-radius:6px;} "
    "QPushButton:hover{background:#3a3a3c; color:#e5e5e7;}"
)


class _ClickableLabel(QLabel):
    """QLabel одного токена ячейки -- клик определяет, в какую половину
    виджета попал курсор (левая -- курсор встаёт ПЕРЕД токеном, правая --
    ПОСЛЕ), см. TableEditorDialog._render_cell_token(). Копия
    _ClickableLabel из formula_editor_dialog.py -- та же роль, тот же
    минимальный код, отдельная копия вместо общего модуля ради того, чтобы
    два самостоятельных редактора-диалога не делили между собой лишнюю
    связь ради 7 строк."""

    def __init__(self, text: str, on_click: Callable[[bool], None]):
        super().__init__(text)
        self._on_click = on_click
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, event):
        before = event.position().x() < self.width() / 2
        self._on_click(before)


class _CaretFrame(QFrame):
    """Мигающая (визуально -- статичная) вертикальная черта курсора
    вставки -- копия _CaretFrame из formula_editor_dialog.py, см. её
    докстринг насчёт того, почему sizeHint() обязателен для FlowLayout."""

    def sizeHint(self) -> QSize:
        return QSize(2, 20)


def _make_flow_widget(object_name: str, margin: int, spacing: int) -> QWidget:
    """QWidget с FlowLayout, готовый переноситься на несколько строк --
    копия _make_flow_widget() из formula_editor_dialog.py (см. её
    докстринг насчёт setHeightForWidth(True))."""
    container = QWidget()
    container.setObjectName(object_name)
    FlowLayout(container, margin=margin, spacing=spacing)
    policy = container.sizePolicy()
    policy.setHeightForWidth(True)
    container.setSizePolicy(policy)
    return container


def _clone_cell(tokens: List[Dict]) -> List[Dict]:
    return [dict(token) for token in tokens]


class TableEditorDialog(QDialog):
    """См. докстринг модуля. Результат читается вызывающей стороной ПОСЛЕ
    exec(), и только если он вернул QDialog.DialogCode.Accepted:
    `removed=True` -- таблицу нужно убрать у поля, иначе `rows`/
    `has_header` -- новое (или обновлённое) содержимое таблицы."""

    def __init__(
        self,
        field_id: str,
        field_label: str,
        all_fields: Dict[str, str],
        all_formulas: Dict[str, Dict],
        all_tables: Dict[str, Dict],
        existing_table: Optional[Dict],
        create_field: Callable[[str], str],
        parent=None,
    ):
        super().__init__(parent)
        self._field_id = field_id
        # Само поле, которое сейчас превращается в таблицу, исключено из
        # списка вставки -- ссылка на само себя бессмысленна (тот же приём,
        # что и самоисключение поля в редакторе формул).
        self._all_fields: Dict[str, str] = {fid: label for fid, label in all_fields.items() if fid != field_id}
        self._all_formulas = dict(all_formulas)
        self._all_tables = dict(all_tables)
        # Колбэк заводит НОВОЕ поле в общем каталоге (field_catalog) и
        # возвращает его id -- физическую запись каталога делает вызывающая
        # сторона (MainWindow), диалог самих JSON-файлов не трогает, тем же
        # принципом, что и resolve_placeholder у FormulaEditorDialog.
        self._create_field = create_field

        if existing_table:
            self._rows: List[List[List[Dict]]] = [
                [_clone_cell(cell) for cell in row] for row in existing_table["rows"]
            ]
            self._has_header = bool(existing_table.get("has_header"))
        else:
            self._rows = [[[], []], [[], []]]  # пустая сетка 2×2 по умолчанию
            self._has_header = False

        self._active_r = 0
        self._active_c = 0
        self._active_zone: List[Dict] = self._rows[0][0]
        self._cursor_index = 0

        self.removed = False
        self.rows: List[List[List[Dict]]] = []
        self.has_header = self._has_header

        self.setWindowTitle("Редактор таблицы")
        self.setStyleSheet(_QSS)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._build_ui(field_label, existing_table is not None)
        self._render_grid()

    # -- Построение диалога -------------------------------------------------
    def _build_ui(self, field_label: str, has_existing: bool):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(4)
        self.setMinimumWidth(480)

        title = QLabel("Редактор таблицы")
        title.setObjectName("tableTitle")
        layout.addWidget(title)

        subtitle = QLabel(f"Поле «{field_label}» — в документ вместо значения пойдёт эта таблица")
        subtitle.setObjectName("tableSubtitle")
        subtitle.setWordWrap(True)
        layout.addSpacing(2)
        layout.addWidget(subtitle)
        layout.addSpacing(8)

        self._header_checkbox = QCheckBox("Первая строка — шапка таблицы")
        self._header_checkbox.setChecked(self._has_header)
        self._header_checkbox.toggled.connect(self._on_header_toggled)
        layout.addWidget(self._header_checkbox)
        layout.addSpacing(6)

        self._grid_widget = QWidget()
        self._grid_layout = QGridLayout(self._grid_widget)
        self._grid_layout.setSpacing(0)
        self._grid_layout.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setObjectName("tableGridScroll")
        scroll.setWidget(self._grid_widget)
        scroll.setWidgetResizable(True)
        # Высота ограничена -- у большой таблицы сетка скроллится ВНУТРИ
        # себя, а не раздувает диалог на весь экран (в отличие от канвы
        # формулы, которой хватало adjustSize(), т.к. формула никогда не
        # бывает настолько большой).
        scroll.setMaximumHeight(280)
        layout.addWidget(scroll)
        layout.addSpacing(6)

        grid_toolbar = QHBoxLayout()
        grid_toolbar.addWidget(self._op_button("+ Строка", self._add_row))
        grid_toolbar.addWidget(self._op_button("+ Столбец", self._add_column))
        grid_toolbar.addWidget(self._op_button("− Строка", self._remove_active_row))
        grid_toolbar.addWidget(self._op_button("− Столбец", self._remove_active_column))
        grid_toolbar.addStretch(1)
        layout.addLayout(grid_toolbar)
        layout.addSpacing(6)

        insert_btn = QToolButton()
        insert_btn.setText("Вставить плейсхолдер")
        insert_btn.setIcon(icons.icon("tag", "#c7c7cc", 13))
        insert_btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        insert_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        insert_btn.setMenu(self._build_placeholder_menu())
        self._insert_btn = insert_btn
        insert_row = QHBoxLayout()
        insert_row.addWidget(insert_btn)
        insert_row.addStretch(1)
        layout.addLayout(insert_row)
        layout.addSpacing(6)

        text_row = QHBoxLayout()
        self._text_input = QLineEdit()
        self._text_input.setObjectName("tableTextInput")
        self._text_input.setPlaceholderText("Текст в ячейку")
        self._text_input.returnPressed.connect(self._on_insert_text_clicked)
        text_row.addWidget(self._text_input, stretch=1)
        text_row.addWidget(self._op_button("Текст", self._on_insert_text_clicked))
        layout.addLayout(text_row)
        layout.addSpacing(6)

        edit_row = QHBoxLayout()
        edit_row.addWidget(self._op_button("⌫ Удалить перед курсором", self._remove_before_cursor))
        edit_row.addWidget(self._op_button("Очистить ячейку", self._clear_active_cell))
        edit_row.addStretch(1)
        layout.addLayout(edit_row)
        layout.addSpacing(10)

        bottom_row = QHBoxLayout()
        if has_existing:
            remove_btn = QPushButton("Убрать таблицу")
            remove_btn.setStyleSheet("QPushButton{background:transparent; border:none; color:#ff453a;}")
            remove_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            remove_btn.clicked.connect(self._on_remove)
            bottom_row.addWidget(remove_btn)
        bottom_row.addStretch(1)
        cancel_btn = QPushButton("Отмена")
        cancel_btn.clicked.connect(self.reject)
        save_btn = QPushButton("Сохранить")
        save_btn.setStyleSheet(
            "QPushButton{background:#0a84ff; border:none; color:#fff; font-weight:500; "
            "padding:6px 12px; border-radius:6px;} QPushButton:hover{background:#3391ff;}"
        )
        save_btn.clicked.connect(self._on_save)
        bottom_row.addWidget(cancel_btn)
        bottom_row.addWidget(save_btn)
        layout.addLayout(bottom_row)

    @staticmethod
    def _op_button(text: str, handler) -> QPushButton:
        btn = QPushButton(text)
        btn.setStyleSheet(_OP_BTN_QSS)
        btn.clicked.connect(handler)
        return btn

    def _build_placeholder_menu(self) -> QMenu:
        menu = QMenu(self)
        for field_id, label in self._all_fields.items():
            text = label + (" (ƒ)" if field_id in self._all_formulas else "") + (
                " (▦)" if field_id in self._all_tables else ""
            )
            action = menu.addAction(text)
            action.triggered.connect(lambda checked=False, fid=field_id: self._insert_placeholder(fid))
        if self._all_fields:
            menu.addSeparator()
        # «+ Новое поле…» -- в отличие от редактора формул, тут поле можно
        # завести «на лету», не выходя в реквизиты (пользователь так решил
        # для этого редактора) -- см. _on_create_field().
        new_field_action = menu.addAction(icons.icon("plus", "#0a84ff", 13), "Новое поле…")
        new_field_action.triggered.connect(lambda checked=False: self._on_create_field())
        return menu

    def _on_create_field(self):
        label, ok = QInputDialog.getText(self, "Новое поле", "Название поля:")
        label = label.strip()
        if not ok or not label:
            return
        field_id = self._create_field(label)
        self._all_fields[field_id] = label
        self._insert_btn.setMenu(self._build_placeholder_menu())
        self._insert_placeholder(field_id)

    # -- Модель курсора: активная ячейка всегда одна (_active_r/_active_c),
    # _active_zone -- прямая ссылка на список токенов ЭТОЙ ячейки,
    # _cursor_index -- позиция вставки внутри него (0..len(zone)). -------
    def _set_active_cell(self, r: int, c: int, cursor_index: Optional[int] = None):
        self._active_r = r
        self._active_c = c
        self._active_zone = self._rows[r][c]
        self._cursor_index = len(self._active_zone) if cursor_index is None else cursor_index
        self._render_grid()

    # -- Вставка/удаление -- всегда РОВНО в позицию курсора (list.insert),
    # не в конец -- те же причины, что и в редакторе формул. ---------------
    def _insert_token(self, token: Dict):
        self._active_zone.insert(self._cursor_index, token)
        self._cursor_index += 1
        self._render_grid()

    def _insert_placeholder(self, field_id: str):
        self._insert_token({"type": "placeholder", "id": field_id})

    def _on_insert_text_clicked(self):
        text = self._text_input.text()
        if not text:
            self._text_input.setFocus()
            return
        self._insert_token({"type": "text", "value": text})
        self._text_input.clear()
        self._text_input.setFocus()

    def _remove_before_cursor(self):
        if self._cursor_index <= 0:
            return
        self._active_zone.pop(self._cursor_index - 1)
        self._cursor_index -= 1
        self._render_grid()

    def _clear_active_cell(self):
        self._active_zone.clear()
        self._cursor_index = 0
        self._render_grid()

    def _on_header_toggled(self, checked: bool):
        self._has_header = checked
        self._render_grid()

    # -- Строки/столбцы -- хотя бы одна строка и один столбец остаются
    # всегда (кнопки удаления не действуют на последнюю). ------------------
    def _add_row(self):
        cols = len(self._rows[0])
        self._rows.append([[] for _ in range(cols)])
        self._set_active_cell(len(self._rows) - 1, 0)

    def _add_column(self):
        for row in self._rows:
            row.append([])
        self._set_active_cell(self._active_r, len(self._rows[0]) - 1)

    def _remove_active_row(self):
        if len(self._rows) <= 1:
            return
        self._rows.pop(self._active_r)
        r = min(self._active_r, len(self._rows) - 1)
        self._set_active_cell(r, min(self._active_c, len(self._rows[0]) - 1))

    def _remove_active_column(self):
        if len(self._rows[0]) <= 1:
            return
        c = self._active_c
        for row in self._rows:
            row.pop(c)
        self._set_active_cell(self._active_r, min(c, len(self._rows[0]) - 1))

    # -- Отрисовка -- перестраивается целиком на КАЖДОЕ изменение, тот же
    # приём, что и у редактора формул/остального конструктора. -------------
    def _render_grid(self):
        self._clear_layout(self._grid_layout)
        for r, row in enumerate(self._rows):
            for c, tokens in enumerate(row):
                is_active = (r == self._active_r and c == self._active_c)
                cell = _make_flow_widget("tableEditorCell", margin=7, spacing=2)
                cell.setMinimumWidth(120)
                cell.setProperty("tableCellHeader", self._has_header and r == 0)
                cell.setProperty("tableCellActive", is_active)
                cell.style().unpolish(cell)
                cell.style().polish(cell)
                # Клик по СВОБОДНОМУ месту ячейки (не по конкретному
                # токену -- те получают клик напрямую от Qt, см. докстринг
                # formula_editor_dialog.py насчёт того, почему тут не нужен
                # аналог DOM stopPropagation()) -- курсор в конец этой
                # ячейки; для ещё не активной ячейки это же попутно и
                # выбирает её (см. _set_active_cell()).
                cell.mousePressEvent = lambda event, rr=r, cc=c: self._set_active_cell(rr, cc)
                self._render_cell_zone(cell, tokens, is_active)
                self._grid_layout.addWidget(cell, r, c)

        self._grid_widget.layout().activate()
        for cell in self._grid_widget.findChildren(QWidget, "tableEditorCell"):
            self._apply_flow_height(cell, min_height=32)

        self.layout().activate()
        self.adjustSize()
        self.setFocus()

    @staticmethod
    def _apply_flow_height(widget: QWidget, min_height: int):
        width = widget.width()
        if width <= 1:
            width = 140
        needed = widget.layout().heightForWidth(width)
        widget.setFixedHeight(max(min_height, needed))

    @staticmethod
    def _clear_layout(layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.hide()
                widget.deleteLater()

    def _render_cell_zone(self, container: QWidget, tokens: List[Dict], is_active: bool):
        layout = container.layout()
        cursor_index = self._cursor_index if is_active else -1
        if cursor_index == 0:
            layout.addWidget(self._make_caret())
        for index, token in enumerate(tokens):
            widget = self._render_cell_token(token, index, is_active)
            layout.addWidget(widget)
            if cursor_index == index + 1:
                layout.addWidget(self._make_caret())

    def _render_cell_token(self, token: Dict, index: int, is_active: bool) -> QWidget:
        ttype = token.get("type")
        text = self._all_fields.get(token["id"], token["id"]) if ttype == "placeholder" else token.get("value", "")
        if is_active:
            def on_click(before: bool, i=index):
                self._set_active_cell(self._active_r, self._active_c, i if before else i + 1)

            label = _ClickableLabel(text, on_click)
        else:
            label = QLabel(text)
        label.setProperty("tableToken", ttype)
        return label

    @staticmethod
    def _make_caret() -> QFrame:
        caret = _CaretFrame()
        caret.setObjectName("tableCaret")
        return caret

    # -- Завершение ---------------------------------------------------------
    def _on_save(self):
        self.removed = False
        self.rows = [[_clone_cell(cell) for cell in row] for row in self._rows]
        self.has_header = self._has_header
        self.accept()

    def _on_remove(self):
        self.removed = True
        self.accept()

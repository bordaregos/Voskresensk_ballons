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

Ячейки можно объединять по строкам/столбцам (см. src/services/
table_merges.py): выделение диапазона -- Shift+клик от активной ячейки,
«Объединить»/«Разъединить» в тулбаре сетки; объединения лежат в
необязательном ключе "merges" таблицы, сетка rows при этом остаётся
полной прямоугольной.

Ячейка может быть формулой «как в Excel» (см. src/services/
table_formulas.py): токен {"type": "formula", "expr", "decimals"} --
единственный в ячейке. Столбцы подписаны A, B, C…, строки -- 1, 2, 3…
(шапка считается строкой); формулу вводят в строке «Формула», «Заполнить
вниз/вправо» протягивает её по выделенному диапазону со сдвигом
относительных ссылок. В сетке формула показывается вместе с предпросмотром
значения; рандом-чипы в предпросмотре -- пробное значение, в документе
будет своё.

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
    QSpinBox, QMessageBox,
)

from ..services import table_merges, table_formulas
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
QWidget#tableEditorCell[tableCellSelected="true"] { background: rgba(10, 132, 255, 12); }
QWidget#tableEditorCell[tableCellActive="true"] { border: 1.5px solid #0a84ff; background: rgba(10, 132, 255, 20); }
QLabel[tableToken="placeholder"] {
    background: rgba(100, 210, 255, 40); color: #64d2ff;
    border: 1px solid rgba(100, 210, 255, 100); border-radius: 5px; padding: 2px 7px; font-size: 11px;
}
QLabel[tableToken="text"] { color: #e5e5e7; font-size: 11.5px; }
QLabel[tableToken="formula"] {
    background: rgba(255, 159, 10, 35); color: #ff9f0a;
    border: 1px solid rgba(255, 159, 10, 100); border-radius: 5px; padding: 2px 7px; font-size: 11px;
}
QLabel[tableToken="formulaError"] {
    background: rgba(255, 69, 58, 35); color: #ff453a;
    border: 1px solid rgba(255, 69, 58, 100); border-radius: 5px; padding: 2px 7px; font-size: 11px;
}
QLabel#tableAxis { color: #8e8e93; font-size: 10.5px; background: #232325; border: 0.5px solid #38383a; padding: 2px 6px; }
QLabel#formulaHint { color: #ff9f0a; font-size: 11.5px; }
QWidget#tableEditorCell[tableCellRef="true"] { border: 1.5px dashed #ff9f0a; }
QLabel#formulaPreview { color: #8e8e93; font-size: 11.5px; }
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
        sample_text: Optional[Callable[[str], str]] = None,
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
        # Пробный текст поля для предпросмотра формул (рандом-поле -- образец
        # значения); без колбэка чип-плейсхолдер в предпросмотре не считается.
        self._sample_text = sample_text
        self._samples: Dict[str, str] = {}

        if existing_table:
            self._rows: List[List[List[Dict]]] = [
                [_clone_cell(cell) for cell in row] for row in existing_table["rows"]
            ]
            self._has_header = bool(existing_table.get("has_header"))
            self._merges: List[Dict] = table_merges.normalize_merges(
                existing_table.get("merges"), len(self._rows), len(self._rows[0]) if self._rows else 0
            )
        else:
            self._rows = [[[], []], [[], []]]  # пустая сетка 2×2 по умолчанию
            self._has_header = False
            self._merges = []

        self._active_r = 0
        self._active_c = 0
        self._active_zone: List[Dict] = self._rows[0][0]
        self._cursor_index = 0
        # Противоположный угол выделения диапазона (Shift+клик) -- второй
        # угол всегда активная ячейка; None -- выделена одна ячейка.
        self._sel_end: Optional[tuple] = None

        self.removed = False
        self.rows: List[List[List[Dict]]] = []
        self.merges: List[Dict] = []
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
        # Размер области подгоняется под сетку в _fit_scroll_to_grid() --
        # диалог растёт вместе с таблицей, а скролл ВНУТРИ включается лишь
        # когда сетка не помещается на экране.
        self._scroll = scroll
        layout.addWidget(scroll)
        layout.addSpacing(6)

        grid_toolbar = QHBoxLayout()
        grid_toolbar.addWidget(self._op_button("+ Строка", self._add_row))
        grid_toolbar.addWidget(self._op_button("+ Столбец", self._add_column))
        grid_toolbar.addWidget(self._op_button("− Строка", self._remove_active_row))
        grid_toolbar.addWidget(self._op_button("− Столбец", self._remove_active_column))
        grid_toolbar.addStretch(1)
        layout.addLayout(grid_toolbar)
        merge_toolbar = QHBoxLayout()
        merge_toolbar.addWidget(self._op_button("Объединить ячейки", self._merge_selection))
        merge_toolbar.addWidget(self._op_button("Разъединить", self._unmerge_active))
        merge_hint = QLabel("Диапазон — Shift+клик")
        merge_hint.setObjectName("tableSubtitle")
        merge_toolbar.addWidget(merge_hint)
        merge_toolbar.addStretch(1)
        layout.addSpacing(4)
        layout.addLayout(merge_toolbar)
        layout.addSpacing(6)

        self._formula_hint = QLabel(
            "Режим формулы: кликайте по ячейкам — их адреса добавятся в формулу; "
            "Shift+клик по другой ячейке делает диапазон. Enter или «Готово» — применить."
        )
        self._formula_hint.setObjectName("formulaHint")
        self._formula_hint.setWordWrap(True)
        self._formula_hint.hide()
        layout.addWidget(self._formula_hint)
        formula_row = QHBoxLayout()
        self._formula_input = QLineEdit()
        self._formula_input.setObjectName("tableTextInput")
        self._formula_input.setPlaceholderText("Формула, например =(B1-B2)/B1*100")
        # Адрес, вставленный кликом: (начало, конец, первая ячейка) -- чтобы
        # Shift+клик мог расширить его до диапазона.
        self._last_point = None
        self._formula_mode = False
        self._formula_input.returnPressed.connect(self._apply_formula)
        self._formula_input.textEdited.connect(lambda _t: self._set_formula_mode(True))
        self._formula_input.textChanged.connect(self._update_formula_preview)
        formula_row.addWidget(self._formula_input, stretch=1)
        self._decimals_spin = QSpinBox()
        self._decimals_spin.setRange(0, 6)
        self._decimals_spin.setValue(table_formulas.DEFAULT_DECIMALS)
        self._decimals_spin.setSuffix(" зн.")
        self._decimals_spin.setToolTip("Знаков после запятой в результате")
        formula_row.addWidget(self._decimals_spin)
        self._formula_btn = self._op_button("ƒ Формула", self._on_formula_button)
        formula_row.addWidget(self._formula_btn)
        self._formula_cancel_btn = self._op_button("Отмена", self._cancel_formula)
        self._formula_cancel_btn.hide()
        formula_row.addWidget(self._formula_cancel_btn)
        layout.addLayout(formula_row)
        self._formula_preview = QLabel("")
        self._formula_preview.setObjectName("formulaPreview")
        self._formula_preview.setWordWrap(True)
        layout.addWidget(self._formula_preview)
        fill_row = QHBoxLayout()
        fill_row.addWidget(self._op_button("Заполнить вниз", self._fill_down))
        fill_row.addWidget(self._op_button("Заполнить вправо", self._fill_right))
        fill_hint = QLabel("По выделенному диапазону (Shift+клик), формула — из его первой строки/столбца")
        fill_hint.setObjectName("tableSubtitle")
        fill_hint.setWordWrap(True)
        fill_row.addWidget(fill_hint, stretch=1)
        layout.addLayout(fill_row)
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
        # Скрытая под объединением ячейка недоступна -- активным становится
        # якорь области.
        merge = table_merges.find_merge(self._merges, r, c)
        if merge is not None:
            r, c = merge["r"], merge["c"]
        self._sel_end = None
        self._last_point = None
        self._active_r = r
        self._active_c = c
        self._active_zone = self._rows[r][c]
        self._cursor_index = len(self._active_zone) if cursor_index is None else cursor_index
        self._load_formula_input()
        self._render_grid()

    # -- Формулы -------------------------------------------------------------
    def _is_formula_active(self) -> bool:
        return table_formulas.is_formula_cell(self._active_zone)

    def _load_formula_input(self):
        """Строка формулы показывает формулу активной ячейки (или пуста)."""
        self._formula_mode = False
        if self._is_formula_active():
            token = self._active_zone[0]
            self._formula_input.setText("=" + token.get("expr", ""))
            self._decimals_spin.setValue(int(token.get("decimals", table_formulas.DEFAULT_DECIMALS)))
        else:
            self._formula_input.clear()
        self._sync_formula_controls()

    def _sync_formula_controls(self):
        self._formula_hint.setVisible(self._formula_mode)
        self._formula_cancel_btn.setVisible(self._formula_mode)
        self._formula_btn.setText("✓ Готово" if self._formula_mode else "ƒ Формула")

    def _set_formula_mode(self, on: bool):
        if self._formula_mode == on:
            return
        self._formula_mode = on
        if on and not self._formula_input.text().strip():
            self._formula_input.setText("=")
        self._sync_formula_controls()

    def _on_formula_button(self):
        """«ƒ Формула» включает режим формулы для активной ячейки, «✓ Готово»
        (та же кнопка) -- применяет."""
        if self._formula_mode:
            self._apply_formula()
            return
        self._set_formula_mode(True)
        self._formula_input.setFocus()
        self._formula_input.setCursorPosition(len(self._formula_input.text()))
        self._render_grid_keep_input()

    def _cancel_formula(self):
        self._last_point = None
        self._load_formula_input()
        self._render_grid()

    def _render_grid_keep_input(self):
        """Перерисовка сетки (подсветка ссылок), не уводя фокус из строки формулы."""
        self._render_grid()
        self._formula_input.setFocus()

    def _apply_formula(self):
        """Записывает формулу из строки в активную ячейку (заменяя её
        прежнее содержимое) и выходит из режима формулы."""
        expr = self._formula_input.text().strip().lstrip("=").strip()
        error = table_formulas.validate_expr(expr)
        if error:
            QMessageBox.warning(self, "Формула", error)
            return
        self._active_zone[:] = [{"type": "formula", "expr": expr, "decimals": self._decimals_spin.value()}]
        self._cursor_index = 1
        self._formula_mode = False
        self._last_point = None
        self._sync_formula_controls()
        self._render_grid()

    def _update_formula_preview(self):
        text = self._formula_input.text().strip().lstrip("=").strip()
        if not text:
            self._formula_preview.setText("")
            return
        error = table_formulas.validate_expr(text)
        self._formula_preview.setText(f"Ошибка: {error}" if error else "")

    def _sample_for(self, field_id: str) -> str:
        if field_id not in self._samples:
            self._samples[field_id] = self._sample_text(field_id) if self._sample_text else ""
        return self._samples[field_id]

    def _evaluate_preview(self):
        """(texts, errors) текущей сетки -- для предпросмотра формул."""
        def resolve(token: Dict) -> str:
            if token.get("type") == "text":
                return token.get("value", "")
            return self._sample_for(token.get("id", ""))

        def get_ph(field_id: str) -> float:
            try:
                return float(self._sample_for(field_id).strip().replace(",", "."))
            except ValueError:
                raise table_formulas.FormulaError(f"Поле «{self._all_fields.get(field_id, field_id)}» — нет пробного числа.")

        return table_formulas.evaluate_table(
            self._rows, resolve, get_ph, lambda r, c: table_merges.is_covered(self._merges, r, c)
        )

    def _fill(self, down: bool):
        r1, c1, r2, c2 = self._selection_rect()
        if (down and r1 == r2) or (not down and c1 == c2):
            return  # нечего протягивать -- диапазон в одну строку/столбец
        for r in range(r1, r2 + 1):
            for c in range(c1, c2 + 1):
                if (down and r == r1) or (not down and c == c1):
                    continue
                if table_merges.is_covered(self._merges, r, c) or table_merges.find_merge(self._merges, r, c):
                    continue
                src_r, src_c = (r1, c) if down else (r, c1)
                source = self._rows[src_r][src_c]
                if table_merges.find_merge(self._merges, src_r, src_c):
                    continue
                d_row, d_col = r - src_r, c - src_c
                if table_formulas.is_formula_cell(source):
                    token = dict(source[0])
                    token["expr"] = table_formulas.shift_expr(token.get("expr", ""), d_row, d_col)
                    self._rows[r][c] = [token]
                else:
                    self._rows[r][c] = _clone_cell(source)
        self._set_active_cell(self._active_r, self._active_c)

    def _fill_down(self):
        self._fill(down=True)

    def _fill_right(self):
        self._fill(down=False)

    def _fix_formulas_after_removal(self, adjust: Callable[[str], str]):
        for row in self._rows:
            for cell in row:
                if table_formulas.is_formula_cell(cell):
                    cell[0]["expr"] = adjust(cell[0].get("expr", ""))

    # -- Вставка/удаление -- всегда РОВНО в позицию курсора (list.insert),
    # не в конец -- те же причины, что и в редакторе формул. ---------------
    def _insert_token(self, token: Dict):
        self._active_zone.insert(self._cursor_index, token)
        self._cursor_index += 1
        self._render_grid()

    def _insert_placeholder(self, field_id: str):
        # В ячейке-формуле чип не вставляется токеном -- он идёт в текст
        # формулы как {id}.
        if self._is_formula_active() or self._formula_mode:
            self._set_formula_mode(True)
            self._formula_input.insert("{" + field_id + "}")
            self._formula_input.setFocus()
            return
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

    def _point_cell(self, r: int, c: int, extend: bool):
        """Клик в режиме формулы: адрес ячейки вставляется в позицию курсора
        строки формулы. Shift+клик сразу после такой вставки превращает
        адрес в диапазон «первая:эта»."""
        merge = table_merges.find_merge(self._merges, r, c)
        if merge is not None:
            r, c = merge["r"], merge["c"]
        if (r, c) == (self._active_r, self._active_c):
            return  # ссылка ячейки на саму себя -- циклическая
        field = self._formula_input
        text, pos = field.text(), field.cursorPosition()
        last = self._last_point
        if extend and last is not None and last[1] == pos:
            start, first = last[0], last[2]
            ref = table_formulas.cell_name(*first) + ":" + table_formulas.cell_name(r, c)
            text = text[:start] + ref + text[pos:]
        else:
            start, first = pos, (r, c)
            ref = table_formulas.cell_name(r, c)
            text = text[:pos] + ref + text[pos:]
        field.setText(text)
        field.setCursorPosition(start + len(ref))
        self._last_point = (start, start + len(ref), first)
        self._render_grid_keep_input()

    def _on_cell_pressed(self, event, r: int, c: int):
        """В режиме указания -- вставка адреса в формулу (_point_cell()).
        Иначе Shift+клик -- выделение диапазона от активной ячейки до
        (r, c), обычный клик -- активная ячейка."""
        if self._formula_mode:
            self._point_cell(r, c, bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier))
            return
        if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            self._sel_end = (r, c)
            self._render_grid()
        else:
            self._set_active_cell(r, c)

    def _selection_rect(self) -> table_merges.Rect:
        """Выделение с учётом объединений -- не рассекает их."""
        er, ec = self._sel_end if self._sel_end else (self._active_r, self._active_c)
        return table_merges.expand_rect(self._merges, (self._active_r, self._active_c, er, ec))

    def _merge_selection(self):
        rect = self._selection_rect()
        anchor = table_merges.merge_cells(self._rows, self._merges, rect)
        if anchor is None:
            return
        self._set_active_cell(*anchor)

    def _unmerge_active(self):
        anchor = table_merges.unmerge_cell(self._merges, self._active_r, self._active_c)
        if anchor is not None:
            self._set_active_cell(*anchor)

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
        removed = self._active_r
        table_merges.remove_row(self._rows, self._merges, removed)
        self._fix_formulas_after_removal(lambda e: table_formulas.adjust_for_row_removal(e, removed))
        r = min(self._active_r, len(self._rows) - 1)
        self._set_active_cell(r, min(self._active_c, len(self._rows[0]) - 1))

    def _remove_active_column(self):
        if len(self._rows[0]) <= 1:
            return
        c = self._active_c
        table_merges.remove_column(self._rows, self._merges, c)
        self._fix_formulas_after_removal(lambda e: table_formulas.adjust_for_column_removal(e, c))
        self._set_active_cell(self._active_r, min(c, len(self._rows[0]) - 1))

    # -- Отрисовка -- перестраивается целиком на КАЖДОЕ изменение, тот же
    # приём, что и у редактора формул/остального конструктора. -------------
    def _render_grid(self):
        self._clear_layout(self._grid_layout)
        sel = self._selection_rect()
        texts, errors = self._evaluate_preview()
        # Подсветка ячеек, на которые ссылается редактируемая формула.
        ref_cells = (
            table_formulas.referenced_cells(self._formula_input.text())
            if self._formula_mode else set()
        )
        for c in range(len(self._rows[0])):
            self._add_axis_label(table_formulas.cell_name(0, c).rstrip("0123456789"), 0, c + 1)
        for r in range(len(self._rows)):
            self._add_axis_label(str(r + 1), r + 1, 0)
        for r, row in enumerate(self._rows):
            for c, tokens in enumerate(row):
                if table_merges.is_covered(self._merges, r, c):
                    continue
                merge = table_merges.find_merge(self._merges, r, c)
                rowspan = merge["rowspan"] if merge else 1
                colspan = merge["colspan"] if merge else 1
                is_selected = (
                    self._sel_end is not None
                    and sel[0] <= r <= sel[2] and sel[1] <= c <= sel[3]
                )
                is_active = (r == self._active_r and c == self._active_c)
                cell = _make_flow_widget("tableEditorCell", margin=7, spacing=2)
                cell.setMinimumWidth(120)
                cell.setProperty("tableCellHeader", self._has_header and r == 0)
                cell.setProperty("tableCellActive", is_active)
                cell.setProperty("tableCellSelected", is_selected)
                cell.setProperty("tableCellRef", (r, c) in ref_cells)
                cell.style().unpolish(cell)
                cell.style().polish(cell)
                # Клик по СВОБОДНОМУ месту ячейки (не по конкретному
                # токену -- те получают клик напрямую от Qt, см. докстринг
                # formula_editor_dialog.py насчёт того, почему тут не нужен
                # аналог DOM stopPropagation()) -- курсор в конец этой
                # ячейки; для ещё не активной ячейки это же попутно и
                # выбирает её (см. _set_active_cell()).
                cell.mousePressEvent = lambda event, rr=r, cc=c: self._on_cell_pressed(event, rr, cc)
                self._render_cell_zone(cell, tokens, is_active, texts[r][c], errors.get((r, c)))
                self._grid_layout.addWidget(cell, r + 1, c + 1, rowspan, colspan)
                # Без явного show() у уже показанного диалога новая ячейка
                # остаётся скрытой до следующего цикла событий, и раскладка
                # не учитывает её размер (сетка "схлопывается").
                cell.show()

        self._grid_widget.layout().activate()
        for cell in self._grid_widget.findChildren(QWidget, "tableEditorCell"):
            self._apply_flow_height(cell, min_height=32)

        self._fit_scroll_to_grid()
        self.layout().activate()
        self.adjustSize()
        self.setFocus()

    def _add_axis_label(self, text: str, row: int, col: int):
        label = QLabel(text)
        label.setObjectName("tableAxis")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._grid_layout.addWidget(label, row, col)
        label.show()

    def _fit_scroll_to_grid(self):
        """Минимальный размер области прокрутки -- размер сетки (плюс рамка
        и место под полосы), но не больше доли экрана: маленькая таблица
        показывается целиком без полос, большая -- скроллится."""
        # Высоты ячеек только что зафиксированы (_apply_flow_height()) --
        # кэш размеров сетки устарел.
        self._grid_layout.invalidate()
        self._grid_layout.activate()
        hint = self._grid_layout.totalMinimumSize()
        screen = self.screen().availableGeometry() if self.screen() else None
        max_w = int(screen.width() * 0.8) if screen else 1000
        max_h = int(screen.height() * 0.5) if screen else 500
        bar = self._scroll.style().pixelMetric(self._scroll.style().PixelMetric.PM_ScrollBarExtent)
        width = hint.width() + 4
        height = hint.height() + 4
        if width > max_w:
            height += bar  # появится горизонтальная полоса
        if height > max_h:
            width += bar  # появится вертикальная полоса
        self._scroll.setMinimumSize(min(width, max_w), min(height, max_h))

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

    def _render_cell_zone(
        self, container: QWidget, tokens: List[Dict], is_active: bool,
        preview: str = "", error: Optional[str] = None,
    ):
        layout = container.layout()
        if table_formulas.is_formula_cell(tokens):
            # Ячейка-формула -- один нередактируемый токен «ƒ значение»; само
            # выражение -- в подсказке и в строке формулы при выборе ячейки.
            expr = tokens[0].get("expr", "")
            label = QLabel(f"ƒ {preview}" if error is None else "ƒ #ОШИБКА")
            label.setProperty("tableToken", "formula" if error is None else "formulaError")
            label.setToolTip(f"={expr}" + (f"\n{error}" if error else ""))
            layout.addWidget(label)
            return
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
        if ttype == "placeholder":
            text = self._all_fields.get(token["id"], token["id"])
        elif ttype == "formula":
            # Формула, склеенная с чем-то при объединении ячеек, -- обычным токеном.
            text = "ƒ " + token.get("expr", "")
        else:
            text = token.get("value", "")
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
        self.merges = [dict(m) for m in self._merges]
        self.accept()

    def _on_remove(self):
        self.removed = True
        self.accept()

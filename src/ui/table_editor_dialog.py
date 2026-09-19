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
настоящую .docx-таблицу, построенную из rows/has_header/merges/align
этого диалога (см. докстринги обеих функций).

Объединение ячеек (merges) и центрирование (align) портированы из того же
JS-мокапа (см. его комментарий у tableEditorState) -- те же имена понятий,
адаптированные под Qt:
- self._merges -- список {"r", "c", "row_span", "col_span"}, тех же
  прямоугольников поверх self._rows, что и merges мокапа (в JSON-словаре
  результата -- snake_case ключи row_span/col_span, а не camelCase
  rowSpan/colSpan мокапа, тем же принципом конвертации, что и hasHeader ->
  has_header). Ячейка, накрытая объединением, но не являющаяся его верхним
  левым углом, просто не получает свой QWidget в сетке -- вместо этого
  QGridLayout.addWidget() зовётся с row_span/col_span у ОДНОЙ ячейки
  верхнего левого угла (родное объединение ячеек QGridLayout, аналог
  colspan/rowspan HTML-мокапа, никакого doc.getElementById-подобного
  прятанья не нужно).
- Выделение диапазона -- self._sel_anchor_r/c (последний ПРОСТОЙ, без
  Shift, клик) вместе с self._active_r/c (последний клик вообще, включая
  Shift) -- та же пара, что selAnchorR/C и activeR/C мокапа, тот же способ
  восстановить прямоугольник диапазона (_selection_rect()).
- self._align -- матрица bool той же формы, что и rows (mockup:
  tableEditorState.align) -- центрирование одной ячейки или всего
  выделенного диапазона разом, независимо от merges.

Ключевое отличие Qt-порта от DOM-мокапа для ОБЪЕДИНЁННОЙ ячейки: в мокапе
понадобилось вручную чинить два CSS-упущения (внутренний div без
width/height:100% и с max-width:240px не дотягивался до реальных границ
уже увеличенной colspan/rowspan <td>, см. .table-editor-cell-merged в
docs/design/вводная_часть.html). У QGridLayout это не нужно -- по
умолчанию любой добавленный виджет БЕЗ явного alignment растягивается по
всей выделенной ему ячейке сетки (в т.ч. составной, из нескольких строк/
столбцов при row_span/col_span > 1) -- НО именно поэтому
_apply_flow_height() (см. её докстринг) здесь специально сделан через
setMinimumHeight(), а не setFixedHeight(), как в formula_editor_dialog.py:
setFixedHeight() -- явный Fixed size policy по вертикали, отключающий это
растяжение, что для объединённой (rowSpan>1) ячейки воспроизвело бы ТОТ ЖЕ
класс бага, что был в мокапе (подсветка/центрирование ограничены размером
одной обычной строки, а не всей высоты объединения)."""

from typing import Callable, Dict, List, Optional, Tuple

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
QWidget#tableEditorCell[tableCellSelected="true"] { background: rgba(10, 132, 255, 45); }
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


def _make_flow_widget(object_name: str, margin: int, spacing: int, center: bool = False) -> QWidget:
    """QWidget с FlowLayout, готовый переноситься на несколько строк --
    почти копия _make_flow_widget() из formula_editor_dialog.py (см. её
    докстринг насчёт setHeightForWidth(True)), с добавленным center= --
    формула им не пользуется, только эта, для чекбокса «По центру»
    (FlowLayout.center, см. docstring модуля)."""
    container = QWidget()
    container.setObjectName(object_name)
    FlowLayout(container, margin=margin, spacing=spacing, center=center)
    policy = container.sizePolicy()
    policy.setHeightForWidth(True)
    container.setSizePolicy(policy)
    return container


def _clone_cell(tokens: List[Dict]) -> List[Dict]:
    return [dict(token) for token in tokens]


def _build_align_matrix(rows: List[List[List[Dict]]], existing_align: Optional[List[List[bool]]]) -> List[List[bool]]:
    """Матрица bool формы rows -- False там, где existing_align вообще нет,
    или он короче/уже (рассинхрон формы, например после ручной правки
    field_tables), а не IndexError -- копия buildAlignMatrix() мокапа."""
    return [
        [
            bool(existing_align[r][c]) if existing_align and r < len(existing_align) and c < len(existing_align[r]) else False
            for c in range(len(row))
        ]
        for r, row in enumerate(rows)
    ]


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
            self._merges: List[Dict] = [dict(m) for m in existing_table.get("merges", [])]
        else:
            self._rows = [[[], []], [[], []]]  # пустая сетка 2×2 по умолчанию
            self._has_header = False
            self._merges = []
        # Матрица той же формы, что и self._rows, с False по умолчанию --
        # безопасно и для таблиц без сохранённого align вовсе (обратная
        # совместимость со старыми field_tables без этого ключа), и при
        # рассинхроне формы (см. _build_align_matrix()).
        self._align: List[List[bool]] = _build_align_matrix(
            self._rows, existing_table.get("align") if existing_table else None
        )

        self._active_r = 0
        self._active_c = 0
        # Якорь выделения -- последняя ячейка, выбранная ПРОСТЫМ (без Shift)
        # кликом; вместе с _active_r/c (двигается и при Shift+клике)
        # определяет прямоугольник выделения для объединения/центрирования
        # (см. _selection_rect()). См. докстринг модуля насчёт соответствия
        # мокапу.
        self._sel_anchor_r = 0
        self._sel_anchor_c = 0
        self._active_zone: List[Dict] = self._rows[0][0]
        self._cursor_index = 0

        self.removed = False
        self.rows: List[List[List[Dict]]] = []
        self.has_header = self._has_header
        self.merges: List[Dict] = []
        self.align: List[List[bool]] = []

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

        hint = QLabel("Shift+клик по ячейке — выделить диапазон для объединения")
        hint.setStyleSheet("color:#636366; font-size:11px;")
        layout.addWidget(hint)
        layout.addSpacing(4)

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

        merge_toolbar = QHBoxLayout()
        merge_toolbar.addWidget(self._op_button("⊞ Объединить", self._merge_selected_cells))
        merge_toolbar.addWidget(self._op_button("⊟ Разъединить", self._unmerge_active_cell))
        merge_toolbar.addStretch(1)
        # Чекбокс сам по себе не переключается кликом мимо активной ячейки
        # -- его checked-состояние на каждый _render_grid() пересинхронизи-
        # руется с self._align верхней левой ячейки ТЕКУЩЕГО выделения
        # (см. _render_grid()), в отличие от self._header_checkbox, который
        # выставляется ровно один раз при открытии диалога (табличный, а
        # не поячеечный признак).
        self._center_checkbox = QCheckBox("По центру")
        self._center_checkbox.toggled.connect(self._set_cell_align)
        merge_toolbar.addWidget(self._center_checkbox)
        layout.addLayout(merge_toolbar)
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
    def _set_active_cell(self, r: int, c: int):
        """Обычный (не-Shift) клик по ячейке -- всегда схлопывает выделение
        в одну ячейку, якорь совпадает с активной (см. докстринг модуля
        насчёт _sel_anchor_r/c). Курсор -- в конец содержимого этой ячейки;
        для точной позиции ВНУТРИ уже активной ячейки см. _set_cursor_index()."""
        self._active_r = r
        self._active_c = c
        self._sel_anchor_r = r
        self._sel_anchor_c = c
        self._active_zone = self._rows[r][c]
        self._cursor_index = len(self._active_zone)
        self._render_grid()

    def _extend_selection(self, r: int, c: int):
        """Shift+клик -- якорь (последний ПРОСТОЙ клик) не трогаем, двигаем
        только активную ячейку; прямоугольник между ними -- _selection_rect()."""
        self._active_r = r
        self._active_c = c
        self._active_zone = self._rows[r][c]
        self._cursor_index = len(self._active_zone)
        self._render_grid()

    def _set_cursor_index(self, index: int):
        """Точная позиция курсора ВНУТРИ уже активной ячейки (клик по
        половине токена, или по свободному месту уже единственной активной
        ячейки) -- r/c/якорь не меняются, в отличие от _set_active_cell()."""
        self._cursor_index = index
        self._render_grid()

    def _on_cell_background_clicked(self, event, r: int, c: int):
        """Клик по СВОБОДНОМУ месту ячейки (не по конкретному токену -- те
        получают клик напрямую от Qt, см. докстринг formula_editor_dialog.py
        насчёт того, почему тут не нужен аналог DOM stopPropagation()).
        Shift+клик расширяет выделение; обычный клик по свободному месту
        уже единственной активной ячейки -- курсор в конец (эквивалент
        JS-мокапа: cell.onclick, см. её комментарий); клик по ещё
        неактивной ячейке (или когда выделен целый диапазон) сперва
        схлопывает выделение и выбирает её."""
        if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            self._extend_selection(r, c)
            return
        is_active = r == self._active_r and c == self._active_c
        if is_active and self._is_single_cell_selection():
            self._set_cursor_index(len(self._rows[r][c]))
        else:
            self._set_active_cell(r, c)

    # -- Объединение ячеек: та же геометрия, что у merges мокапа (см.
    # докстринг модуля). Индексы -- строго grid-координаты self._rows, не
    # координаты видимых QWidget'ов (у накрытых объединением ячеек своего
    # QWidget вообще нет, см. _render_grid()). ------------------------------
    def _get_covering_merge(self, r: int, c: int) -> Optional[Dict]:
        for m in self._merges:
            if m["r"] <= r <= m["r"] + m["row_span"] - 1 and m["c"] <= c <= m["c"] + m["col_span"] - 1:
                return m
        return None

    def _get_merge_at(self, r: int, c: int) -> Optional[Dict]:
        m = self._get_covering_merge(r, c)
        return m if m and m["r"] == r and m["c"] == c else None

    def _is_cell_hidden(self, r: int, c: int) -> bool:
        m = self._get_covering_merge(r, c)
        return m is not None and not (m["r"] == r and m["c"] == c)

    def _expand_to_merge_footprint(self, r: int, c: int) -> Tuple[int, int, int, int]:
        m = self._get_merge_at(r, c)
        if m:
            return m["r"], m["c"], m["r"] + m["row_span"] - 1, m["c"] + m["col_span"] - 1
        return r, c, r, c

    def _selection_rect(self) -> Tuple[int, int, int, int]:
        """(r0, c0, r1, c1) -- прямоугольник выделения, объединение
        footprint'ов якоря и активной ячейки (обе всегда указывают на
        верхний левый угол своей области -- обычной или уже объединённой)."""
        ar0, ac0, ar1, ac1 = self._expand_to_merge_footprint(self._sel_anchor_r, self._sel_anchor_c)
        br0, bc0, br1, bc1 = self._expand_to_merge_footprint(self._active_r, self._active_c)
        return min(ar0, br0), min(ac0, bc0), max(ar1, br1), max(ac1, bc1)

    def _is_single_cell_selection(self) -> bool:
        r0, c0, r1, c1 = self._selection_rect()
        return r0 == r1 and c0 == c1

    def _selection_is_mergeable(self) -> bool:
        """Диапазон можно объединить, если в нём больше одной ячейки и ни
        одно уже существующее объединение не пересекает границу диапазона
        ЧАСТИЧНО -- полностью лежащие внутри существующие объединения ОК
        (поглощаются новым, более крупным, см. _merge_selected_cells())."""
        r0, c0, r1, c1 = self._selection_rect()
        if r0 == r1 and c0 == c1:
            return False
        for r in range(r0, r1 + 1):
            for c in range(c0, c1 + 1):
                m = self._get_covering_merge(r, c)
                if m and (m["r"] < r0 or m["c"] < c0 or m["r"] + m["row_span"] - 1 > r1 or m["c"] + m["col_span"] - 1 > c1):
                    return False
        return True

    def _merge_selected_cells(self):
        if not self._selection_is_mergeable():
            return  # частичное пересечение с существующим объединением -- молча ничего не делаем, тот же минимализм, что у «− Строка»/«− Столбец» на границе минимального размера
        r0, c0, r1, c1 = self._selection_rect()
        self._merges = [
            m for m in self._merges
            if not (m["r"] >= r0 and m["c"] >= c0 and m["r"] + m["row_span"] - 1 <= r1 and m["c"] + m["col_span"] - 1 <= c1)
        ]
        # Содержимое объединённой ячейки -- содержимое верхней левой ячейки
        # диапазона, остальное теряется (как при объединении в Word/Excel).
        for r in range(r0, r1 + 1):
            for c in range(c0, c1 + 1):
                if r == r0 and c == c0:
                    continue
                self._rows[r][c] = []
        self._merges.append({"r": r0, "c": c0, "row_span": r1 - r0 + 1, "col_span": c1 - c0 + 1})
        self._set_active_cell(r0, c0)  # заодно схлопывает выделение к одной ячейке

    def _unmerge_active_cell(self):
        m = self._get_merge_at(self._active_r, self._active_c)
        if not m:
            return  # активная ячейка не является верхним левым углом объединения -- нечего разъединять
        self._merges = [x for x in self._merges if x is not m]
        self._render_grid()

    def _set_cell_align(self, checked: bool):
        """Центрирование -- применяется ко всем ячейкам текущего выделения
        (для одной активной ячейки это диапазон из одной клетки). Скрытые
        (накрытые чужим объединением) координаты внутри диапазона
        пропускаются -- у них нет своего визуального представления."""
        r0, c0, r1, c1 = self._selection_rect()
        for r in range(r0, r1 + 1):
            for c in range(c0, c1 + 1):
                if self._is_cell_hidden(r, c):
                    continue
                self._align[r][c] = checked
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
        self._align.append([False] * cols)
        self._set_active_cell(len(self._rows) - 1, 0)

    def _add_column(self):
        for row in self._rows:
            row.append([])
        for align_row in self._align:
            align_row.append(False)
        self._set_active_cell(self._active_r, len(self._rows[0]) - 1)

    def _adjust_merges_for_row_removal(self, removed_r: int):
        """Объединение, у которого удаляемая строка строго выше верхнего
        левого угла, сдвигается на 1; объединение, чей диапазон ВКЛЮЧАЕТ
        удаляемую строку, просто теряет 1 из row_span; объединение целиком
        ниже не трогаем. Если после этого объединение схлопнулось до 1×1 --
        выбрасываем его, дальше это обычная ячейка. Индексы -- старые (до
        pop), копия adjustMergesForRowRemoval() мокапа."""
        kept = []
        for m in self._merges:
            bottom = m["r"] + m["row_span"] - 1
            if removed_r < m["r"]:
                m["r"] -= 1
            elif removed_r <= bottom:
                m["row_span"] -= 1
            if m["row_span"] >= 1 and m["col_span"] >= 1 and (m["row_span"] > 1 or m["col_span"] > 1):
                kept.append(m)
        self._merges = kept

    def _adjust_merges_for_column_removal(self, removed_c: int):
        kept = []
        for m in self._merges:
            right = m["c"] + m["col_span"] - 1
            if removed_c < m["c"]:
                m["c"] -= 1
            elif removed_c <= right:
                m["col_span"] -= 1
            if m["row_span"] >= 1 and m["col_span"] >= 1 and (m["row_span"] > 1 or m["col_span"] > 1):
                kept.append(m)
        self._merges = kept

    def _remove_active_row(self):
        if len(self._rows) <= 1:
            return
        self._adjust_merges_for_row_removal(self._active_r)
        self._rows.pop(self._active_r)
        self._align.pop(self._active_r)
        r = min(self._active_r, len(self._rows) - 1)
        self._set_active_cell(r, min(self._active_c, len(self._rows[0]) - 1))

    def _remove_active_column(self):
        if len(self._rows[0]) <= 1:
            return
        c = self._active_c
        self._adjust_merges_for_column_removal(c)
        for row in self._rows:
            row.pop(c)
        for align_row in self._align:
            align_row.pop(c)
        self._set_active_cell(self._active_r, min(c, len(self._rows[0]) - 1))

    # -- Отрисовка -- перестраивается целиком на КАЖДОЕ изменение, тот же
    # приём, что и у редактора формул/остального конструктора. -------------
    def _render_grid(self):
        self._clear_layout(self._grid_layout)
        r0, c0, r1, c1 = self._selection_rect()
        is_single_cell_selection = r0 == r1 and c0 == c1
        self._center_checkbox.blockSignals(True)
        self._center_checkbox.setChecked(bool(self._align[r0][c0]))
        self._center_checkbox.blockSignals(False)
        for r, row in enumerate(self._rows):
            for c, tokens in enumerate(row):
                if self._is_cell_hidden(r, c):
                    continue  # накрыта объединением слева/сверху -- своего QWidget нет, addWidget() с row_span/col_span у верхнего левого угла её перекрывает
                merge = self._get_merge_at(r, c)
                is_active = (r == self._active_r and c == self._active_c)
                is_selected = not is_single_cell_selection and r0 <= r <= r1 and c0 <= c <= c1
                cell = _make_flow_widget("tableEditorCell", margin=7, spacing=2, center=self._align[r][c])
                cell.setMinimumWidth(120)
                cell.setProperty("tableCellHeader", self._has_header and r == 0)
                cell.setProperty("tableCellActive", is_active)
                cell.setProperty("tableCellSelected", is_selected)
                cell.style().unpolish(cell)
                cell.style().polish(cell)
                # Клик по СВОБОДНОМУ месту ячейки (не по конкретному
                # токену -- те получают клик напрямую от Qt, см. докстринг
                # formula_editor_dialog.py насчёт того, почему тут не нужен
                # аналог DOM stopPropagation()) -- см. _on_cell_background_clicked().
                cell.mousePressEvent = lambda event, rr=r, cc=c: self._on_cell_background_clicked(event, rr, cc)
                self._render_cell_zone(cell, tokens, is_active)
                row_span = merge["row_span"] if merge else 1
                col_span = merge["col_span"] if merge else 1
                self._grid_layout.addWidget(cell, r, c, row_span, col_span)

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
        # setMinimumHeight -- НЕ setFixedHeight (как в formula_editor_dialog.py):
        # см. докстринг модуля насчёт того, почему объединённой (row_span>1)
        # ячейке нужно позволить растянуться на всю высоту составной строки
        # сетки, а не обрезать её собственным Fixed size policy по вертикали.
        widget.setMinimumHeight(max(min_height, needed))

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
                self._set_cursor_index(i if before else i + 1)

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
        self.align = [row[:] for row in self._align]
        self.accept()

    def _on_remove(self):
        self.removed = True
        self.accept()

"""Редактор формул -- «Создать формулу»/«Редактировать формулу» из ПКМ на
чипе плейсхолдера в реквизитах конструктора документов (см.
src/ui/main_window.py, _show_chip_context_menu()/_open_formula_editor()).

Портирован из JS-мокапа (docs/design/вводная_часть.html, formulaModal +
соседние function formula*()) -- та же модель курсора вставки (активная
область + позиция внутри неё, см. FormulaEditorDialog._set_cursor()), та
же настоящая визуальная дробь (числитель/черта/знаменатель, каждый со
своей вложенной последовательностью токенов), то же округление с
фиксированным числом знаков после запятой (см.
src/services/formula_engine.py).

Ключевое упрощение относительно DOM-мокапа: там клик по любому месту
формулы приходилось останавливать через event.stopPropagation(), чтобы не
всплыл до родительской области. Qt не эмулирует всплытие мыши между
виджетами так, как DOM -- клик достаётся напрямую тому виджету, что
физически лежит под курсором (дочернему токену, если курсор над ним,
иначе -- контейнеру области), поэтому эта развязка тут не нужна вовсе."""

import functools
from typing import Callable, Dict, List, Optional, Tuple

from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QColor, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QWidget, QLabel, QPushButton, QToolButton,
    QMenu, QSpinBox, QAbstractSpinBox, QFrame, QMessageBox, QSizePolicy, QScrollArea,
)

from . import icons
from .flow_layout import FlowLayout
from ..services.formula_engine import evaluate_formula, format_formula_result

_QSS = """
QDialog { background: #2c2c2e; }
QDialog QLabel { color: #c7c7cc; font-size: 12px; }
QLabel#formulaTitle { color: #e5e5e7; font-size: 13px; font-weight: 600; }
QLabel#formulaSubtitle { color: #8e8e93; font-size: 11.5px; }
QWidget#formulaCanvas { background: #1c1c1e; border: 0.5px solid #38383a; border-radius: 8px; }
QWidget#formulaCanvas[formulaZoneActive="true"] { border: 1.5px solid #0a84ff; }
QLabel#formulaHint { color: #5a5a5c; font-size: 11px; font-style: italic; }
QLabel[formulaToken="placeholder"] {
    background: rgba(10, 132, 255, 40); color: #5ab4ff;
    border: 1px solid rgba(10, 132, 255, 110); border-radius: 6px; padding: 3px 8px; font-size: 12.5px;
}
QLabel[formulaToken="number"] { color: #e5e5e7; font-size: 12.5px; padding: 2px 3px; }
QLabel[formulaToken="op"] { color: #8e8e93; font-size: 13px; font-weight: 600; padding: 0 3px; }
QFrame#formulaCaret { background: #0a84ff; }
QFrame#formulaFracBar { background: #c7c7cc; }
QWidget#formulaFracZone { border: 1px dashed #38383a; border-radius: 4px; }
QWidget#formulaFracZone[formulaZoneActive="true"] { border: 1.5px solid #0a84ff; background: rgba(10, 132, 255, 24); }
QSpinBox#formulaDecimalsInput {
    background: #1c1c1e; border: 0.5px solid #48484a; border-radius: 6px;
    padding: 3px 4px; font-size: 12px; color: #e5e5e7;
}
"""

_STEPPER_BTN_QSS = (
    "QToolButton{background:#2c2c2e; border:0.5px solid #48484a; border-radius:4px;} "
    "QToolButton:hover{background:#3a3a3c;} "
    "QToolButton:pressed{background:#48484a;}"
)

_OP_BTN_QSS = (
    "QPushButton{background:#242426; border:0.5px solid #38383a; color:#c7c7cc; "
    "font-size:12px; padding:5px 10px; border-radius:6px;} "
    "QPushButton:hover{background:#3a3a3c; color:#e5e5e7;}"
)


class _ClickableLabel(QLabel):
    """QLabel одного токена формулы -- клик определяет, в какую половину
    виджета попал курсор (левая -- курсор встаёт ПЕРЕД токеном, правая --
    ПОСЛЕ), см. FormulaEditorDialog._render_token()."""

    def __init__(self, text: str, on_click: Callable[[bool], None]):
        super().__init__(text)
        self._on_click = on_click
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, event):
        before = event.position().x() < self.width() / 2
        self._on_click(before)


class _ParenGlyph(QWidget):
    """Скобка "(" / ")", растянутая под высоту соседней дроби внутри той же
    пары -- обычный текстовый токен (font-size:13px, см. _QSS) остаётся
    маленьким независимо от того, что стоит рядом с ним внутри скобок, и
    визуально не "обнимает" высокую дробь, как в математической записи.
    Простое увеличение font-size тут не подходит: глиф "(" большинства
    шрифтов при сильном масштабировании выглядит непропорционально
    толстым/разорванным -- вместо этого кривая рисуется явно через
    QPainterPath на нужную высоту (см. FormulaEditorDialog._build_zone_widgets()
    насчёт того, как вычисляется целевая высота для пары скобок)."""

    _COLOR = QColor("#8e8e93")

    def __init__(self, kind: str, height: int, on_click: Callable[[bool], None]):
        super().__init__()
        self._kind = kind
        self._h = max(height, 16)
        self._w = max(9, round(self._h * 0.3))
        self._on_click = on_click
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def sizeHint(self) -> QSize:
        return QSize(self._w, self._h)

    def mousePressEvent(self, event):
        before = event.position().x() < self.width() / 2
        self._on_click(before)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(self._COLOR)
        pen.setWidthF(1.6)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)

        w, h, pad = float(self._w), float(self._h), 2.0
        path = QPainterPath()
        if self._kind == "(":
            path.moveTo(w * 0.8, pad)
            path.cubicTo(w * 0.05, h * 0.22, w * 0.05, h * 0.78, w * 0.8, h - pad)
        else:
            path.moveTo(w * 0.2, pad)
            path.cubicTo(w * 0.95, h * 0.22, w * 0.95, h * 0.78, w * 0.2, h - pad)
        painter.drawPath(path)


class _SpinStepper(QWidget):
    """Свои кнопки вверх/вниз для QSpinBox округления -- нативные стрелки
    QSpinBox (ButtonSymbols.UpDownArrows) оказались настолько крошечными
    (особенно на macOS), что в них трудно попасть курсором, а увеличение
    их размера чисто через QSS (::up-button/::down-button width/height)
    эмпирически не сработало: сама область кнопки становится шире, но
    стрелка-индикатор внутри не рисуется вовсе (проверено headless-
    скриншотом) -- похоже, стиль без явного image: не берётся рисовать
    сам глиф под нестандартный размер. Тут вместо этого -- те же
    SVG-иконки (icons.py), что и везде в конструкторе, произвольного
    размера и гарантированно видимые."""

    def __init__(self, spin_box: QSpinBox, size: int = 22):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        up = QToolButton()
        up.setIcon(icons.icon("chevron-up", "#c7c7cc", 11))
        up.setFixedSize(size, size)
        up.setAutoRepeat(True)
        up.setStyleSheet(_STEPPER_BTN_QSS)
        up.clicked.connect(spin_box.stepUp)

        down = QToolButton()
        down.setIcon(icons.icon("chevron-down", "#c7c7cc", 11))
        down.setFixedSize(size, size)
        down.setAutoRepeat(True)
        down.setStyleSheet(_STEPPER_BTN_QSS)
        down.clicked.connect(spin_box.stepDown)

        layout.addWidget(up)
        layout.addWidget(down)


class _CaretFrame(QFrame):
    """Мигающая (визуально -- статичная, см. докстринг модуля) вертикальная
    черта курсора вставки. ОБЯЗАТЕЛЬНО переопределяет sizeHint() -- голый
    QFrame его не переопределяет вовсе (в отличие от QLabel, чей sizeHint
    считается по тексту/шрифту), а FlowLayout (см. flow_layout.py) кладёт
    виджеты РОВНО по item.sizeHint(), не сверяясь с setFixedWidth()/
    setMinimumHeight() -- без этого переопределения QFrame.sizeHint()
    возвращает что-то произвольно большое, и черта раздувается в огромный
    синий прямоугольник, обрезающий соседние токены."""

    def sizeHint(self) -> QSize:
        return QSize(2, 22)


def _clone_tokens(tokens: List[Dict]) -> List[Dict]:
    cloned = []
    for token in tokens:
        if token.get("type") == "fraction":
            cloned.append({
                "type": "fraction",
                "num": _clone_tokens(token.get("num", [])),
                "den": _clone_tokens(token.get("den", [])),
            })
        else:
            cloned.append(dict(token))
    return cloned


class FormulaEditorDialog(QDialog):
    """См. докстринг модуля. Результат читается вызывающей стороной ПОСЛЕ
    exec(), и только если он вернул QDialog.DialogCode.Accepted:
    `removed=True` -- формулу нужно удалить у поля, иначе `tokens`/
    `decimals` -- новое (или обновлённое) значение формулы."""

    def __init__(
        self,
        field_id: str,
        field_label: str,
        all_fields: Dict[str, str],
        all_formulas: Dict[str, Dict],
        existing_formula: Optional[Dict],
        resolve_placeholder: Callable[[str], Optional[float]],
        parent=None,
    ):
        super().__init__(parent)
        self._field_id = field_id
        # Само поле, для которого создаётся формула, исключено из списка
        # вставки -- ссылка на само себя всегда была бы циклом (см.
        # evaluate_formula()/visiting в formula_engine.py).
        self._all_fields = {fid: label for fid, label in all_fields.items() if fid != field_id}
        self._all_formulas = dict(all_formulas)
        self._resolve_placeholder = resolve_placeholder

        # Черновик -- редактируем копию, не сам сохранённый объект, чтобы
        # «Отмена» не оставляла частично применённые правки.
        self._tokens: List[Dict] = _clone_tokens(existing_formula["tokens"]) if existing_formula else []
        self._active_zone: List[Dict] = self._tokens
        self._cursor_index = len(self._tokens)
        self._decimals = existing_formula["decimals"] if existing_formula else 2

        self.removed = False
        self.tokens: List[Dict] = []
        self.decimals = self._decimals

        self.setWindowTitle("Редактор формул")
        self.setStyleSheet(_QSS)
        # StrongFocus -- иначе self.setFocus() в _render_canvas() ниже
        # молча не сработает (у QWidget/QDialog по умолчанию
        # Qt.FocusPolicy.NoFocus): без фокуса на диалоге набор цифр с
        # клавиатуры (см. keyPressEvent()) уходил бы не туда -- например,
        # оставался бы на QSpinBox округления, если тот получил фокус
        # раньше, а клик по канве фокус на себя не переключает (у меток
        # токенов формулы фокус-политика тоже NoFocus).
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._build_ui(field_label, existing_formula is not None)
        # Порог для решения "нужна ли этой паре скобок растянутая
        # отрисовка" (см. _build_zone_widgets()) -- высота ОБЫЧНОГО
        # текстового знака-скобки при текущих _QSS. Меряется один раз тут,
        # а не хардкодится числом, чтобы не разъезжаться с _QSS при правке
        # стилей.
        self._plain_op_height = self._measure_plain_op_height()
        self._render_canvas()

    # -- Построение диалога -------------------------------------------------
    def _build_ui(self, field_label: str, has_existing: bool):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(4)
        self.setMinimumWidth(430)

        title = QLabel("Редактор формул")
        title.setObjectName("formulaTitle")
        layout.addWidget(title)

        subtitle = QLabel(f"Поле «{field_label}» — значение будет вычисляться автоматически")
        subtitle.setObjectName("formulaSubtitle")
        subtitle.setWordWrap(True)
        layout.addSpacing(2)
        layout.addWidget(subtitle)
        layout.addSpacing(8)

        self._canvas = self._make_flow_widget("formulaCanvas", margin=10, spacing=6)
        self._canvas.setMinimumHeight(44)
        # Канва в QScrollArea: длинная формула (много переносов, дроби с
        # длинными плейсхолдерами) иначе растёт вниз без предела, а окно
        # ограничено размером экрана -- канва налезала на «Результат» и
        # кнопки. Высота области = высота канвы, но не больше _CANVAS_MAX_HEIGHT;
        # сверх этого -- вертикальная прокрутка (см. _fit_canvas_scroll()).
        self._canvas_scroll = QScrollArea()
        self._canvas_scroll.setObjectName("formulaCanvasScroll")
        self._canvas_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._canvas_scroll.setWidgetResizable(True)
        self._canvas_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._canvas_scroll.setStyleSheet("QScrollArea#formulaCanvasScroll { background: transparent; }")
        self._canvas_scroll.setWidget(self._canvas)
        layout.addWidget(self._canvas_scroll)

        result_row = QHBoxLayout()
        result_row.addWidget(QLabel("Результат:"))
        self._result_label = QLabel()
        self._result_label.setStyleSheet("color:#e5e5e7; font-weight:500;")
        result_row.addWidget(self._result_label)
        result_row.addStretch(1)
        layout.addLayout(result_row)

        decimals_row = QHBoxLayout()
        decimals_row.addWidget(QLabel("Округление: до"))
        self._decimals_input = QSpinBox()
        self._decimals_input.setObjectName("formulaDecimalsInput")
        self._decimals_input.setRange(0, 6)
        self._decimals_input.setValue(self._decimals)
        self._decimals_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # Свои кнопки вместо нативных -- см. докстринг _SpinStepper().
        self._decimals_input.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self._decimals_input.valueChanged.connect(self._on_decimals_changed)
        decimals_row.addWidget(self._decimals_input)
        decimals_row.addWidget(_SpinStepper(self._decimals_input))
        decimals_row.addWidget(QLabel("знаков после запятой"))
        decimals_row.addStretch(1)
        layout.addLayout(decimals_row)
        layout.addSpacing(6)

        insert_btn = QToolButton()
        insert_btn.setText("Вставить плейсхолдер")
        insert_btn.setIcon(icons.icon("tag", "#c7c7cc", 13))
        insert_btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        insert_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        insert_btn.setMenu(self._build_placeholder_menu())
        insert_row = QHBoxLayout()
        insert_row.addWidget(insert_btn)
        insert_row.addStretch(1)
        layout.addLayout(insert_row)
        layout.addSpacing(6)

        number_row = QHBoxLayout()
        for symbol in ("+", "−", "×", "÷", "(", ")"):
            number_row.addWidget(self._op_button(symbol, functools.partial(self._insert_op, symbol)))
        number_row.addWidget(self._op_button("Дробь", self._insert_fraction))
        number_row.addStretch(1)
        layout.addLayout(number_row)
        layout.addSpacing(6)

        edit_row = QHBoxLayout()
        edit_row.addWidget(self._op_button("⌫ Удалить перед курсором", self._remove_before_cursor))
        edit_row.addWidget(self._op_button("Очистить всё", self._clear_all))
        edit_row.addStretch(1)
        layout.addLayout(edit_row)
        layout.addSpacing(10)

        bottom_row = QHBoxLayout()
        if has_existing:
            remove_btn = QPushButton("Убрать формулу")
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

    @staticmethod
    def _make_flow_widget(object_name: str, margin: int, spacing: int) -> QWidget:
        """QWidget с FlowLayout, готовый переноситься на несколько строк
        (canvas формулы, числитель/знаменатель дроби). setHeightForWidth(True)
        на sizePolicy -- ОБЯЗАТЕЛЕН и легко забывается: без него содержащий
        QVBoxLayout не запрашивает у FlowLayout.heightForWidth() реальную
        высоту под перенесённые строки, виджет остаётся на минимальной
        высоте, а перенесённые токены/дробь просто вылезают за его границы
        и обрезаются/накладываются на соседей, вместо того чтобы раздвинуть
        поле вниз (см. FlowLayout.hasHeightForWidth()/heightForWidth())."""
        container = QWidget()
        container.setObjectName(object_name)
        FlowLayout(container, margin=margin, spacing=spacing)
        policy = container.sizePolicy()
        policy.setHeightForWidth(True)
        container.setSizePolicy(policy)
        return container

    def _build_placeholder_menu(self) -> QMenu:
        menu = QMenu(self)
        if not self._all_fields:
            action = menu.addAction("Нет доступных плейсхолдеров")
            action.setEnabled(False)
            return menu
        for field_id, label in self._all_fields.items():
            text = label + (" (ƒ)" if field_id in self._all_formulas else "")
            action = menu.addAction(text)
            action.triggered.connect(lambda checked=False, fid=field_id: self._insert_placeholder(fid))
        return menu

    # -- Модель курсора: activeZone -- ссылка на конкретный список токенов
    # (верхний уровень формулы либо num/den какой-то дроби внутри неё),
    # cursorIndex -- позиция вставки внутри него (0..len(zone)). -----------
    def _set_cursor(self, zone: List[Dict], index: int):
        self._active_zone = zone
        self._cursor_index = index
        self._render_canvas()

    # -- Вставка/удаление -- всегда РОВНО в позицию курсора (list.insert),
    # не в конец -- курсор сдвигается за вставленным элементом, поэтому
    # серия нажатий подряд печатает последовательность в том порядке, в
    # котором на кнопки нажали, независимо от того, где стоял курсор. -----
    def _insert_token(self, token: Dict):
        self._active_zone.insert(self._cursor_index, token)
        self._cursor_index += 1
        self._render_canvas()

    def _insert_placeholder(self, field_id: str):
        self._insert_token({"type": "placeholder", "id": field_id})

    def _insert_op(self, op: str):
        self._insert_token({"type": "op", "value": op})

    def _insert_fraction(self):
        fraction = {"type": "fraction", "num": [], "den": []}
        self._insert_token(fraction)
        # Курсор сразу переходит в числитель новой дроби, как в редакторе
        # формул Word -- отдельно от _insert_token() выше: тут меняется и
        # область, и позиция курсора, а не просто сдвиг в той же области.
        self._active_zone = fraction["num"]
        self._cursor_index = 0
        self._render_canvas()

    def _type_number_char(self, char: str):
        """Цифра/запятая, набранная прямо на канве (см. keyPressEvent()) --
        если непосредственно ПЕРЕД курсором уже стоит число, символ
        ДОПИСЫВАЕТСЯ к нему (как в обычном текстовом поле, курсор не
        сдвигается на отдельный новый токен под каждое нажатие), иначе
        начинается новое число -- кроме случая, когда первым символом
        оказалась сама запятая/точка: числа без целой части не
        поддерживаются."""
        zone = self._active_zone
        prev = zone[self._cursor_index - 1] if self._cursor_index > 0 else None
        is_separator = char in (",", ".")
        if prev is not None and prev.get("type") == "number":
            if is_separator and "," in prev["value"]:
                return
            prev["value"] += "," if is_separator else char
            self._render_canvas()
            return
        if is_separator:
            return
        self._insert_token({"type": "number", "value": char})

    def keyPressEvent(self, event):
        text = event.text()
        if text.isdigit() or text in (",", "."):
            self._type_number_char(text)
            return
        if event.key() == Qt.Key.Key_Backspace:
            self._remove_before_cursor()
            return
        super().keyPressEvent(event)

    def _remove_before_cursor(self):
        """Backspace -- удаляет элемент СЛЕВА от курсора (а не последний
        элемент активной области как таковой) и ставит курсор на его
        место -- симметрично тому, как ⌫ работает в любом текстовом поле."""
        if self._cursor_index <= 0:
            return
        self._active_zone.pop(self._cursor_index - 1)
        self._cursor_index -= 1
        self._render_canvas()

    def _clear_all(self):
        self._tokens.clear()
        self._active_zone = self._tokens
        self._cursor_index = 0
        self._render_canvas()

    def _on_decimals_changed(self, value: int):
        self._decimals = value
        self._update_result()

    # -- Отрисовка -- рекурсивная: у дроби num/den отрисовываются той же
    # _render_zone(), просто во вложенный контейнер. Перестраивается
    # целиком на КАЖДОЕ изменение (тот же приём, что и остальной
    # конструктор документов, см. _render_slot_fields() в main_window.py)
    # -- формула никогда не бывает настолько большой, чтобы это было
    # заметно по производительности. ---------------------------------------
    def _render_canvas(self):
        self._clear_layout(self._canvas.layout())
        self._render_zone(self._canvas, self._tokens, is_top_level=True)
        self._update_result()

        # sizePolicy().setHeightForWidth(True) (см. _make_flow_widget())
        # формально включает height-for-width, но эмпирически проверено:
        # QVBoxLayout всё равно не запрашивает через него реальную высоту
        # у вложенного FlowLayout при изменении содержимого ПОСЛЕ первого
        # show() -- виджет остаётся на прежней (обычно минимальной) высоте,
        # хотя сам FlowLayout.heightForWidth() при прямом вызове совершенно
        # верно возвращает нужное большее число (проверено headless-скриптом
        # отдельно). Поэтому высота выставляется вручную, а не через
        # автоматическое распространение по дереву лэйаутов.
        #
        # Порядок: сначала activate() -- закрепляет по всему дереву ШИРИНЫ
        # (они не зависят от высоты и потому уже корректны), затем читаем
        # heightForWidth() СНИЗУ ВВЕРХ -- сперва num/den зоны дробей (их
        # высота ещё не влияет ни на что снаружи), последней -- сама канва
        # (её высота теперь учитывает уже выставленные высоты дробей внутри
        # неё, т.к. QVBoxLayout дроби пересчитывает totalSizeHint по своим,
        # теперь верным, детям).
        #
        # Один проход недостаточен: ширина зоны дроби известна только после
        # activate(), а её высота (setFixedHeight) меняет размер обёртки
        # дроби, то есть высоту строки канвы и, из-за переноса, иногда и
        # раскладку по ширине. Поэтому проход повторяется, пока высоты не
        # перестанут меняться (на практике -- 2-3 итерации).
        for _ in range(5):
            self.layout().activate()
            before = [w.height() for w in self._canvas.findChildren(QWidget, "formulaFracZone")]
            before.append(self._canvas.height())
            # Зоны без дробей внутри (вложенные дроби -- глубже) считаются
            # раньше канвы: findChildren() отдаёт родителей раньше детей,
            # поэтому идём в обратном порядке -- снизу вверх.
            for zone in reversed(self._canvas.findChildren(QWidget, "formulaFracZone")):
                self._apply_flow_height(zone, min_height=24)
            self._apply_flow_height(self._canvas, min_height=44)
            self._fit_canvas_scroll()
            self.layout().activate()
            after = [w.height() for w in self._canvas.findChildren(QWidget, "formulaFracZone")]
            after.append(self._canvas.height())
            if before == after:
                break

        # QDialog не пересчитывает своё окно само по себе при изменении
        # содержимого ПОСЛЕ показа (это происходит только один раз, при
        # первом exec()/show()) -- без явного adjustSize() выросшая канва
        # осталась бы обрезанной внутри окна старого размера, даже если
        # сама канва теперь размечена правильно. invalidate() -- обязателен:
        # кэш размеров корневого layout остаётся от ДО setFixedHeight()
        # канвы, и без сброса окно подгоняется под устаревшую (меньшую)
        # высоту -- канва налезает на строку «Результат» и нижние кнопки.
        #
        # Не adjustSize(): он урезает окно до доли высоты экрана, и результат
        # оказывался ниже sizeHint() -- нижние строки налезали друг на друга.
        # Высота канвы ограничена _CANVAS_MAX_HEIGHT, так что окно и без
        # этого не вырастает сверх разумного.
        self.layout().invalidate()
        self.layout().activate()
        hint = self.sizeHint()
        self.resize(max(self.width(), hint.width()), hint.height())

        # Возвращает клавиатурный фокус диалогу после ЛЮБОГО изменения
        # (клик по канве, вставка через кнопку) -- чтобы набор цифр (см.
        # keyPressEvent()) продолжал попадать в формулу, а не оставался на
        # только что нажатой кнопке/поле округления.
        self.setFocus()

    # Предельная высота видимой части канвы, px; выше -- прокрутка.
    _CANVAS_MAX_HEIGHT = 260

    def _fit_canvas_scroll(self):
        """Высота области прокрутки под текущую высоту канвы (+2 px на
        границу канвы), но не выше _CANVAS_MAX_HEIGHT."""
        self._canvas_scroll.setFixedHeight(min(self._canvas.height(), self._CANVAS_MAX_HEIGHT))

    def _apply_flow_height(self, widget: QWidget, min_height: int):
        """Явно выставляет высоту widget (с FlowLayout) под его текущую
        ширину -- см. докстринг _render_canvas() насчёт того, почему это
        нельзя доверить автоматическому height-for-width. До первого show()
        (самый первый рендер в __init__()) у widget ещё нет реальной
        ширины -- берём ширину диалога как разумную оценку того же
        порядка величины."""
        width = widget.width()
        if width <= 1:
            width = max(self.minimumWidth() - 40, 200)
        needed = widget.layout().heightForWidth(width)
        widget.setFixedHeight(max(min_height, needed))

    @staticmethod
    def _clear_layout(layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                # hide() -- обязателен, не только deleteLater(): реальное
                # удаление откладывается до следующего прохода цикла
                # событий, а до тех пор виджет остаётся видимым, как был,
                # и просвечивает из-под свежеотрисованных токенов той же
                # зоны (воспроизведено -- старый текст-подсказка "нажмите
                # на кнопку ниже" оставался виден под новыми токенами).
                widget.hide()
                widget.deleteLater()

    def _render_zone(self, container: QWidget, zone: List[Dict], is_top_level: bool = False):
        layout = container.layout()
        is_active = zone is self._active_zone
        container.setProperty("formulaZoneActive", is_active)
        container.style().unpolish(container)
        container.style().polish(container)
        # Клик по СВОБОДНОМУ месту области (не по конкретному токену -- те
        # получают клик напрямую от Qt, минуя этот контейнер, см. докстринг
        # модуля) -- курсор становится в конец этой области.
        container.mousePressEvent = lambda event, z=zone: self._set_cursor(z, len(z))

        cursor_index = self._cursor_index if is_active else -1

        if cursor_index == 0:
            layout.addWidget(self._make_caret())
        if not zone:
            hint = QLabel("нажмите на кнопку ниже, чтобы добавить" if is_top_level else "пусто")
            hint.setObjectName("formulaHint")
            layout.addWidget(hint)
        for index, widget in enumerate(self._build_zone_widgets(container, zone)):
            layout.addWidget(widget)
            if cursor_index == index + 1:
                layout.addWidget(self._make_caret())

    def _build_zone_widgets(self, container: QWidget, zone: List[Dict]) -> List[QWidget]:
        """Строит по одному виджету на каждый токен зоны, в порядке зоны --
        отдельно от простого маппинга _render_token(): паре скобок,
        обрамляющей что-то выше обычной строки (в первую очередь -- дробь),
        здесь подбирается растянутая под эту высоту отрисовка
        (_ParenGlyph), а не всегда плоский текстовый "(" / ")". Требует
        ДВУХ проходов -- высоту соседей внутри пары скобок можно узнать
        только после того, как они сами уже построены."""
        pairs = self._match_bracket_pairs(zone)
        bracket_indices = {i for pair in pairs for i in pair}

        widgets: List[Optional[QWidget]] = [None] * len(zone)
        for index, token in enumerate(zone):
            if index in bracket_indices:
                continue
            widgets[index] = self._prepare_zone_widget(container, self._render_token(token, zone, index))

        for open_i, close_i in pairs:
            inner_heights = [
                widgets[i].sizeHint().height()
                for i in range(open_i + 1, close_i)
                if widgets[i] is not None
            ]
            target_h = max(inner_heights) if inner_heights else 0
            for i in (open_i, close_i):
                if target_h > self._plain_op_height + 4:
                    widget = self._render_bracket_glyph(zone[i]["value"], target_h, zone, i)
                else:
                    widget = self._render_token(zone[i], zone, i)
                widgets[i] = self._prepare_zone_widget(container, widget)

        return widgets  # type: ignore[return-value]

    def _prepare_zone_widget(self, container: QWidget, widget: QWidget) -> QWidget:
        """Родитель выставляется СРАЗУ (а не только позже, при
        layout.addWidget()) -- иначе у виджета ещё нет цепочки предков до
        диалога, стиль (_QSS, откуда берётся font-size токена) к нему не
        применяется, и sizeHint() из _build_zone_widgets() выше меряет по
        шрифту приложения по умолчанию, а не по тому, что реально будет
        нарисовано. _force_visible() -- та же причина, что и явный show()
        в FlowLayout.addItem() (см. её докстринг): виджет, построенный уже
        после первого показа диалога, сам по себе не становится видимым, и
        БЕЗ этого sizeHint() (в т.ч. у обёртки дроби, чья высота собирается
        из QVBoxLayout'а её числителя/черты/знаменателя) считался бы по
        пустому/пока-не-показанному поддереву."""
        widget.setParent(container)
        self._force_visible(widget)
        widget.ensurePolished()
        return widget

    @staticmethod
    def _force_visible(widget: QWidget):
        widget.show()
        for child in widget.findChildren(QWidget):
            child.show()

    def _measure_plain_op_height(self) -> int:
        probe = QLabel("(")
        probe.setProperty("formulaToken", "op")
        probe.setParent(self._canvas)
        probe.ensurePolished()
        height = probe.sizeHint().height()
        probe.setParent(None)
        probe.deleteLater()
        return height

    @staticmethod
    def _match_bracket_pairs(zone: List[Dict]) -> List[Tuple[int, int]]:
        """Пары индексов "(" -- ")" внутри ОДНОЙ зоны (в числитель/знаменатель
        дроби скобки родительской зоны не заглядывают -- у вложенной зоны
        свои собственные пары, см. рекурсивный вызов _render_zone() из
        _render_fraction()). Порядок результата -- порядок закрытия
        скобок, т.е. САМИ ВНУТРЕННИЕ пары идут раньше внешних: то, что
        нужно для _build_zone_widgets() выше, где высота внешней пары
        должна учитывать уже готовую (при необходимости -- растянутую)
        отрисовку внутренней. Незакрытая/лишняя ")" без пары -- не пара,
        останется обычным текстовым знаком."""
        pairs: List[Tuple[int, int]] = []
        stack: List[int] = []
        for index, token in enumerate(zone):
            if token.get("type") != "op":
                continue
            value = token.get("value")
            if value == "(":
                stack.append(index)
            elif value == ")" and stack:
                pairs.append((stack.pop(), index))
        return pairs

    def _render_bracket_glyph(self, kind: str, height: int, zone: List[Dict], index: int) -> QWidget:
        def on_click(before: bool, z=zone, i=index):
            self._set_cursor(z, i if before else i + 1)

        return _ParenGlyph(kind, height, on_click)

    @staticmethod
    def _make_caret() -> QFrame:
        caret = _CaretFrame()
        caret.setObjectName("formulaCaret")
        return caret

    def _render_token(self, token: Dict, zone: List[Dict], index: int) -> QWidget:
        ttype = token.get("type")
        if ttype == "fraction":
            return self._render_fraction(token, zone, index)

        text = self._all_fields.get(token["id"], token["id"]) if ttype == "placeholder" else token.get("value", "")

        def on_click(before: bool, z=zone, i=index):
            self._set_cursor(z, i if before else i + 1)

        label = _ClickableLabel(text, on_click)
        label.setProperty("formulaToken", ttype)
        return label

    def _render_fraction(self, token: Dict, parent_zone: List[Dict], parent_index: int) -> QWidget:
        wrapper = QWidget()
        outer = QVBoxLayout(wrapper)
        outer.setContentsMargins(2, 0, 2, 0)
        outer.setSpacing(2)

        num_zone = self._make_flow_widget("formulaFracZone", margin=3, spacing=4)
        bar = QFrame()
        bar.setObjectName("formulaFracBar")
        bar.setFixedHeight(1)
        den_zone = self._make_flow_widget("formulaFracZone", margin=3, spacing=4)

        outer.addWidget(num_zone)
        outer.addWidget(bar)
        outer.addWidget(den_zone)

        self._render_zone(num_zone, token["num"])
        self._render_zone(den_zone, token["den"])

        # Клик по числителю/знаменателю сам решает свою позицию курсора
        # (см. _render_zone() выше). Клик прямо по обёртке дроби (её полю
        # вокруг num/bar/den, чаще всего -- по самой черте) считается
        # кликом по ДРОБИ ЦЕЛИКОМ как по обычному токену родительской
        # области -- до неё или после, левая/правая половина обёртки.
        def on_wrapper_click(event, z=parent_zone, i=parent_index, w=wrapper):
            before = event.position().x() < w.width() / 2
            self._set_cursor(z, i if before else i + 1)

        wrapper.mousePressEvent = on_wrapper_click
        return wrapper

    def _update_result(self):
        value = (
            evaluate_formula(self._tokens, self._resolve_placeholder, self._all_formulas)
            if self._tokens else None
        )
        self._result_label.setText(format_formula_result(value, self._decimals))

    # -- Завершение ---------------------------------------------------------
    def _on_save(self):
        if not self._tokens:
            QMessageBox.warning(
                self, "Формула пустая",
                "Добавьте хотя бы один элемент (плейсхолдер, число или дробь).",
            )
            return
        self.removed = False
        self.tokens = _clone_tokens(self._tokens)
        self.decimals = self._decimals
        self.accept()

    def _on_remove(self):
        self.removed = True
        self.accept()

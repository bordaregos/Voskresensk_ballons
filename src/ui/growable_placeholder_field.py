"""GrowablePlaceholderField -- текстовое поле реквизитов конструктора
документов, растущее по высоте вместе с введённым текстом (перенос строк,
а не горизонтальный скролл одной строки, как было раньше -- см. историю
_render_slot_fields() в src/ui/main_window.py) и сворачивающееся до одной
строки, когда не нужно. Перенос мокапа docs/design/вводная_часть.html
(autoGrowField()/.expanded/.field-expand-btn) на реальный QPlainTextEdit.

Раскрывается двумя независимыми способами, как и в мокапе:
- фокус (печатаешь -- видно, что печатаешь) -- временный, сворачивается по
  потере фокуса, если не закреплено (см. ниже);
- клик по шеврону в правом верхнем углу поля -- ручной, держит поле
  раскрытым для ЧТЕНИЯ независимо от фокуса, не сворачивается по клику
  мимо. Шеврон показывается, только если текст реально не помещается в
  одну строку -- сворачивать/держать раскрытым однострочное значение
  незачем.
"""

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtWidgets import QPlainTextEdit, QToolButton

from . import icons


class GrowablePlaceholderField(QPlainTextEdit):
    # Совпадает с QSS "padding: 6px 8px" у
    # QGroupBox#fieldsPanel/#introFieldsPanel QPlainTextEdit (см.
    # CONSTRUCTOR_QSS в main_window.py) -- держим эти два места в
    # соответствии, если правится один, поправить и другой. Высота меряется
    # через fontMetrics()/document(), а не через рамку/margins виджета --
    # так надёжнее: не зависит от того, что именно (QSS padding, border)
    # в реальности рисует Qt поверх содержимого.
    _VERTICAL_PADDING = 12
    _FRAME_ALLOWANCE = 4
    _CHEVRON_SIZE = 12
    _CHEVRON_MARGIN = 3

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        # Как и в обычной однострочной форме -- Tab переходит к следующему
        # полю, а не вставляет символ табуляции (умолчание QPlainTextEdit).
        self.setTabChangesFocus(True)

        # Закреплено ли поле раскрытым через шеврон -- в отличие от
        # раскрытия по фокусу, это состояние переживает потерю фокуса.
        self._pinned_expanded = False

        self._chevron_btn = QToolButton(self)
        self._chevron_btn.setAutoRaise(True)
        self._chevron_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._chevron_btn.setToolTip("Свернуть/развернуть поле")
        self._chevron_btn.setFixedSize(self._CHEVRON_SIZE + 6, self._CHEVRON_SIZE + 6)
        self._chevron_btn.setIconSize(QSize(self._CHEVRON_SIZE, self._CHEVRON_SIZE))
        self._chevron_btn.setStyleSheet(
            "QToolButton{background:transparent;border:none;border-radius:4px;}"
            "QToolButton:hover{background:#3a3a3c;}"
        )
        self._chevron_btn.hide()
        self._chevron_btn.clicked.connect(self._toggle_pinned)

        self.textChanged.connect(self._update_height)
        self._update_height()

    def _single_line_height(self) -> int:
        return self.fontMetrics().lineSpacing() + self._VERTICAL_PADDING + self._FRAME_ALLOWANCE

    def _wrapped_line_count(self) -> int:
        """Число визуальных строк с учётом переноса. document().size() тут
        НЕ годится (проверено эмпирически) -- QPlainTextEdit использует
        QPlainTextDocumentLayout, а не обычный QTextDocumentLayout (это и
        есть источник его эффективности на больших документах -- он не
        лэйаутит весь текст целиком), и documentSize().height() у него
        возвращает число строк, а НЕ пиксели (в отличие от QTextEdit) --
        реальную высоту нужно считать самим: количество строк на блок
        (block.layout().lineCount(), уже с учётом переноса) на количество
        блоков (абзацев, разделённых \\n)."""
        doc = self.document()
        doc.setTextWidth(max(self.viewport().width(), 1))
        total = 0
        block = doc.begin()
        while block.isValid():
            layout = block.layout()
            total += max(1, layout.lineCount() if layout else 1)
            block = block.next()
        return max(total, 1)

    def _content_height(self) -> int:
        return (
            self._wrapped_line_count() * self.fontMetrics().lineSpacing()
            + self._VERTICAL_PADDING + self._FRAME_ALLOWANCE
        )

    def _is_multiline(self) -> bool:
        return self._content_height() > self._single_line_height() + 2

    def _update_height(self):
        multiline = self._is_multiline()
        self._chevron_btn.setVisible(multiline)
        if not multiline:
            # Схлопнувшееся обратно до одной строки поле не должно
            # оставаться "залипшим" закреплённым -- шеврон, которым можно
            # было бы это отменить, всё равно уже не виден.
            self._pinned_expanded = False
        else:
            self._chevron_btn.setIcon(
                icons.icon(
                    "chevron-down" if self._pinned_expanded else "chevron-right", "#8e8e93", self._CHEVRON_SIZE,
                )
            )

        expanded = multiline and (self._pinned_expanded or self.hasFocus())
        self.setFixedHeight(self._content_height() if expanded else self._single_line_height())
        self._reposition_chevron()

    def _reposition_chevron(self):
        btn = self._chevron_btn
        btn.move(max(0, self.width() - btn.width() - self._CHEVRON_MARGIN), self._CHEVRON_MARGIN)

    def _toggle_pinned(self):
        self._pinned_expanded = not self._pinned_expanded
        self._update_height()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._reposition_chevron()

    def focusInEvent(self, event):
        super().focusInEvent(event)
        self._update_height()

    def focusOutEvent(self, event):
        super().focusOutEvent(event)
        self._update_height()

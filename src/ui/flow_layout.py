"""FlowLayout -- дочерние виджеты слева направо, перенос на новую строку по
ширине контейнера. Стандартный рецепт из официальных примеров Qt (у
QLayout нет этого "из коробки", в отличие от CSS flex-wrap) -- нужен
редактору формул конструктора документов (formula_editor_dialog.py) для
строки токенов формулы, которая должна переноситься на несколько строк,
если не помещается в ширину диалога."""

from typing import List, Tuple

from PyQt6.QtCore import QPoint, QRect, QSize, Qt
from PyQt6.QtWidgets import QLayout


class FlowLayout(QLayout):
    def __init__(self, parent=None, margin: int = 0, spacing: int = 6):
        super().__init__(parent)
        if parent is not None:
            self.setContentsMargins(margin, margin, margin, margin)
        self.setSpacing(spacing)
        self._items = []

    def addItem(self, item):
        # Виджет, добавленный в этот layout уже ПОСЛЕ того, как его окно
        # показано (типичный случай при живой перестройке содержимого --
        # см. FormulaEditorDialog._render_canvas()), Qt сам не показывает:
        # show()-каскад из QWidget.show() срабатывает только один раз, в
        # момент первого показа самого верхнего окна, и не подхватывает
        # виджеты, добавленные в дерево позже. Без явного show() здесь
        # QWidgetItem считает такой виджет "пустым" (аналог CSS
        # display:none) и всегда возвращает (0, 0) из sizeHint() -- перенос
        # строк тогда никогда не срабатывает, а heightForWidth() всегда
        # даёт минимальную высоту, даже когда токенов много (воспроизведено
        # и подтверждено трассировкой при отладке формул конструктора
        # документов -- см. src/ui/formula_editor_dialog.py).
        #
        # Порядок ниже критичен. widget.show() внутри уже видимого
        # родителя, управляемого layout'ом, сам синхронно запускает
        # релэйаут родителя (до возврата из show()) -- если добавить item в
        # self._items ПОСЛЕ show(), этот синхронный релэйаут отрабатывает
        # по СТАРОМУ списку (без ещё не добавленного item), после чего Qt
        # считает layout снова «чистым» и явный activate() из
        # _render_canvas() уже ничего не пересчитывает: item молча
        # остаётся с геометрией по умолчанию (0, 0, 640, 480) -- на канве
        # формулы это выглядело как последний добавленный токен (обычно
        # курсор), раздувшийся в сплошной синий прямоугольник на всю канву
        # (воспроизведено и подтверждено трассировкой setGeometry). Поэтому
        # item сперва попадает в self._items, и только потом -- show();
        # invalidate() в конце -- подстраховка на случай, если сам show()
        # релэйаут не спровоцирует.
        self._items.append(item)
        widget = item.widget()
        if widget is not None:
            widget.show()
        self.invalidate()

    def count(self) -> int:
        return len(self._items)

    def itemAt(self, index):
        return self._items[index] if 0 <= index < len(self._items) else None

    def takeAt(self, index):
        return self._items.pop(index) if 0 <= index < len(self._items) else None

    def expandingDirections(self):
        return Qt.Orientation(0)

    def hasHeightForWidth(self) -> bool:
        return True

    def heightForWidth(self, width: int) -> int:
        return self._do_layout(QRect(0, 0, width, 0), test_only=True)

    def setGeometry(self, rect: QRect):
        super().setGeometry(rect)
        self._do_layout(rect, test_only=False)

    def sizeHint(self) -> QSize:
        return self.minimumSize()

    def minimumSize(self) -> QSize:
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        margins = self.contentsMargins()
        size += QSize(margins.left() + margins.right(), margins.top() + margins.bottom())
        return size

    def _do_layout(self, rect: QRect, test_only: bool) -> int:
        left, top, right, bottom = self.getContentsMargins()
        effective = rect.adjusted(left, top, -right, -bottom)
        spacing = self.spacing()

        # Две строки формулы часто вперемешку содержат мелкие токены
        # (знаки, скобки) и высокие (дробь) -- строке нужна её ПОЛНАЯ
        # высота ЗАРАНЕЕ, до расстановки y отдельных элементов, иначе
        # каждый элемент придётся класть по верхнему краю строки (единая
        # высота, известная сразу по ходу однопроходного цикла), и мелкие
        # токены "повиснут" у потолка строки вместо того, чтобы стоять по
        # центру вровень с чертой соседней дроби -- поэтому сначала
        # группируем элементы по строкам, и только потом просчитываем
        # позиции.
        lines: List[List[Tuple[object, QSize]]] = [[]]
        x = effective.x()
        line_height = 0
        for item in self._items:
            hint = item.sizeHint()
            next_x = x + hint.width() + spacing
            if next_x - spacing > effective.right() and line_height > 0:
                x = effective.x()
                next_x = x + hint.width() + spacing
                line_height = 0
                lines.append([])
            lines[-1].append((item, hint))
            x = next_x
            line_height = max(line_height, hint.height())

        y = effective.y()
        content_bottom = effective.y()
        for line in lines:
            if not line:
                continue
            line_height = max(hint.height() for _, hint in line)
            if not test_only:
                x = effective.x()
                for item, hint in line:
                    item_y = y + (line_height - hint.height()) // 2
                    item.setGeometry(QRect(QPoint(x, item_y), hint))
                    x += hint.width() + spacing
            y += line_height + spacing
            content_bottom = y - spacing

        return content_bottom - rect.y() + bottom

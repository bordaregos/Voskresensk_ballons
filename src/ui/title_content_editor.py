"""Встроенный редактор содержимого варианта титульного листа конструктора
документов -- открывается ПКМ («Редактировать шаблон») на уже вставленном
в документ блоке (src/ui/main_window.py, контекстное меню includedBlockList),
доступно только для пользовательских вариантов. Встроенные (TITLE_VARIANTS,
src/services/template_schema.py) сюда не попадают -- их заготовки собраны
один раз в Word вручную и generate_title_fragment() их не перезаписывает
(safe-regeneration сознательно не реализована, см. модульный докстринг
src/services/template_generator.py) -- проверка variant_id "встроенный или
нет" остаётся на стороне вызывающего кода в main_window.py.

Дизайн, обсуждённый и обкатанный сначала на JS-мокапе
(docs/design/constructor_mockup.html) перед переносом в Qt:
  1. Плейсхолдер вставляется в позицию курсора в редакторе, не в конец.
  2. Список реквизитов варианта -- ПРОИЗВОДНОЕ от того, какие плейсхолдеры
     реально сейчас в тексте (derive_subtitle_fields_from_content()), а не
     отдельно поддерживаемый список.
  3. Общий каталог полей (get_all_field_labels()) переиспользуется между
     вариантами при вставке; можно завести новое поле прямо тут.

Отличие от браузерного мокапа: там плейсхолдер -- ЛИТЕРАЛЬНЫЙ "{{ id }}"
текст с contenteditable=false (эмулирует неразбиваемый чип встроенным в
DOM API браузера). В Qt плейсхолдер -- НЕ текст вообще, а настоящий
встроенный объект (QTextObjectInterface, см. _PlaceholderChipHandler ниже)
-- цельная нередактируемая "пилюля" со скруглённым фоном, которую рисует
сам редактор, а не ран текста с подсветкой. Раньше (первая версия) чип был
именно раном с подсвеченным фоном -- на практике соседние чипы без текста
между ними визуально сливались в одно пятно (не было видно, где кончается
один плейсхолдер и начинается другой), это и стало поводом перейти на
настоящий объект: у каждого своя отрисованная рамка, границы видны всегда,
независимо от соседей. Как бонус, объект действительно атомарный -- в
отличие от рана с форматированием, вклиниться курсором в середину и
допечатать туда посимвольно физически нельзя, можно только удалить целиком.

Реальный id поля хранится в свойстве QTextCharFormat (PLACEHOLDER_PROPERTY_ID)
объекта -- тем же способом, что и раньше, извлечение содержимого
(_extract_content()) не отличает объект от прежнего рана с подсветкой.
Литеральный Jinja-синтаксис "{{ doc_number }}" появляется только при
генерации .docx (add_title_content(), template_generator.py) -- в буфере
редактора его вообще не существует как текста.
"""

from typing import Dict, List, Optional
from uuid import uuid4

from PyQt6.QtCore import QObject, QRectF, QSizeF, Qt
from PyQt6.QtGui import (
    QColor, QFont, QFontMetricsF, QPainterPath, QTextCharFormat, QTextCursor,
    QTextFormat, QTextObjectInterface,
)
from PyQt6.QtWidgets import (
    QDialog, QDialogButtonBox, QHBoxLayout, QInputDialog, QLabel, QMenu,
    QPushButton, QTextEdit, QToolButton, QVBoxLayout, QWidget,
)

from ..models.title_variant import TitleVariant, derive_subtitle_fields_from_content
from ..services.title_variants_store import get_all_field_labels, load_field_catalog, save_field_catalog
from . import icons

# Свой id свойства QTextCharFormat для пометки "это объект-плейсхолдер, а не
# обычный текст" -- значения ниже QTextFormat.Property.UserProperty
# зарезервированы самим Qt, отсюда требование начинать пользовательские с
# него же (то же самое для ObjectTypes.UserObject у типа объекта ниже).
PLACEHOLDER_PROPERTY_ID = int(QTextFormat.Property.UserProperty) + 1
_LABEL_PROPERTY_ID = int(QTextFormat.Property.UserProperty) + 2
PLACEHOLDER_OBJECT_TYPE = int(QTextFormat.ObjectTypes.UserObject) + 1

_CHIP_BACKGROUND = QColor("#123a5c")
_CHIP_BORDER = QColor("#2e6da8")
_CHIP_FOREGROUND = QColor("#5ab4ff")
_CHIP_PADDING_H = 7.0
_CHIP_PADDING_V = 3.0
_CHIP_RADIUS = 5.0


class _PlaceholderChipHandler(QObject, QTextObjectInterface):
    """Отрисовщик объекта-плейсхолдера -- один инстанс регистрируется на
    document().documentLayout() редактора (см. _build_ui()) и используется
    для ВСЕХ чипов в нём, конкретные id/подпись каждого экземпляра приходят
    через format при каждом вызове, самого обработчика не касаются."""

    def intrinsicSize(self, doc, pos_in_document, fmt):
        # Qt передаёт сюда общий QTextFormat, не QTextCharFormat -- у него
        # нет .font() (в PyQt6 даже явный QTextCharFormat(fmt)-каст из
        # базового QTextFormat не биндится, в отличие от C++ API), поэтому
        # берём шрифт с самого документа, а не пытаемся его вытащить из fmt.
        # .property() ниже и в drawObject() работает на базовом QTextFormat
        # как есть -- свойства хранятся не по подклассам.
        label = fmt.property(_LABEL_PROPERTY_ID) or ""
        metrics = QFontMetricsF(doc.defaultFont())
        width = metrics.horizontalAdvance(label) + _CHIP_PADDING_H * 2
        height = metrics.height() + _CHIP_PADDING_V * 2
        return QSizeF(width, height)

    def drawObject(self, painter, rect, doc, pos_in_document, fmt):
        label = fmt.property(_LABEL_PROPERTY_ID) or ""
        painter.save()
        painter.setRenderHint(painter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(QRectF(rect), _CHIP_RADIUS, _CHIP_RADIUS)
        painter.fillPath(path, _CHIP_BACKGROUND)
        painter.setPen(_CHIP_BORDER)
        painter.drawPath(path)
        painter.setPen(_CHIP_FOREGROUND)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, label)
        painter.restore()


def _chip_format(field_id: str, label: str) -> QTextCharFormat:
    fmt = QTextCharFormat()
    fmt.setObjectType(PLACEHOLDER_OBJECT_TYPE)
    fmt.setProperty(PLACEHOLDER_PROPERTY_ID, field_id)
    fmt.setProperty(_LABEL_PROPERTY_ID, label)
    return fmt


def _insert_chip(cursor: QTextCursor, field_id: str, label: str):
    """Вставляет чип-объект в позицию cursor -- используется и при первой
    загрузке содержимого (_load_content()), и при интерактивной вставке
    (_insert_placeholder()). Символ-заглушка ObjectReplacementCharacter --
    стандартный приём Qt для впечатывания QTextObjectInterface-объекта
    (см. drawObject() выше, который заменяет его при отрисовке на саму
    "пилюлю"), сам по себе не показывается и не хранится как текст."""
    cursor.insertText("￼", _chip_format(field_id, label))


class _PlainPasteTextEdit(QTextEdit):
    """QTextEdit по умолчанию вставляет из буфера обмена rich text как есть
    -- цвет, размер шрифта, выравнивание источника (Word, браузер, другой
    редактор) переносятся буквально. На тёмном фоне этого редактора
    вставленный текст с явным тёмным/чёрным цветом становится нечитаемым
    (обнаружено на реальной вставке -- почти невидимый текст поверх
    #1c1c1e), а поддержка bold/italic/чипов рассчитана на собственные,
    предсказуемые форматы (см. _chip_format(), _cmd_bold()/_cmd_italic()),
    не на что угодно из источника.

    insertFromMimeData() перекрыт так, чтобы ЛЮБАЯ вставка (Ctrl+V и
    drag-and-drop текста) шла как обычный текст, наследуя формат текущей
    позиции курсора (жирный/курсив, если сейчас включены через тулбар), а
    не форматирование источника."""

    def insertFromMimeData(self, source):
        if source.hasText():
            self.insertPlainText(source.text())
        else:
            super().insertFromMimeData(source)


class TitleContentEditorDialog(QDialog):
    """Модалка редактирования содержимого одного пользовательского варианта
    титульного листа. Ничего не пишет на диск сама -- при принятии (Ok)
    результат достаётся через content()/subtitle_fields(), вызывающая
    сторона (main_window.py) отвечает за сохранение в title_variants_store
    и регенерацию .docx фрагмента (generate_title_fragment()), а также за
    обновление формы реквизитов на главном экране, если этот вариант сейчас
    в документе."""

    def __init__(
        self,
        parent: QWidget,
        variant: TitleVariant,
        field_values: Optional[Dict[str, str]] = None,
    ):
        """field_values -- текущие значения полей реквизитов ГЛАВНОГО экрана,
        если variant сейчас вставлен в документ (для живого предпросмотра с
        реальными значениями); пустой словарь, если редактируется вариант,
        который сейчас не в документе -- тогда предпросмотр показывает
        подписи полей в скобках вместо значений."""
        super().__init__(parent)
        self._field_values = field_values or {}
        self.setWindowTitle(f"Редактирование шаблона: {variant.document_title}")
        self.resize(720, 420)

        self._build_ui()
        self._load_content(variant)
        self._update_preview()

    # -- UI ------------------------------------------------------------------

    def _build_ui(self):
        root = QVBoxLayout(self)

        toolbar = QHBoxLayout()
        bold_btn = QToolButton()
        bold_btn.setIcon(icons.icon("bold", "#c7c7cc", 13))
        bold_btn.setToolTip("Жирный")
        bold_btn.clicked.connect(self._cmd_bold)
        toolbar.addWidget(bold_btn)

        italic_btn = QToolButton()
        italic_btn.setIcon(icons.icon("italic", "#c7c7cc", 13))
        italic_btn.setToolTip("Курсив")
        italic_btn.clicked.connect(self._cmd_italic)
        toolbar.addWidget(italic_btn)

        insert_btn = QToolButton()
        insert_btn.setIcon(icons.icon("tag", "#c7c7cc", 13))
        insert_btn.setText(" Вставить плейсхолдер")
        insert_btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        insert_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        insert_btn.setMenu(self._build_placeholder_menu())
        toolbar.addWidget(insert_btn)
        toolbar.addStretch(1)
        root.addLayout(toolbar)

        panes = QHBoxLayout()
        editor_col = QVBoxLayout()
        editor_col.addWidget(QLabel("Содержимое титульного листа"))
        self.editor = _PlainPasteTextEdit()
        # Держим ссылку на handler в self -- PyQt не продлевает жизнь
        # Python-объекта только за счёт регистрации в C++-слое документа,
        # без этого он мог бы быть собран сборщиком мусора раньше времени.
        self._chip_handler = _PlaceholderChipHandler(self)
        self.editor.document().documentLayout().registerHandler(
            PLACEHOLDER_OBJECT_TYPE, self._chip_handler
        )
        self.editor.textChanged.connect(self._update_preview)
        editor_col.addWidget(self.editor)
        panes.addLayout(editor_col)

        preview_col = QVBoxLayout()
        preview_col.addWidget(QLabel("Предпросмотр"))
        self.preview = QTextEdit()
        self.preview.setReadOnly(True)
        preview_col.addWidget(self.preview)
        panes.addLayout(preview_col)
        root.addLayout(panes)

        hint = QLabel(
            "Подсвеченные блоки — плейсхолдеры, заменяются значениями реквизитов "
            "при сборке документа. Реквизиты на главном экране обновятся под текущий "
            "набор плейсхолдеров после сохранения."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #8e8e93; font-size: 11px;")
        root.addWidget(hint)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Save
        )
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("Сохранить шаблон")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Отмена")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _build_placeholder_menu(self) -> QMenu:
        menu = QMenu(self)
        for field_id, label in get_all_field_labels().items():
            action = menu.addAction(label)
            action.triggered.connect(lambda checked=False, fid=field_id, lbl=label: self._insert_placeholder(fid, lbl))
        menu.addSeparator()
        new_field_action = menu.addAction(icons.icon("plus", "#0a84ff", 13), "Новое поле…")
        new_field_action.triggered.connect(self._create_and_insert_new_field)
        return menu

    # -- Загрузка исходного содержимого ---------------------------------------

    def _load_content(self, variant: TitleVariant):
        cursor = self.editor.textCursor()
        labels = get_all_field_labels()
        content = variant.content
        if not content:
            # Нет content -- старый вариант или только что созданный через
            # «Добавить» без единого сохранения в этом редакторе. Стартовый
            # каркас: одна строка "Подпись: [плейсхолдер]" на поле из
            # subtitle_fields -- отправная точка для правки, не пустой лист.
            content = [
                [{"text": f"{labels.get(field_id, field_id)}: "}, {"placeholder": field_id}]
                for field_id in variant.subtitle_fields
            ]

        for paragraph_index, paragraph_runs in enumerate(content):
            if paragraph_index > 0:
                cursor.insertBlock()
            for run_spec in paragraph_runs:
                field_id = run_spec.get("placeholder")
                if field_id:
                    _insert_chip(cursor, field_id, labels.get(field_id, field_id))
                    continue
                fmt = QTextCharFormat()
                if run_spec.get("bold"):
                    fmt.setFontWeight(QFont.Weight.Bold.value)
                if run_spec.get("italic"):
                    fmt.setFontItalic(True)
                cursor.insertText(run_spec.get("text", ""), fmt)

    # -- Форматирование --------------------------------------------------------

    def _cmd_bold(self):
        is_bold = self.editor.fontWeight() >= QFont.Weight.Bold.value
        self.editor.setFontWeight(QFont.Weight.Normal.value if is_bold else QFont.Weight.Bold.value)

    def _cmd_italic(self):
        self.editor.setFontItalic(not self.editor.fontItalic())

    # -- Вставка плейсхолдеров ---------------------------------------------

    def _insert_placeholder(self, field_id: str, label: str):
        # self.editor.textCursor() -- это позиция курсора, оставленная
        # пользователем при последнем взаимодействии с самим полем
        # редактирования; клик по тулбару/пункту меню её не сдвигает (в
        # отличие от DOM, где contenteditable теряет Range при потере
        # фокуса -- в мокапе поэтому пришлось вручную сохранять/восстанавливать
        # выделение, здесь это не нужно). Поэтому вставка попадает ровно
        # туда, куда пользователь ткнул перед тем, как открыть меню.
        cursor = self.editor.textCursor()
        _insert_chip(cursor, field_id, label)
        # Пробел обычным форматом сразу после чипа -- чтобы вставленные
        # подряд несколько плейсхолдеров не оказались впритык друг к другу
        # (сама "пилюля" при этом всё равно отрисована отдельным блоком со
        # своей рамкой, см. _PlaceholderChipHandler -- слипание тут не
        # визуальное, а просто отсутствие места, куда поставить курсор
        # между ними при печати дальше).
        cursor.insertText(" ", QTextCharFormat())
        self.editor.setTextCursor(cursor)
        self.editor.setFocus()

    def _create_and_insert_new_field(self):
        label, ok = QInputDialog.getText(self, "Новое поле", "Название поля:")
        label = label.strip()
        if not ok or not label:
            return
        field_id = "field_" + uuid4().hex[:8]
        catalog = load_field_catalog()
        catalog[field_id] = label
        save_field_catalog(catalog)
        self._insert_placeholder(field_id, label)

    # -- Извлечение содержимого / производных полей ---------------------------

    def _extract_content(self) -> List[List[Dict]]:
        """Сканирует QTextDocument редактора в структурированное content --
        см. src/models/title_variant.py, TitleVariant.content."""
        content: List[List[Dict]] = []
        block = self.editor.document().begin()
        while block.isValid():
            paragraph: List[Dict] = []
            it = block.begin()
            while not it.atEnd():
                fragment = it.fragment()
                if fragment.isValid() and fragment.text():
                    fmt = fragment.charFormat()
                    field_id = fmt.property(PLACEHOLDER_PROPERTY_ID)
                    if field_id:
                        paragraph.append({"placeholder": field_id})
                    else:
                        run: Dict = {"text": fragment.text()}
                        if fmt.fontWeight() >= QFont.Weight.Bold.value:
                            run["bold"] = True
                        if fmt.fontItalic():
                            run["italic"] = True
                        paragraph.append(run)
                it += 1
            content.append(paragraph)
            block = block.next()
        return content

    def content(self) -> List[List[Dict]]:
        """Итоговое содержимое -- вызывать после exec() == Accepted."""
        return self._extract_content()

    def subtitle_fields(self) -> List[str]:
        """Итоговый список плейсхолдеров, производный от содержимого."""
        return derive_subtitle_fields_from_content(self._extract_content())

    # -- Живой предпросмотр -----------------------------------------------

    def _update_preview(self):
        labels = get_all_field_labels()
        self.preview.clear()
        cursor = self.preview.textCursor()
        content = self._extract_content()
        for paragraph_index, paragraph_runs in enumerate(content):
            if paragraph_index > 0:
                cursor.insertBlock()
            for run in paragraph_runs:
                field_id = run.get("placeholder")
                if field_id:
                    label = labels.get(field_id, field_id)
                    value = self._field_values.get(field_id, "").strip()
                    fmt = QTextCharFormat()
                    if value:
                        cursor.insertText(value, fmt)
                    else:
                        fmt.setForeground(QColor("#8e8e93"))
                        fmt.setFontItalic(True)
                        cursor.insertText(f"[{label}]", fmt)
                    continue
                fmt = QTextCharFormat()
                if run.get("bold"):
                    fmt.setFontWeight(QFont.Weight.Bold.value)
                if run.get("italic"):
                    fmt.setFontItalic(True)
                cursor.insertText(run.get("text", ""), fmt)

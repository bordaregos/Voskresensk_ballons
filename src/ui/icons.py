"""Иконки конструктора документов.

Тот же набор символов и тот же визуальный стиль (обводка, viewBox 24x24,
stroke-width 2, скруглённые концы), что в SVG-спрайте
docs/design/constructor_mockup.html -- копии путей оттуда, один в один.

В проекте нет иконочного шрифта/.qrc (см. CLAUDE.md) -- вместо этого SVG
рендерится в QPixmap на лету через QtSvg.QSvgRenderer, с нужным цветом
(color подставляется прямо в атрибут stroke перед рендером). QtSvg --
часть того же пакета PyQt6 (requirements.txt), отдельной зависимости не
добавляет.
"""

from functools import lru_cache

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QIcon, QPainter, QPixmap
from PyQt6.QtSvg import QSvgRenderer

_PATHS = {
    "chevron-right": '<polyline points="9 6 15 12 9 18"/>',
    "chevron-down": '<polyline points="6 9 12 15 18 9"/>',
    "chevron-up": '<polyline points="6 15 12 9 18 15"/>',
    "files": (
        '<rect x="3" y="7" width="13" height="13" rx="2"/>'
        '<path d="M8 7V4a1 1 0 0 1 1-1h11a1 1 0 0 1 1 1v11a1 1 0 0 1-1 1h-3"/>'
    ),
    "file-text": (
        '<path d="M14 3v4a1 1 0 0 0 1 1h4"/>'
        '<path d="M17 21H7a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h7l5 5v11a2 2 0 0 1-2 2z"/>'
        '<line x1="9" y1="9" x2="10" y2="9"/>'
        '<line x1="9" y1="13" x2="15" y2="13"/>'
        '<line x1="9" y1="17" x2="15" y2="17"/>'
    ),
    "plus": '<line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>',
    "drag-drop": (
        '<rect x="4" y="4" width="16" height="16" rx="2" stroke-dasharray="4 3"/>'
        '<path d="M12 9v6"/><path d="M9 12l3 3 3-3"/>'
    ),
    "x": '<line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>',
    "trash": (
        '<line x1="4" y1="7" x2="20" y2="7"/>'
        '<path d="M10 11v6"/><path d="M14 11v6"/>'
        '<path d="M5 7l1 12a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2l1-12"/>'
        '<path d="M9 7V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v3"/>'
    ),
    "edit": '<path d="M12 20h9"/><path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4Z"/>',
    "bold": (
        '<path d="M6 4h8a3.5 3.5 0 0 1 0 7H6z"/>'
        '<path d="M6 11h9a3.5 3.5 0 0 1 0 7H6z"/>'
    ),
    "italic": '<line x1="19" y1="4" x2="10" y2="4"/><line x1="14" y1="20" x2="5" y2="20"/><line x1="15" y1="4" x2="9" y2="20"/>',
    # Без залитой точки-дырочки, в отличие от мокапа -- fill="currentColor"
    # без явного CSS color рендерился бы чёрным независимо от переданного
    # color (см. _svg_bytes), остальные иконки в наборе тоже чисто контурные.
    "tag": (
        '<path d="M20.59 13.41L11 3.83A2 2 0 0 0 9.59 3.24L4 3a1 1 0 0 0-1 1l.24 5.59a2 2 0 0 0 .59 1.41'
        'l9.58 9.58a2 2 0 0 0 2.83 0l4.35-4.35a2 2 0 0 0 0-2.82z"/>'
        '<circle cx="7.5" cy="7.5" r="1.2"/>'
    ),
    "table": (
        '<rect x="3" y="4" width="18" height="16" rx="1.5"/>'
        '<line x1="3" y1="10" x2="21" y2="10"/><line x1="9" y1="10" x2="9" y2="20"/>'
    ),
    "signature": (
        '<path d="M3 17c2-4 3-6 5-6s2 3 4 3 3-5 5-5 2 4 4 4"/>'
        '<line x1="3" y1="21" x2="21" y2="21"/>'
    ),
    "upload": (
        '<path d="M4 17v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2"/>'
        '<polyline points="7 9 12 4 17 9"/><line x1="12" y1="4" x2="12" y2="15"/>'
    ),
    # Дробная черта с точкой-числителем/точкой-знаменателем -- «Создать
    # формулу»/«Редактировать формулу» в ПКМ-меню чипа плейсхолдера (см.
    # src/ui/main_window.py, _show_chip_context_menu()). Точки -- такие же
    # незалитые кружки-контуры, как у "tag" выше, по той же причине
    # (fill="currentColor" не резолвится через этот рендерер).
    "formula": '<line x1="4" y1="12" x2="20" y2="12"/><circle cx="8" cy="6" r="1.3"/><circle cx="16" cy="18" r="1.3"/>',
}


def _svg_bytes(name: str, color: str) -> bytes:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
        f'fill="none" stroke="{color}" stroke-width="2" '
        f'stroke-linecap="round" stroke-linejoin="round">{_PATHS[name]}</svg>'
    ).encode("utf-8")


@lru_cache(maxsize=256)
def render(name: str, color: str = "#8e8e93", size: int = 16) -> QPixmap:
    """Растеризует иконку `name` цветом `color` в квадратный QPixmap
    size x size. Кэшируется по (name, color, size) -- одни и те же
    комбинации запрашиваются на каждую перестройку списка/каждый drop."""
    renderer = QSvgRenderer(_svg_bytes(name, color))
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pm)
    renderer.render(painter)
    painter.end()
    return pm


def icon(name: str, color: str = "#8e8e93", size: int = 16) -> QIcon:
    """QIcon-обёртка над render() -- для QPushButton/QListWidgetItem/QAction."""
    return QIcon(render(name, color, size))


def combine(specs, size: int = 14, gap: int = 4) -> QIcon:
    """Собирает несколько иконок бок о бок в один QIcon -- для мокапа
    группы «Титульные листы» (шеврон + папка перед текстом), у которой в
    .ui обычная QPushButton с одним слотом под icon().

    specs -- список пар (name, color). Не кэшируется (в отличие от
    render()) -- вызывается только на переключение группы, не на каждую
    перерисовку списка."""
    total_width = len(specs) * size + gap * max(0, len(specs) - 1)
    pm = QPixmap(total_width, size)
    pm.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pm)
    x = 0
    for name, color in specs:
        painter.drawPixmap(x, 0, render(name, color, size))
        x += size + gap
    painter.end()
    return QIcon(pm)

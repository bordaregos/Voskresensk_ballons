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

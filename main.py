"""Точка входа в приложение."""

import sys
import os

# Добавляем корень проекта в sys.path, чтобы работали импорты пакета src/
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication, QInputDialog

from src.equipment_types import REGISTRY
from src.ui.main_window import MainWindow


def fit_window_to_screen(window, fraction: float = 0.9):
    """Подгоняет размер и положение окна под доступную область экрана.

    Окно не масштабируется сверх своего заданного в .ui размера (если
    экран больше -- остаётся как задизайнено), но ужимается и
    центрируется, если экран меньше -- иначе на небольших ноутбучных
    экранах/диагоналях окно может открыться за пределами видимой области.
    """
    screen = window.screen() or QApplication.primaryScreen()
    if screen is None:
        return
    available = screen.availableGeometry()
    width = min(window.width(), int(available.width() * fraction))
    height = min(window.height(), int(available.height() * fraction))
    window.resize(width, height)
    window.move(
        available.x() + (available.width() - width) // 2,
        available.y() + (available.height() - height) // 2,
    )


def main():
    """Запуск приложения."""
    app = QApplication(sys.argv)

    # Выбор типа объекта нужен только когда в реестре больше одного типа —
    # пока это не так, диалог не показывается и поведение не меняется.
    if len(REGISTRY) > 1:
        types = list(REGISTRY.values())
        labels = [t.label for t in types]
        label, ok = QInputDialog.getItem(
            None, "Тип объекта", "Выберите тип объекта освидетельствования:", labels, editable=False
        )
        if not ok:
            return
        equipment_type = types[labels.index(label)]
    else:
        equipment_type = next(iter(REGISTRY.values()))

    # Создаём и показываем главное окно
    window = MainWindow(equipment_type)
    fit_window_to_screen(window)
    window.show()

    # Запускаем цикл событий
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

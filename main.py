"""Точка входа в приложение."""

import sys
import os

# Добавляем корень проекта в sys.path, чтобы работали импорты пакета src/
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication

from src.ui.main_window import MainWindow


def main():
    """Запуск приложения."""
    app = QApplication(sys.argv)
    
    # Создаём и показываем главное окно
    window = MainWindow()
    window.show()
    
    # Запускаем цикл событий
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

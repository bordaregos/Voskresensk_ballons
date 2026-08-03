"""
Точка входа в приложение.

Этот файл использует старый UI из ui_logic.py, но подключает
новые сервисы из пакета src/ для расчётов и генерации документов.
"""

import sys
import os

# Добавляем путь к src/ в sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication

# Используем старый UI
from ui_logic import MainWindow


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

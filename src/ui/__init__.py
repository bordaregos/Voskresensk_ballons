"""Инициализация UI пакета.

Без eager-импортов MainWindow/FileHandler здесь: main_window.py импортирует
equipment_types.py, а тот резолвит widget_names через src.ui — жадный
импорт MainWindow в этом __init__ создавал цикл. Импортируйте напрямую из
подмодулей: from src.ui.main_window import MainWindow.
"""

"""Импорт и экспорт данных в UI."""

from pathlib import Path
from typing import List, Dict, Any

from PyQt6.QtWidgets import QFileDialog, QMessageBox, QTableWidgetItem

from src.services.importer import (
    import_balloon_list_from_csv,
    import_project_from_json,
)
from src.services.exporter import (
    export_balloon_list_to_csv,
    export_report_to_json,
)
from src.models.project import Project, BalloonProject
from src.config import OUTPUT_DIR


class FileHandler:
    """Обработчик файлов для импорта/экспорта."""
    
    def __init__(self, main_window):
        """
        Инициализация обработчика файлов.
        
        Args:
            main_window: Экземпляр MainWindow
        """
        self.main_window = main_window
    
    def import_csv_balloon_list(self):
        """
        Импорт списка баллонов из CSV файла.
        
        Открывает диалог выбора файла и загружает данные в таблицу баллонов.
        """
        file_path, _ = QFileDialog.getOpenFileName(
            self.main_window,
            "Выберите CSV файл с баллонами",
            str(OUTPUT_DIR),
            "CSV файлы (*.csv);;All files (*.*)"
        )
        
        if not file_path:
            return
        
        try:
            # Импорт данных
            balloons_data = import_balloon_list_from_csv(Path(file_path))
            
            if not balloons_data:
                self.main_window.show_message(
                    "Ошибка",
                    "Файл не содержит данных баллонов",
                    QMessageBox.Icon.Warning
                )
                return
            
            # Заполнение таблицы баллонов
            self._fill_balloon_table_from_data(balloons_data)
            
            self.main_window.show_message(
                "Успех",
                f"Загружено {len(balloons_data)} баллонов из CSV",
                QMessageBox.Icon.Information
            )
            
        except Exception as e:
            self.main_window.show_message(
                "Ошибка импорта",
                f"Ошибка при импорте CSV: {str(e)}",
                QMessageBox.Icon.Critical
            )
    
    def export_csv_balloon_list(self):
        """
        Экспорт списка баллонов в CSV файл.
        
        Сохраняет данные из таблицы баллонов в CSV файл.
        """
        file_path, _ = QFileDialog.getSaveFileName(
            self.main_window,
            "Выберите место для сохранения CSV",
            str(OUTPUT_DIR / "баллоны.csv"),
            "CSV файлы (*.csv);;All files (*.*)"
        )
        
        if not file_path:
            return
        
        try:
            # Получение данных из таблицы
            balloons_data = self._get_balloon_data_from_table()
            
            if not balloons_data:
                self.main_window.show_message(
                    "Ошибка",
                    "Таблица баллонов пуста",
                    QMessageBox.Icon.Warning
                )
                return
            
            # Экспорт в CSV
            export_balloon_list_to_csv(balloons_data, Path(file_path))
            
            self.main_window.show_message(
                "Успех",
                f"Данные сохранены в {file_path}",
                QMessageBox.Icon.Information
            )
            
        except Exception as e:
            self.main_window.show_message(
                "Ошибка экспорта",
                f"Ошибка при экспорте в CSV: {str(e)}",
                QMessageBox.Icon.Critical
            )
    
    def save_project_json(self):
        """
        Сохранение проекта в JSON файл.
        
        Сохраняет все данные проекта в JSON файл.
        """
        file_path, _ = QFileDialog.getSaveFileName(
            self.main_window,
            "Выберите место для сохранения проекта",
            str(OUTPUT_DIR / "проект.json"),
            "JSON файлы (*.json);;All files (*.*)"
        )
        
        if not file_path:
            return
        
        try:
            # Создание проекта
            project = self._create_project()
            
            # Сохранение
            project.save_to_file(Path(file_path))
            
            self.main_window.show_message(
                "Успех",
                f"Проект сохранён в {file_path}",
                QMessageBox.Icon.Information
            )
            
        except Exception as e:
            self.main_window.show_message(
                "Ошибка",
                f"Ошибка при сохранении проекта: {str(e)}",
                QMessageBox.Icon.Critical
            )
    
    def open_project_json(self):
        """
        Загрузка проекта из JSON файла.
        
        Загружает все данные проекта из JSON файла.
        """
        file_path, _ = QFileDialog.getOpenFileName(
            self.main_window,
            "Выберите JSON файл проекта",
            str(OUTPUT_DIR),
            "JSON файлы (*.json);;All files (*.*)"
        )
        
        if not file_path:
            return
        
        try:
            # Загрузка проекта
            project = Project.load_from_file(Path(file_path))
            
            # Заполнение UI данными
            self._fill_ui_from_project(project)
            
            self.main_window.show_message(
                "Успех",
                f"Проект загружен из {file_path}",
                QMessageBox.Icon.Information
            )
            
        except Exception as e:
            self.main_window.show_message(
                "Ошибка",
                f"Ошибка при загрузке проекта: {str(e)}",
                QMessageBox.Icon.Critical
            )
    
    def _fill_balloon_table_from_data(self, balloons_data: List[Dict[str, Any]]):
        """
        Заполнение таблицы баллонов данными из списка.
        
        Args:
            balloons_data: Список словарей с данными баллонов
        """
        table = self.main_window.table_ballons
        table.setRowCount(len(balloons_data))
        
        for row, balloon_data in enumerate(balloons_data):
            # Заводской номер
            serial = balloon_data.get('serial_number', '')
            item = QTableWidgetItem(str(serial))
            table.setItem(row, 0, item)
            
            # Минимальная толщина (если есть)
            min_thick = balloon_data.get('min_thickness')
            if min_thick is not None:
                item = QTableWidgetItem(str(min_thick).replace('.', ','))
                table.setItem(row, 1, item)
            
            # Год изготовления - миграция старого формата
            # В старом JSON: max_thickness содержал год, year_of_manufacture сод��ржал массу
            # В новом JSON: year_of_manufacture - год, mass - масса
            
            # 1. Сначала проверяем max_thickness на год (старый формат)
            year = None
            max_thick_val = balloon_data.get('max_thickness')
            if max_thick_val is not None:
                val = float(str(max_thick_val).replace(',', '.'))
                if val > 1900:  # это год в старом формате
                    year = int(val)
                elif val < 100:  # это толщина
                    item = QTableWidgetItem(str(val).replace('.', ','))
                    table.setItem(row, 1, item)
            
            # 2. Проверяем year_of_manufacture (может быть масса в старом формате)
            # В старом формате year_of_manufacture содержал массу, а не год
            year_val = balloon_data.get('year_of_manufacture')
            if year_val is not None:
                val = float(str(year_val).replace(',', '.'))
                if val > 1900:  # это год (новый формат)
                    if year is None:  # не нашли год в max_thickness
                        year = int(val)
                elif val < 100:  # это масса (в старом или новом формате)
                    mass = val
                    item = QTableWidgetItem(str(mass).replace('.', ','))
                    table.setItem(row, 3, item)
            
            # 3. Если год найден, заполняем его в таблицу
            if year is not None:
                item = QTableWidgetItem(str(year))
                table.setItem(row, 2, item)
            
            # 4. Проверяем mass (новый формат)
            mass = balloon_data.get('mass')
            if mass is not None:
                item = QTableWidgetItem(str(mass).replace('.', ','))
                if table.item(row, 3) is None:  # не заполнили уже
                    table.setItem(row, 3, item)
            
            # Масса - пытаемся найти в mass
            mass = balloon_data.get('mass')
            if mass is not None:
                # Проверяем не заполнили ли мы уже массу из year_of_manufacture
                if table.item(row, 3) is None:
                    item = QTableWidgetItem(str(mass).replace('.', ','))
                    table.setItem(row, 3, item)
            
            # Миграция: если max_thickness есть и > 100, это масса
            max_thick = balloon_data.get('max_thickness')
            if max_thick is not None and table.item(row, 3) is None:
                val = float(str(max_thick).replace(',', '.'))
                if val > 100:  # это масса
                    item = QTableWidgetItem(str(val).replace('.', ','))
                    table.setItem(row, 3, item)
            
            # Миграция: если max_thickness < 100 и не заполнена толщина, это может быть Sмакс
            if max_thick is not None and table.item(row, 1) is None:
                val = float(str(max_thick).replace(',', '.'))
                if val < 100:  # это толщина
                    item = QTableWidgetItem(str(val).replace('.', ','))
                    table.setItem(row, 1, item)
        
        # Обновление с_min_lst для последующих расчётов
        self.main_window.s_min_lst = []
        for row in range(table.rowCount()):
            item = table.item(row, 1)
            if item and item.text():
                try:
                    self.main_window.s_min_lst.append(float(item.text().replace(',', '.')))
                except ValueError:
                    pass
    
    def _get_balloon_data_from_table(self) -> List[Dict[str, Any]]:
        """
        Получение данных баллонов из таблицы.
        
        Returns:
            Список словарей с данными баллонов
        """
        table = self.main_window.table_ballons
        balloons = []
        
        for row in range(table.rowCount()):
            balloon = {}
            
            # Заводской номер
            item = table.item(row, 0)
            if item and item.text():
                balloon['serial_number'] = item.text()
            
            # Минимальная толщина
            item = table.item(row, 1)
            if item and item.text():
                balloon['min_thickness'] = float(item.text().replace(',', '.'))
            
            # Год изготовления - теперь это 3 колонка
            item = table.item(row, 2)
            if item and item.text():
                # Год должен быть целым числом
                balloon['year_of_manufacture'] = int(float(item.text().replace(',', '.')))
            
            # Масса - теперь это 4 колонка
            item = table.item(row, 3)
            if item and item.text():
                balloon['mass'] = float(item.text().replace(',', '.'))
            
            if balloon.get('serial_number'):
                balloons.append(balloon)
        
        return balloons
    
    def _create_project(self) -> Project:
        """
        Создание объекта Project из текущих данных UI.
        
        Returns:
            Объект Project
        """
        # Получение данных формы
        form_data = self.main_window.get_form_data()
        
        # Получение данных баллонов
        balloons_data = self._get_balloon_data_from_table()
        
        project = Project(
            report_data=form_data,
            balloons_data=balloons_data,
            settings={
                'working_pressure': form_data.get('p_rab_MPa', 39.0),
                'hydro_test_pressure': form_data.get('p_gidro', 59.0),
                'pneumatic_test_pressure': form_data.get('p_pnevma', 45.0),
            },
            output_dir=str(OUTPUT_DIR),
        )
        
        return project
    
    def _fill_ui_from_project(self, project: Project):
        """
        Заполнение UI данными из проекта.
        
        Args:
            project: Объект Project
        """
        from PyQt6.QtCore import QDate, QLocale
        
        # Заполнение форм данными из report_data
        for key, value in project.report_data.items():
            widget = getattr(self.main_window, key, None)
            if widget is not None:
                if hasattr(widget, 'setPlainText'):
                    widget.setPlainText(str(value))
                elif hasattr(widget, 'setCurrentText'):
                    widget.setCurrentText(str(value))
                elif hasattr(widget, 'setValue'):
                    try:
                        # Заменяем запятую на точку перед преобразованием
                        val = float(str(value).replace(',', '.'))
                        widget.setValue(int(val))
                    except (ValueError, TypeError):
                        pass
                elif hasattr(widget, 'setDate'):
                    # Обработка QDateEdit
                    if isinstance(value, str):
                        # Пытаемся распарсить дату в формате dd.MM.yyyy или dd MMMM yyyy
                        try:
                            # Сначала пытаемся как dd.MM.yyyy
                            date_parts = value.split('.')
                            if len(date_parts) == 3:
                                day = int(date_parts[0])
                                month = int(date_parts[1])
                                year = int(date_parts[2])
                                widget.setDate(QDate(year, month, day))
                            else:
                                # Если не удалось, пробуем через QLocale
                                locale = QLocale('ru_RU')
                                date = locale.toDate(value, 'dd MMMM yyyy')
                                if date.isValid():
                                    widget.setDate(date)
                        except (ValueError, IndexError):
                            pass
                    elif isinstance(value, (int, float)):
                        # Если передан год, создаем дату (например, 2026 -> 01.01.2026)
                        widget.setDate(QDate(int(value), 1, 1))
        
        # Заполнение таблицы баллонов
        self._fill_balloon_table_from_data(project.balloons_data)

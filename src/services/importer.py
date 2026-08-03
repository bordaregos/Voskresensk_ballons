"""Импорт данных из CSV и JSON файлов."""

import csv
import json
from pathlib import Path
from typing import Dict, List, Any, Optional


class BalloonImportError(Exception):
    """Исключение для ошибок импорта."""
    pass


class CSVImporter:
    """Импорт данных из CSV файлов."""
    
    # Стандартные заголовки CSV для баллонов
    BALLOON_HEADERS = {
        'serial_number': ['зав№', 'заг№', 'serial', 'serial_number', 'serialnumber'],
        'min_thickness': ['sмин', 's_min', 'smin', 'мин', 'min'],
        'year_of_manufacture': ['г.и.', 'god', 'year', 'год', 'year_of_manufacture', 'Год изготовления'],
        'mass': ['масса', 'mass', 'Масса'],
    }
    
    def __init__(self):
        """Инициализация импортера."""
        self.errors: List[str] = []
    
    def import_balloon_csv(self, filepath: Path) -> List[Dict[str, Any]]:
        """
        Импорт данных баллонов из CSV файла.
        
        Args:
            filepath: Путь к CSV файлу
            
        Returns:
            Список словарей с данными баллонов
            
        Raises:
            BalloonImportError: Если файл не найден или ошибка при чтении
        """
        if not filepath.exists():
            raise BalloonImportError(f"Файл не найден: {filepath}")
        
        balloons = []
        
        try:
            with open(filepath, 'r', encoding='utf-8-sig') as file:
                reader = csv.DictReader(file, delimiter=';')
                
                for row_num, row in enumerate(reader, start=2):  # start=2 из-за заголовка
                    balloon_data = self._parse_balloon_row(row, row_num)
                    if balloon_data:
                        balloons.append(balloon_data)
        
        except UnicodeDecodeError:
            # Попытка прочитать в другой кодировке
            with open(filepath, 'r', encoding='cp1251') as file:
                reader = csv.DictReader(file, delimiter=';')
                
                for row_num, row in enumerate(reader, start=2):
                    balloon_data = self._parse_balloon_row(row, row_num)
                    if balloon_data:
                        balloons.append(balloon_data)
        
        except csv.Error as e:
            raise BalloonImportError(f"Ошибка при чтении CSV: {e}")
        
        return balloons
    
    def _parse_balloon_row(self, row: Dict[str, str], row_num: int) -> Optional[Dict[str, Any]]:
        """
        Парсинг одной строки CSV файла.
        
        Args:
            row: Словарь с данными строки
            row_num: Номер строки для сообщений об ошибках
            
        Returns:
            Словарь с данными баллона или None если строка пустая
        """
        balloon_data = {}
        
        # Ищем заводской номер
        serial = self._find_field(row, self.BALLOON_HEADERS['serial_number'])
        if not serial:
            self.errors.append(f"Строка {row_num}: не найден заводской номер")
            return None
        
        balloon_data['serial_number'] = serial.strip()
        
        # Ищем минимальную толщину
        min_thick = self._find_field(row, self.BALLOON_HEADERS['min_thickness'])
        if min_thick:
            try:
                balloon_data['min_thickness'] = float(min_thick.replace(',', '.'))
            except ValueError:
                self.errors.append(f"Строка {row_num}: некорректное значение Sмин '{min_thick}'")
        
        # Ищем год изготовления
        year = self._find_field(row, self.BALLOON_HEADERS['year_of_manufacture'])
        if year:
            try:
                # Handle Russian decimal separator (comma)
                balloon_data['year_of_manufacture'] = int(float(year.replace(',', '.')))
            except ValueError:
                self.errors.append(f"Строка {row_num}: некорректный год '{year}'")
        
        # Ищем массу
        mass = self._find_field(row, self.BALLOON_HEADERS['mass'])
        if mass:
            try:
                balloon_data['mass'] = float(mass.replace(',', '.'))
            except ValueError:
                self.errors.append(f"Строка {row_num}: некорректное значение массы '{mass}'")
        
        return balloon_data
    
    def _find_field(self, row: Dict[str, str], possible_names: List[str]) -> Optional[str]:
        """
        Поиск поля в строке по возможным названиям.
        
        Args:
            row: Словарь с данными
            possible_names: Список возможных названий поля
            
        Returns:
            Значение поля или None
        """
        # Прямой поиск
        for name in possible_names:
            if name in row and row[name]:
                return row[name]
        
        # Поиск с учетом регистра
        row_lower = {k.lower(): v for k, v in row.items()}
        for name in possible_names:
            if name.lower() in row_lower and row_lower[name.lower()]:
                return row_lower[name.lower()]
        
        return None


class JSONImporter:
    """Импорт данных из JSON файлов."""
    
    def import_project(self, filepath: Path) -> Dict[str, Any]:
        """
        Импорт полного проекта из JSON файла.
        
        Args:
            filepath: Путь к JSON файлу
            
        Returns:
            Словарь с данными проекта
            
        Raises:
            BalloonImportError: Если файл не найден или ошибка при чтении
        """
        if not filepath.exists():
            raise BalloonImportError(f"Файл не найден: {filepath}")
        
        try:
            with open(filepath, 'r', encoding='utf-8') as file:
                data = json.load(file)
            return data
        except json.JSONDecodeError as e:
            raise BalloonImportError(f"Ошибка при чтении JSON: {e}")


def import_balloon_list_from_csv(filepath: Path) -> List[Dict[str, Any]]:
    """
    Упрощённая функция импорта баллонов из CSV.
    
    Args:
        filepath: Путь к CSV файлу
        
    Returns:
        Список словарей с данными баллонов
    """
    importer = CSVImporter()
    return importer.import_balloon_csv(filepath)


def import_project_from_json(filepath: Path) -> Dict[str, Any]:
    """
    Упрощённая функция импорта проекта из JSON.
    
    Args:
        filepath: Путь к JSON файлу
        
    Returns:
        Словарь с данными проекта
    """
    importer = JSONImporter()
    return importer.import_project(filepath)

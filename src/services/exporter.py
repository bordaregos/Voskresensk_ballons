"""Экспорт данных в CSV и JSON файлы."""

import csv
import json
from pathlib import Path
from typing import Dict, List, Any

from ..config import OUTPUT_DIR


class Exporter:
    """Экспорт данных в различные форматы."""
    
    def __init__(self):
        """Инициализация экспортера."""
        pass
    
    def export_balloon_list_to_csv(self, balloons: List[Dict[str, Any]], filepath: Path) -> str:
        """
        Экспорт списка баллонов в CSV файл.
        
        Args:
            balloons: Список словарей с данными баллонов
            filepath: Путь к выходному файлу
            
        Returns:
            Путь к сохранённому файлу
        """
        if not balloons:
            raise ValueError("Список баллонов пуст")
        
        # Определяем заголовки на основе данных
        headers = ['зав№', 'Sмин', 'Год изготовления', 'Масса']
        
        with open(filepath, 'w', newline='', encoding='utf-8-sig') as file:
            writer = csv.DictWriter(
                file,
                fieldnames=headers,
                delimiter=';',
                quoting=csv.QUOTE_NONNUMERIC
            )
            writer.writeheader()
            
            for balloon in balloons:
                row = {
                    headers[0]: balloon.get('serial_number', ''),
                    headers[1]: str(balloon.get('min_thickness', '')).replace('.', ','),
                    headers[2]: str(balloon.get('year_of_manufacture', '')).replace('.', ','),
                    headers[3]: str(balloon.get('mass', '')).replace('.', ','),
                }
                writer.writerow(row)
        
        return str(filepath)
    
    def export_balloon_list_to_json(self, balloons: List[Dict[str, Any]], filepath: Path) -> str:
        """
        Экспорт списка баллонов в JSON файл.
        
        Args:
            balloons: Список словарей с данными баллонов
            filepath: Путь к выходному файлу
            
        Returns:
            Путь к сохранённому файлу
        """
        with open(filepath, 'w', encoding='utf-8') as file:
            json.dump(balloons, file, ensure_ascii=False, indent=2)
        
        return str(filepath)


def export_balloon_list_to_csv(balloons: List[Dict[str, Any]], filepath: Path) -> str:
    """
    Упрощённая функция экспорта баллонов в CSV.

    Args:
        balloons: Список словарей с данными баллонов
        filepath: Путь к выходному файлу

    Returns:
        Путь к сохранённому файлу
    """
    exporter = Exporter()
    return exporter.export_balloon_list_to_csv(balloons, filepath)

"""Экспорт данных в CSV и JSON файлы."""

import csv
import json
from pathlib import Path
from typing import Dict, List, Any

from ..models.balloon import Report, Balloon
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
    
    def export_report_to_json(self, report: Report, filepath: Path) -> str:
        """
        Экспорт заключения в JSON файл.
        
        Args:
            report: Модель заключения
            filepath: Путь к выходному файлу
            
        Returns:
            Путь к сохранённому файлу
        """
        data = self._report_to_dict(report)
        
        with open(filepath, 'w', encoding='utf-8') as file:
            json.dump(data, file, ensure_ascii=False, indent=2)
        
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
    
    def _report_to_dict(self, report: Report) -> Dict[str, Any]:
        """
        Преобразование модели Report в словарь для JSON.
        
        Args:
            report: Модель заключения
            
        Returns:
            Словарь с данными
        """
        return {
            'report_number': report.report_number,
            'registration_number': report.registration_number,
            'creation_date': report.creation_date.strftime('%d.%m.%Y') if report.creation_date else None,
            'section_name': report.section_name,
            'date_of_injection': report.date_of_injection,
            'test_medium': report.test_medium,
            'gost': report.gost,
            'total_count': report.total_count,
            'total_volume': report.total_volume,
            'working_pressure': report.working_pressure,
            'hydro_test_pressure': report.hydro_test_pressure,
            'pneumatic_test_pressure': report.pneumatic_test_pressure,
            'test_pressure_pneumatic_kgs': report.test_pressure_pneumatic_kgs,
            'min_wall_thickness': report.min_wall_thickness,
            'min_wall_thickness_serial': report.min_wall_thickness_serial,
            'year_range': report.year_range,
            'calculated_sigma': report.calculated_sigma,
            'calculated_sigma_hydro': report.calculated_sigma_hydro,
            'calculated_thickness': report.calculated_thickness,
            'calculated_thickness_hydro': report.calculated_thickness_hydro,
            'max_calculated_thickness': report.max_calculated_thickness,
            'permissible_pressure': report.permissible_pressure,
            'corrosion_rate': report.corrosion_rate,
            'remaining_life': report.remaining_life,
            'remaining_life_comment': report.remaining_life_comment,
            'hardness_min': report.hardness_min,
            'hardness_max': report.hardness_max,
            'balloons': [
                {
                    'serial_number': b.serial_number,
                    'registration_number': b.registration_number,
                    'nominal_volume': b.nominal_volume,
                    'outer_diameter': b.outer_diameter,
                    'wall_thickness': b.wall_thickness,
                    'material_yield_strength': b.material_yield_strength,
                    'material_ultimate_strength': b.material_ultimate_strength,
                    'material': b.material,
                    'year_of_manufacture': b.year_of_manufacture,
                    'manufacturer': b.manufacturer,
                    'thickness_measurements': b.thickness_measurements,
                    'date_of_installation': b.date_of_installation.strftime('%d.%m.%Y') if b.date_of_installation else None,
                    'years_of_operation': b.years_of_operation,
                    'corrosion_allowance': b.corrosion_allowance,
                    'working_pressure': b.working_pressure,
                    'hydro_test_pressure': b.hydro_test_pressure,
                    'pneumatic_test_pressure': b.pneumatic_test_pressure,
                    'test_medium': b.test_medium,
                    'length': b.length,
                    'mass': b.mass,
                    'design_code': b.design_code,
                }
                for b in report.balloons
            ],
        }


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


def export_report_to_json(report: Report, filepath: Path) -> str:
    """
    Упрощённая функция экспорта заключения в JSON.
    
    Args:
        report: Модель заключения
        filepath: Путь к выходному файлу
        
    Returns:
        Путь к сохранённому файлу
    """
    exporter = Exporter()
    return exporter.export_report_to_json(report, filepath)

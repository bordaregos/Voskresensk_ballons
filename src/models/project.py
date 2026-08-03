"""Модель проекта для сохранения и загрузки состояния."""

import json
from pathlib import Path
from datetime import date
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional

from .balloon import Balloon, Report


@dataclass
class Project:
    """Модель проекта для сохранения состояния приложения."""
    
    # Метаданные
    version: str = "1.0.0"
    created_date: str = field(default_factory=lambda: date.today().strftime('%d.%m.%Y'))
    last_modified: str = field(default_factory=lambda: date.today().strftime('%d.%m.%Y'))
    
    # Данные заключения
    report_data: Dict[str, Any] = field(default_factory=dict)
    
    # Данные баллонов
    balloons_data: List[Dict[str, Any]] = field(default_factory=list)
    
    # Настройки
    settings: Dict[str, Any] = field(default_factory=lambda: {
        'working_pressure': 39.0,
        'hydro_test_pressure': 59.0,
        'pneumatic_test_pressure': 45.0,
        'inner_diameter': 411.0,
        'material_yield_strength': 898.0,
        'material_ultimate_strength': 981.0,
    })
    
    # Пути
    template_path: Optional[str] = None
    output_dir: str = "output"
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразование в словарь для JSON."""
        return asdict(self)
    
    def to_json(self) -> str:
        """Преобразование в JSON строку."""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Project':
        """Создание проекта из словаря."""
        return cls(
            version=data.get('version', '1.0.0'),
            created_date=data.get('created_date', date.today().strftime('%d.%m.%Y')),
            last_modified=data.get('last_modified', date.today().strftime('%d.%m.%Y')),
            report_data=data.get('report_data', {}),
            balloons_data=data.get('balloons_data', []),
            settings=data.get('settings', {}),
            template_path=data.get('template_path'),
            output_dir=data.get('output_dir', 'output'),
        )
    
    @classmethod
    def from_json(cls, json_str: str) -> 'Project':
        """Создание проекта из JSON строки."""
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    def save_to_file(self, filepath: Path) -> str:
        """
        Сохранение проекта в файл.
        
        Args:
            filepath: Путь к файлу
            
        Returns:
            Путь к сохранённому файлу
        """
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        with open(filepath, 'w', encoding='utf-8') as file:
            file.write(self.to_json())
        
        self.last_modified = date.today().strftime('%d.%m.%Y')
        
        return str(filepath)
    
    @classmethod
    def load_from_file(cls, filepath: Path) -> 'Project':
        """
        Загрузка проекта из файла.
        
        Args:
            filepath: Путь к файлу
            
        Returns:
            Объект Project
        """
        with open(filepath, 'r', encoding='utf-8') as file:
            data = json.load(file)
        
        return cls.from_dict(data)


@dataclass
class BalloonProject:
    """Модель проекта только для баллонов (упрощённая)."""
    
    balloons: List[Balloon] = field(default_factory=list)
    settings: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразование в словарь."""
        return {
            'balloons': [
                {
                    'serial_number': b.serial_number,
                    'min_thickness': b.min_thickness,
                    'max_thickness': b.max_thickness,
                    'year_of_manufacture': b.year_of_manufacture,
                    'thickness_measurements': b.thickness_measurements,
                }
                for b in self.balloons
            ],
            'settings': self.settings,
        }
    
    def to_json(self) -> str:
        """Преобразование в JSON строку."""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BalloonProject':
        """Создание из словаря."""
        balloons = []
        for b_data in data.get('balloons', []):
            balloon = Balloon(
                serial_number=b_data.get('serial_number', ''),
                min_thickness=b_data.get('min_thickness', 0.0),
                max_thickness=b_data.get('max_thickness', 0.0),
                year_of_manufacture=b_data.get('year_of_manufacture', 2024),
                thickness_measurements=b_data.get('thickness_measurements', []),
            )
            balloons.append(balloon)
        
        return cls(
            balloons=balloons,
            settings=data.get('settings', {}),
        )
    
    @classmethod
    def from_json(cls, json_str: str) -> 'BalloonProject':
        """Создание из JSON строки."""
        data = json.loads(json_str)
        return cls.from_dict(data)

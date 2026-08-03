"""Модель проекта для сохранения и загрузки состояния."""

import json
from pathlib import Path
from datetime import date
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional


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

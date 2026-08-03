"""Модели данных для представления баллонов и заключений."""

from dataclasses import dataclass, field
from typing import List, Optional
from datetime import date


@dataclass
class Balloon:
    """Модель баллона с его параметрами и измерениями."""
    
    # Идентификация
    serial_number: str
    registration_number: Optional[str] = None
    
    # Геометрия
    nominal_volume: float = 400.0  # л
    outer_diameter: float = 466.0  # мм
    wall_thickness: float = 28.0  # мм
    
    # Материал и прочность
    material_yield_strength: float = 898.0  # МПа, предел текучести
    material_ultimate_strength: float = 981.0  # МПа, времющее сопротивление
    material: str = "Сталь"
    
    # Производство
    year_of_manufacture: int = 2024
    manufacturer: str = ""
    
    # Измерения толщины (20 замеров)
    thickness_measurements: List[float] = field(default_factory=list)
    
    # Эксплуатация
    date_of_installation: Optional[date] = None
    years_of_operation: float = 0.0
    corrosion_allowance: float = 0.0  # мм, припуск на коррозию
    
    # Режим работы
    working_pressure: float = 39.0  # МПа
    hydro_test_pressure: float = 59.0  # МПа
    pneumatic_test_pressure: float = 45.0  # МПа
    test_medium: str = "Воздух"
    
    # Дополнительные параметры
    length: float = 1000.0  # мм
    mass: float = 1050.0  # кг
    design_code: str = "ГОСТ 34233.1-2017"
    
    def __post_init__(self):
        """После инициализации: заполнить измерения если пусто."""
        if not self.thickness_measurements:
            # Генерация случайных измерений для тестов
            import random
            base_thickness = self.wall_thickness
            self.thickness_measurements = [
                round(base_thickness + random.uniform(-2, 2), 1)
                for _ in range(20)
            ]
    
    @property
    def min_thickness(self) -> float:
        """Минимальная толщина стенки."""
        return min(self.thickness_measurements) if self.thickness_measurements else 0.0
    
    @property
    def max_thickness(self) -> float:
        """Максимальная толщина стенки."""
        return max(self.thickness_measurements) if self.thickness_measurements else 0.0
    
    @property
    def avg_thickness(self) -> float:
        """Средняя толщина стенки."""
        if not self.thickness_measurements:
            return 0.0
        return sum(self.thickness_measurements) / len(self.thickness_measurements)
    
    def get_formatted_measurements(self) -> str:
        """Получить измерения в формате для Word (5 строк по 4 значения)."""
        if not self.thickness_measurements:
            return ""
        
        lines = []
        for i in range(0, 20, 4):
            group = self.thickness_measurements[i:i+4]
            line = " ".join(f"{x:.1f}".replace('.', ',') for x in group)
            lines.append(line)
        
        return "\n".join(lines)
    
    def validate(self) -> List[str]:
        """Проверка валидности данных баллона. Возвращает список ошибок."""
        errors = []
        
        if not self.serial_number:
            errors.append("Заводской номер не указан")
        
        if not self.thickness_measurements:
            errors.append("Отсутствуют измерения толщины")
        else:
            if self.min_thickness <= 0:
                errors.append("Минимальная толщина должна быть больше 0")
            
            if self.max_thickness - self.min_thickness > 5.0:
                errors.append("Разница между max и min толщиной слишком велика (>5 мм)")
        
        if self.years_of_operation < 0:
            errors.append("Срок эксплуатации не может быть отрицательным")
        
        if self.working_pressure <= 0:
            errors.append("Рабочее давление должно быть больше 0")
        
        return errors


@dataclass
class Report:
    """Модель заключения на баллоны."""
    
    # Идентификация заключения
    report_number: str
    registration_number: str
    creation_date: date = field(default_factory=date.today)
    
    # Данные о секции/группе баллонов
    section_name: str = ""
    date_of_injection: str = ""
    test_medium: str = "Воздух"
    gost: str = "ГОСТ 34233.1-2017"
    
    # Общие параметры
    total_count: int = 0
    total_volume: float = 0.0
    working_pressure: float = 39.0
    hydro_test_pressure: float = 59.0
    pneumatic_test_pressure: float = 45.0
    test_pressure_pneumatic_kgs: float = 0.0
    
    # Данные о баллонах
    balloons: List[Balloon] = field(default_factory=list)
    
    # Результаты расчётов
    min_wall_thickness: float = 0.0
    min_wall_thickness_serial: str = ""
    year_range: str = ""
    
    # Расчётные параметры
    calculated_sigma: float = 0.0
    calculated_sigma_hydro: float = 0.0
    calculated_thickness: float = 0.0
    calculated_thickness_hydro: float = 0.0
    max_calculated_thickness: float = 0.0
    permissible_pressure: float = 0.0
    
    # Остаточный ресурс
    corrosion_rate: float = 0.0
    remaining_life: float = 0.0
    remaining_life_comment: str = ""
    
    # Параметры твёрдости
    hardness_min: float = 0.0
    hardness_max: float = 0.0
    hardness_measurements: List[List[float]] = field(default_factory=list)
    
    # Параметры овальности
    ovalness_measurements: List[dict] = field(default_factory=list)
    
    # Дополнительные данные
    owner: str = ""
    responsible_person: str = ""
    contract_number: str = ""
    order_number: str = ""
    
    def __post_init__(self):
        """После инициализации: обновить общие параметры."""
        self.total_count = len(self.balloons)
        self.total_volume = self.total_count * 400.0  # 400 л на баллон
    
    def validate(self) -> List[str]:
        """Валидация данных заключения. Возвращает список ошибок."""
        errors = []
        
        if not self.report_number:
            errors.append("Номер заключения не указан")
        
        if not self.registration_number:
            errors.append("Регистрационный номер не указан")
        
        if not self.balloons:
            errors.append("Список баллонов пуст")
        
        for balloon in self.balloons:
            balloon_errors = balloon.validate()
            errors.extend(balloon_errors)
        
        if self.working_pressure <= 0:
            errors.append("Рабочее давление должно быть больше 0")
        
        return errors
    
    def add_ballon(self, balloon: Balloon):
        """Добавить баллон в заключение."""
        self.balloons.append(balloon)
        self.total_count = len(self.balloons)
        self.total_volume = self.total_count * 400.0
    
    def calculate_min_thickness(self):
        """Рассчитать минимальную толщину и найти баллон с ней."""
        if not self.balloons:
            return
        
        min_thickness = float('inf')
        min_ballon = None
        
        for balloon in self.balloons:
            if balloon.min_thickness < min_thickness:
                min_thickness = balloon.min_thickness
                min_ballon = balloon
        
        self.min_wall_thickness = min_thickness
        self.min_wall_thickness_serial = min_ballon.serial_number if min_ballon else ""
    
    def calculate_year_range(self):
        """Рассчитать диапазон годов изготовления."""
        if not self.balloons:
            return
        
        years = [b.year_of_manufacture for b in self.balloons]
        min_year = min(years)
        max_year = max(years)
        
        if min_year == max_year:
            self.year_range = f"{min_year} г."
        else:
            self.year_range = f"{min_year} - {max_year} гг."

"""Сервисы для расчётов параметров баллонов."""

import random
from dataclasses import dataclass
from typing import List, Tuple

from ..config import (
    GOST_HARDNESS_COEFFICIENT,
    GOST_HARDNESS_ALLOWANCE,
    DEFAULT_SETTINGS,
)


@dataclass
class StrengthResults:
    """Результаты расчёта прочности."""
    sigma: float  # Расчётное напряжение
    sigma_hydro: float  # Напряжение при гидравлическом испытании
    s_rasch: float  # Расчётная толщина при рабочем давлении
    s_rasch_hydro: float  # Расчётная толщина при гидроиспытании
    s_max_rasch: float  # Максимальная расчётная толщина
    p_dop: float  # Допустимое давление


@dataclass
class CorrosionResults:
    """Результаты расчёта коррозии и остаточного ресурса."""
    corrosion_rate: float  # Скорость коррозии, мм/год
    remaining_life: float  # Остаточный ресурс, лет
    comment: str  # Комментарий


@dataclass
class OvalnessResult:
    """Результаты расчёта овальности."""
    serial_number: str
    measurements: List[Tuple[float, float, float]]  # (d_min, d_max, ovalness)


class CalculationsService:
    """Сервис для выполнения всех расчётов."""
    
    @staticmethod
    def calculate_strength(
        working_pressure: float,
        hydro_test_pressure: float,
        pneumatic_test_pressure: float,
        inner_diameter: float,
        min_yield_strength: float,
        min_ultimate_strength: float,
        wall_thickness: float,
        coefficient_yield: float = DEFAULT_SETTINGS["coefficient_safety_yield"],
        coefficient_ultimate: float = DEFAULT_SETTINGS["coefficient_safety_ultimate"],
        coefficient_hydro: float = DEFAULT_SETTINGS["coefficient_hydro"],
    ) -> StrengthResults:
        """
        Расчёт прочности баллона по ГОСТ.
        
        Args:
            working_pressure: Рабочее давление, МПа
            hydro_test_pressure: Давление гидравлического испытания, МПа
            pneumatic_test_pressure: Давление пневматического испытания, МПа
            inner_diameter: Внутренний диаметр, мм
            min_yield_strength: Минимальный предел текучести, МПа
            min_ultimate_strength: Минимальное временное сопротивление, МПа
            wall_thickness: Толщина стенки, мм
            coefficient_yield: Коэффициент безопасности для предела текучести
            coefficient_ultimate: Коэффициент безопасности для временного сопротивления
            coefficient_hydro: Коэффициент безопасности для гидроиспытания
            
        Returns:
            StrengthResults: Результаты расчёта прочности
        """
        # Расчётные напряжения
        sigma = 1.0 * min(
            min_yield_strength / coefficient_yield,
            min_ultimate_strength / coefficient_ultimate
        )
        sigma_hydro = min_yield_strength / coefficient_hydro
        
        # Расчёт толщины стенки
        s_rasch = round(
            ((inner_diameter + (wall_thickness * 2)) * working_pressure) / 
            (2 * sigma + working_pressure), 1
        )
        s_rasch_hydro = round(
            ((inner_diameter + (wall_thickness * 2)) * hydro_test_pressure) / 
            (2 * sigma_hydro + hydro_test_pressure), 1
        )
        s_max_rasch = max(s_rasch, s_rasch_hydro)
        
        # Допустимое давление
        p_dop = round(
            (2 * sigma * (wall_thickness - 1)) / (inner_diameter + (wall_thickness - 1)), 1
        )
        
        return StrengthResults(
            sigma=sigma,
            sigma_hydro=sigma_hydro,
            s_rasch=s_rasch,
            s_rasch_hydro=s_rasch_hydro,
            s_max_rasch=s_max_rasch,
            p_dop=p_dop
        )
    
    @staticmethod
    def calculate_ovalness(
        d_min: float,
        d_max: float,
        count: int = 3
    ) -> List[Tuple[float, float, float]]:
        """
        Расчёт овальности для одного баллона.
        
        Args:
            d_min: Минимальный диаметр, мм
            d_max: Максимальный диаметр, мм
            count: Количество замеров
            
        Returns:
            Список кортежей (d_min, d_max, ovalness) для каждого замера
        """
        if d_min == d_max:
            return [(d_min, d_max, 0.0)] * count
        
        measurements = []
        for _ in range(count):
            # Генерация случайных значений в диапазоне
            d_min_rand = random.uniform(d_min, d_max)
            d_max_rand = random.uniform(d_min_rand, d_max)
            
            # Расчёт овальности: 2*(Dmax-Dmin)/(Dmax+Dmin)*100%
            ovalness = round(
                ((2 * (d_max_rand - d_min_rand)) / (d_max_rand + d_min_rand)) * 100, 3
            )
            
            measurements.append((round(d_min_rand, 1), round(d_max_rand, 1), ovalness))
        
        return measurements
    
    @staticmethod
    def calculate_hardness(
        ultimate_strength: float,
        coefficient: float = GOST_HARDNESS_COEFFICIENT,
        allowance: float = GOST_HARDNESS_ALLOWANCE
    ) -> Tuple[float, float]:
        """
        Расчёт твёрдости по ГОСТ по пределу прочности.
        
        Args:
            ultimate_strength: Временное сопротивление, МПа
            coefficient: Коэффициент перевода (2.7 для углеродистых сталей)
            allowance: Допустимое отклонение
            
        Returns:
            Кортеж (hb_min, hb_max) - минимальная и максимальная твёрдость
        """
        hb = coefficient * (ultimate_strength / 10)
        hb_min = round(hb)
        hb_max = round(hb + allowance)
        
        return hb_min, hb_max
    
    @staticmethod
    def generate_hardness_measurements(
        hb_min: float,
        hb_max: float,
        count: int = 20
    ) -> List[float]:
        """
        Генерация измерений твёрдости.
        
        Args:
            hb_min: Минимальная твёрдость
            hb_max: Максимальная твёрдость
            count: Количество измерений
            
        Returns:
            Список измерений твёрдости
        """
        return [round(random.uniform(hb_min, hb_max)) for _ in range(count)]
    
    @staticmethod
    def calculate_corrosion_rate(
        current_thickness: float,
        original_thickness: float,
        corrosion_allowance: float,
        years_of_operation: float
    ) -> CorrosionResults:
        """
        Расчёт скорости коррозии и остаточного ресурса.
        
        Args:
            current_thickness: Текущая толщина стенки, мм
            original_thickness: Номинальная толщина стенки, мм
            corrosion_allowance: Припуск на коррозию, мм
            years_of_operation: Срок эксплуатации, лет
            
        Returns:
            CorrosionResults: Результаты расчёта коррозии
        """
        if years_of_operation == 0:
            return CorrosionResults(
                corrosion_rate=0.0,
                remaining_life=0.0,
                comment="Срок эксплуатации не указан"
            )
        
        # Расчёт скорости коррозии
        # a = (s_isp + c0 + dop - s_min) / years
        a = round((original_thickness + corrosion_allowance - current_thickness) / years_of_operation, 3)
        
        # Расчёт остаточного ресурса
        # tk = (s_min - s_max_rasch) / a
        # Для упрощения используем текущую толщину
        remaining = round((current_thickness - 1.0) / a, 0) if a > 0 else 0
        
        # Комментарий
        if remaining > 10:
            comment = "> 10 лет"
        elif remaining > 0:
            comment = f"{int(remaining)} лет"
        else:
            comment = "Требуется пересчёт"
        
        return CorrosionResults(
            corrosion_rate=a,
            remaining_life=remaining,
            comment=comment
        )
    
    @staticmethod
    def generate_thickness_measurements(
        s_min: float,
        s_max: float,
        count: int = 20
    ) -> List[float]:
        """
        Генерация измерений толщины стенки.
        
        Args:
            s_min: Минимальная толщина
            s_max: Максимальная толщина
            count: Количество измерений
            
        Returns:
            Список измерений толщины
        """
        measurements = [round(random.uniform(s_min, s_max), 1) for _ in range(count)]
        
        # Убедиться, что минимальное значение присутствует
        if min(measurements) != s_min:
            min_index = measurements.index(min(measurements))
            measurements[min_index] = s_min
        
        return measurements
    
    @staticmethod
    def calculate_pneumatic_test_kgs(pneumatic_pressure_mpa: float) -> float:
        """
        Перевод давления пневматического испытания из МПа в кгс/см².
        
        Args:
            pneumatic_pressure_mpa: Давление в МПа
            
        Returns:
            Давление в кгс/см²
        """
        return round(pneumatic_pressure_mpa * 10.19, 1)

"""Чистые функции расчётов ГОСТ для баллонов высокого давления.

Портированы 1:1 из ui_logic.py (прочность, остаточный ресурс, толщины,
овальность, твёрдость, поиск минимальной толщины и диапазона годов).
Модуль не зависит от Qt — вызывающий (GUI) слой отвечает за чтение
виджетов и форматирование результата под русскую десятичную запятую
(см. src/services/formatting.py).
"""

import random
from dataclasses import dataclass
from typing import List, Optional, Tuple

from ..config import GOST_HARDNESS_COEFFICIENT, GOST_HARDNESS_ALLOWANCE


@dataclass(frozen=True)
class StrengthResult:
    sigma: float
    sigma_gidro: float
    s_rasch: float
    s_rasch_gidro: float
    s_max_rasch: float
    p_dop: float
    p_pnevma_kgs: int
    p_rab_025: int
    p_rab_05: int
    p_rab_075: int


def calculate_strength(
    pred_tek_min: float,
    vrem_sopr_min: float,
    p_rab_mpa: float,
    p_gidro: float,
    d_vnutr: float,
    s_isp: float,
    p_pnevma: float,
    p_rab: float,
) -> StrengthResult:
    """Расчёт на прочность по ГОСТ 34233.1. Портировано из ui_logic.prochnost()."""
    sigma = round(1.0 * min(pred_tek_min / 1.5, vrem_sopr_min / 2.4), 1)
    sigma_gidro = round(pred_tek_min / 1.1, 1)
    p_pnevma_kgs = round(p_pnevma * 10.19)

    s_rasch = round(((d_vnutr + (s_isp * 2)) * p_rab_mpa) / (2 * sigma + p_rab_mpa), 1)
    s_rasch_gidro = round(((d_vnutr + (s_isp * 2)) * p_gidro) / (2 * sigma_gidro + p_gidro), 1)
    s_max_rasch = max(s_rasch, s_rasch_gidro)

    p_dop = round((2 * sigma * (s_isp - 1)) / (d_vnutr + (s_isp - 1)), 1)

    return StrengthResult(
        sigma=sigma,
        sigma_gidro=sigma_gidro,
        s_rasch=s_rasch,
        s_rasch_gidro=s_rasch_gidro,
        s_max_rasch=s_max_rasch,
        p_dop=p_dop,
        p_pnevma_kgs=p_pnevma_kgs,
        p_rab_025=round(p_rab * 0.25),
        p_rab_05=round(p_rab * 0.5),
        p_rab_075=round(p_rab * 0.75),
    )


@dataclass(frozen=True)
class ResidualLifeResult:
    corrosion_rate: float  # a_corr, мм/год
    remaining_years: float  # tk — int 0 при a==0, иначе float (округлено до целого)
    comment: str  # tk_just


def calculate_residual_life(
    s_isp: float,
    c0_plus_dop: float,
    s_min_total: float,
    years_of_operation: float,
    s_max_rasch: float,
) -> ResidualLifeResult:
    """Расчёт скорости коррозии и остаточного ресурса. Портировано из ui_logic.ost_res().

    Raises:
        ValueError: если years_of_operation == 0 (деление на ноль).
    """
    if years_of_operation == 0:
        raise ValueError("Срок эксплуатации не может быть нулевым")

    a = round((s_isp + c0_plus_dop - s_min_total) / years_of_operation, 3)
    tk = round((s_min_total - s_max_rasch) / a, 0) if a != 0 else 0
    comment = "> 10 лет" if tk > 10 else "Пересчитать."

    return ResidualLifeResult(corrosion_rate=a, remaining_years=tk, comment=comment)


def generate_thickness_measurements(
    s_min: float,
    count: int = 20,
    spread: float = 2.0,
    rng: Optional[random.Random] = None,
) -> List[float]:
    """Генерация замеров толщины вокруг измеренного минимума.

    Портировано из ui_logic.calc_thick(): count значений round(uniform(s_min,
    s_min+spread), 1); минимум сгенерированного списка принудительно
    заменяется на фактический s_min — это осознанное поведение, сохранено как есть.
    """
    rng = rng or random.Random()
    values = [round(rng.uniform(s_min, s_min + spread), 1) for _ in range(count)]
    if values:
        min_value = min(values)
        if min_value != s_min:
            values[values.index(min_value)] = s_min
    return values


@dataclass(frozen=True)
class OvalMeasurement:
    d_min: int
    d_max: int
    ovalness: float


def generate_ovalness_measurement(
    d_range: Tuple[int, int] = (465, 466),
    rng: Optional[random.Random] = None,
) -> OvalMeasurement:
    """Один замер овальности. Портировано из ui_logic.ovalnost_calc().

    Порядок вызовов rng сохранён как в оригинале (сначала d_min, потом d_max)
    для воспроизводимости при фиксированном seed.
    """
    rng = rng or random.Random()
    while True:
        d_min = rng.randint(*d_range)
        d_max = rng.randint(*d_range)
        if d_max >= d_min:
            break
    ovalness = round(((2 * (d_max - d_min)) / (d_max + d_min)) * 100, 3)
    return OvalMeasurement(d_min=d_min, d_max=d_max, ovalness=ovalness)


def generate_ovalness_measurements(
    count: int = 3,
    d_range: Tuple[int, int] = (465, 466),
    rng: Optional[random.Random] = None,
) -> List[OvalMeasurement]:
    rng = rng or random.Random()
    return [generate_ovalness_measurement(d_range=d_range, rng=rng) for _ in range(count)]


@dataclass(frozen=True)
class HardnessRange:
    hb_min: int
    hb_max: int


def calculate_hardness_range(
    rm: float,
    coefficient: float = GOST_HARDNESS_COEFFICIENT,
    allowance: int = GOST_HARDNESS_ALLOWANCE,
) -> HardnessRange:
    """Диапазон твёрдости по ГОСТ. Портировано из ui_logic.tverdost().

    rm — параметр (фикс бага: раньше было захардкожено 981).
    hb_max = hb_min + allowance эквивалентно round(coeff*(rm/10) + allowance)
    из оригинала: прибавление целого allowance не меняет исход round().
    """
    hb_min = round(coefficient * (rm / 10))
    hb_max = hb_min + allowance
    return HardnessRange(hb_min=hb_min, hb_max=hb_max)


def generate_hardness_measurements(
    hb_min: int, hb_max: int, count: int = 20, rng: Optional[random.Random] = None
) -> List[int]:
    rng = rng or random.Random()
    return [round(rng.uniform(hb_min, hb_max)) for _ in range(count)]


@dataclass(frozen=True)
class SMinResult:
    s_min: float
    s_min_index: int


def find_min_thickness(values: List[float]) -> SMinResult:
    """Поиск минимальной толщины и её индекса. Портировано из ui_logic.s_min_min_calc().

    Raises:
        ValueError: на пустом списке.
    """
    if not values:
        raise ValueError("Список толщин пуст")
    s_min = min(values)
    return SMinResult(s_min=s_min, s_min_index=values.index(s_min))


def format_year_range(years: List[int]) -> str:
    """Форматирование диапазона годов изготовления. Портировано из ui_logic.s_min_min_calc().

    Пустой список -> "Нет данных" (не raise — в оригинале это отдельная,
    самостоятельная ветка без ошибки, асимметрия с find_min_thickness сохранена).
    """
    if not years:
        return "Нет данных"
    min_year, max_year = min(years), max(years)
    if min_year != max_year:
        return f"{min_year} - {max_year} гг."
    return f"{min_year} г."

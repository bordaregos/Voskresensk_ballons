"""Чистые функции расчётов ГОСТ 32388-2013 для технологических трубопроводов.

Модуль не зависит от Qt, по образцу src/services/calculations.py (баллоны).
Опорный пример для формул и тестов — реальный отчёт по техническому
диагностированию трубопровода TD_720291_otd_214_1.docx (труба 8,0х2,0 мм,
сталь 12Х18Н10Т, Pр=68,6 МПа, [σ]=147 МПа, φ=1,0, C2=0,2 мм, Sф=1,99 мм,
Sн=2,0 мм, 52 года эксплуатации).

В документе часть формул дана обычным текстом, часть — встроенными
объектами MS Equation (WMF/EMF), не читаемыми доступными в этом окружении
инструментами конвертации. Там, где текста не было, формула восстановлена
алгебраически или по порядку переменных, перечисленных в тексте рядом с
формулой, и сверена с документом там, где это было возможно — см.
докстринги ниже и tests/test_calculations_pipeline.py.
"""

import random
from dataclasses import dataclass
from typing import Dict, List, Optional

# Допускаемое напряжение [σ] по марке стали и температуре, МПа.
# Подтверждена только одна точка из TD_720291_otd_214_1.docx
# (12Х18Н10Т, +20°C -> 147). Дополнительные марки/температуры добавляются
# сюда по мере появления новых объектов трубопроводов.
ALLOWABLE_STRESS_TABLE: Dict[str, Dict[float, float]] = {
    "12Х18Н10Т": {20.0: 147.0},
}


def get_allowable_stress(steel_grade: str, temperature_c: float) -> float:
    """[σ] по марке стали и температуре, линейная интерполяция между табличными точками.

    Raises:
        KeyError: неизвестная марка стали.
        ValueError: температура вне табличного диапазона (в т.ч. когда для
            марки известна только одна точка и температура ей не равна —
            интерполировать не из чего).
    """
    table = ALLOWABLE_STRESS_TABLE.get(steel_grade)
    if table is None:
        raise KeyError(f"Неизвестная марка стали: {steel_grade}")

    points = sorted(table.items())
    if len(points) == 1:
        only_temp, only_value = points[0]
        if temperature_c != only_temp:
            raise ValueError(
                f"Для марки {steel_grade} известна только точка {only_temp}°C — "
                f"для {temperature_c}°C нужна вторая табличная точка."
            )
        return only_value

    if temperature_c < points[0][0] or temperature_c > points[-1][0]:
        raise ValueError(f"Температура {temperature_c}°C вне табличного диапазона для {steel_grade}")

    for (t1, s1), (t2, s2) in zip(points, points[1:]):
        if t1 <= temperature_c <= t2:
            if t1 == t2:
                return s1
            fraction = (temperature_c - t1) / (t2 - t1)
            return round(s1 + fraction * (s2 - s1), 1)

    raise ValueError(f"Не удалось интерполировать [σ] для {steel_grade} при {temperature_c}°C")


@dataclass(frozen=True)
class PipelineStrengthResult:
    s_calc: float    # Sr, расчётная толщина стенки прямой трубы, мм
    s_reject: float  # [S] = Sr + C2, минимально допустимая (отбраковочная) толщина, мм
    p_allow: float   # [P], допускаемое давление, МПа
    strength_ok: bool  # условие прочности: Sф >= [S] и [P] >= Pр


def calculate_pipeline_strength(
    p_working: float,
    d_outer: float,
    allowable_stress: float,
    s_actual: float,
    c2: float,
    phi: float = 1.0,
) -> PipelineStrengthResult:
    """Поверочный расчёт на прочность прямой трубы по ГОСТ 32388-2013.

    `[P] = (2·φ·[σ]·(Sф - C2)) / (Da - (Sф - C2))` — дана в документе-примере
    текстом дословно, взята как есть.

    `Sr` в документе была картинкой формулы (не текстом) — восстановлена
    алгебраически как решение формулы `[P]` относительно `S` при `P=Pр`,
    `C2=0`: `Sr = (Pр·Da) / (2·φ·[σ] + Pр)`. На контрольном примере даёт
    1,51 мм — точное совпадение с документом.

    Проверка `[P]` на контрольном примере (147, 1,99, 8,0, 0,2, φ=1) даёт
    84,74 МПа против 85,35 МПа в документе (~0,7% расхождение) — вероятно,
    исходные величины в документе показаны с округлением до отображаемых
    разрядов, а расчёт в оригинале шёл по более точным непоказанным
    значениям. Формула не корректировалась под точное совпадение цифры,
    так как дана в тексте документа дословно, а не восстановлена.
    """
    s_calc = round((p_working * d_outer) / (2 * phi * allowable_stress + p_working), 2)
    s_reject = round(s_calc + c2, 2)
    p_allow = round(
        (2 * phi * allowable_stress * (s_actual - c2)) / (d_outer - (s_actual - c2)), 2
    )
    strength_ok = s_actual >= s_reject and p_allow >= p_working
    return PipelineStrengthResult(
        s_calc=s_calc, s_reject=s_reject, p_allow=p_allow, strength_ok=strength_ok
    )


@dataclass(frozen=True)
class PipelineResidualLifeResult:
    corrosion_rate: float  # Аф, мм/год
    remaining_years: float  # Тост, лет
    comment: str


def calculate_pipeline_residual_life(
    s_nominal: float,
    s_actual: float,
    s_reject: float,
    years_of_operation: float,
    k: float = 1.0,
    c0_fraction: float = 0.4,
) -> PipelineResidualLifeResult:
    """Скорость коррозии и остаточный ресурс трубопровода.

    `Аф = (Sи + C0 - Sф) / t`, `C0 = c0_fraction·Sи` — обе формулы в
    документе были картинками, восстановлены по порядку переменных,
    перечисленных в тексте рядом с формулой (Sи, C0, Sф, t). На контрольном
    примере (Sи=2,0, Sф=1,99, t=52 года) даёт Аф≈0,0156 мм/год.

    `Тост = k·(Sф - Sотб) / Аф`, `Sотб = [S]` — дана в документе текстом.
    При k=1,0 контрольный пример даёт Тост≈18 лет, что согласуется с
    выводом документа «остаточный ресурс более 10 лет» — в отличие от Sr
    (см. calculate_pipeline_strength), в документе нет точной цифры Тост
    для сверки, только качественный вывод, так что это самосогласованная,
    а не дословно подтверждённая проверка.

    k — коэффициент, зависящий от категории трубопровода и срока службы
    без замены (методика Госгортехнадзора, письмо № 02-35/327 от
    24.07.1996). Точная таблица значений k не найдена в открытом доступе;
    k=1.0 — задокументированное рабочее допущение, дающее результат,
    согласующийся с выводом примера. Скорректировать при появлении
    официальной методики.

    Raises:
        ValueError: если years_of_operation == 0 (деление на ноль).
    """
    if years_of_operation == 0:
        raise ValueError("Срок эксплуатации не может быть нулевым")

    c0 = c0_fraction * s_nominal
    corrosion_rate = round((s_nominal + c0 - s_actual) / years_of_operation, 4)
    remaining_years = (
        round(k * (s_actual - s_reject) / corrosion_rate, 0) if corrosion_rate != 0 else 0
    )
    comment = "> 10 лет" if remaining_years > 10 else "Пересчитать."

    return PipelineResidualLifeResult(
        corrosion_rate=corrosion_rate, remaining_years=remaining_years, comment=comment
    )


@dataclass(frozen=True)
class SegmentSpec:
    number: int
    element_type: str  # "прямой участок" | "отвод"
    size: str           # типоразмер, например "8,0х2,0"


@dataclass(frozen=True)
class SegmentMeasurement:
    number: int
    element_type: str
    size: str
    thickness: float


def generate_pipeline_thickness_measurements(
    segments: List[SegmentSpec],
    s_min: float,
    spread: float = 0.1,
    rng: Optional[random.Random] = None,
) -> List[SegmentMeasurement]:
    """Синтетические замеры толщины по участкам трассы трубопровода.

    По аналогии с generate_thickness_measurements() для баллонов — один
    замер round(uniform(s_min, s_min+spread), 2) на переданный участок, а
    не фиксированное число точек одного объекта. spread по умолчанию
    заметно меньше баллонного (0,1 мм против 2,0 мм) — в контрольном
    примере реальные замеры толщинометра лежат в диапазоне 1,99–2,05 мм,
    то есть отражают точность прибора, а не допуск на прокат.
    """
    rng = rng or random.Random()
    return [
        SegmentMeasurement(
            number=seg.number,
            element_type=seg.element_type,
            size=seg.size,
            thickness=round(rng.uniform(s_min, s_min + spread), 2),
        )
        for seg in segments
    ]

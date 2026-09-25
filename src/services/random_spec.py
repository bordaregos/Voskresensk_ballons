"""Параметры генератора случайных чисел для поля-плейсхолдера конструктора
документов («Создать рандом» из ПКМ на чипе, src/ui/random_editor_dialog.py).

Спецификация -- plain dict, JSON-совместимый (секция field_randoms в
data/title_variants.json, см. title_variants_store.load_field_randoms()):
    {"kind": "int" | "float", "low": float, "high": float,
     "step": float, "decimals": int}

Значение берётся из сетки low, low+step, low+2*step, ... <= high (границы
включительно, если попадают в сетку). decimals имеет смысл только для
kind == "float" -- сколько знаков после запятой показывать в результате.
"""

import random
from typing import Dict, Optional

from .formatting import format_ru, format_ru_fixed

KINDS = ("int", "float")
MAX_DECIMALS = 6


def default_random_spec() -> Dict:
    return {"kind": "int", "low": 0, "high": 100, "step": 1, "decimals": 2}


def validate_random_spec(spec: Dict) -> Optional[str]:
    """None -- спецификация корректна, иначе текст ошибки для пользователя."""
    if spec.get("kind") not in KINDS:
        return "Неизвестный тип числа."
    low, high, step = spec["low"], spec["high"], spec["step"]
    if low >= high:
        return "Нижняя граница должна быть меньше верхней."
    if step <= 0:
        return "Шаг должен быть больше нуля."
    if step > high - low:
        return "Шаг не может быть больше диапазона между границами."
    if spec["kind"] == "int":
        if any(float(v) != int(v) for v in (low, high, step)):
            return "Для целого числа границы и шаг должны быть целыми."
    elif not 0 <= spec.get("decimals", 0) <= MAX_DECIMALS:
        return f"Количество знаков после запятой — от 0 до {MAX_DECIMALS}."
    return None


def generate_random_value(spec: Dict, rng: Optional[random.Random] = None) -> str:
    """Случайное значение из сетки спецификации, уже отформатированное под
    русскую запятую (format_ru() для целых, format_ru_fixed() -- для
    вещественных). ValueError, если спецификация некорректна."""
    error = validate_random_spec(spec)
    if error:
        raise ValueError(error)
    rng = rng or random.Random()
    low, high, step = spec["low"], spec["high"], spec["step"]
    # +1e-9 -- защита от погрешности float на верхней границе (0.1 * 3 и т.п.)
    steps_count = int((high - low) / step + 1e-9)
    value = low + rng.randint(0, steps_count) * step
    if spec["kind"] == "int":
        return format_ru(int(value))
    return format_ru_fixed(value, spec["decimals"])


def format_random_bound(spec: Dict, value: float) -> str:
    """Граница диапазона для показа в реквизитах: целое -- без дробной
    части, вещественное -- с decimals знаками, обе с русской запятой."""
    if spec["kind"] == "int":
        return format_ru(int(value))
    return format_ru_fixed(value, spec["decimals"])

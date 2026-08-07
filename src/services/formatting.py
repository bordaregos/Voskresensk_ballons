"""Форматирование чисел под русскую десятичную запятую.

Два разных паттерна используются в оригинале и не взаимозаменяемы:
format_ru — "наивный" str(x).replace('.', ',') (int остаётся без запятой,
используется для большинства полей); format_ru_fixed — фиксированное
число знаков после запятой (используется только для блока толщин).
Смешение паттернов даёт видимую регрессию в готовом документе
(например p_pnevma_kgs=459 стал бы "459,0" вместо "459").
"""

from typing import List


def format_ru(value) -> str:
    """str(value).replace('.', ',') — для int запятая не добавляется."""
    return str(value).replace(".", ",")


def format_ru_fixed(value: float, ndigits: int = 1) -> str:
    """Фиксированное число знаков после запятой, с русской запятой."""
    return f"{value:.{ndigits}f}".replace(".", ",")


def parse_ru(text: str) -> float:
    """'12,5' -> 12.5. Raises ValueError как float() при некорректном вводе."""
    return float(text.replace(",", "."))


def format_thickness_block(values: List[float], per_line: int = 4) -> str:
    """Блок замеров толщины: строки по `per_line` значений, разделённые пробелом."""
    lines = []
    for i in range(0, len(values), per_line):
        group = values[i : i + per_line]
        lines.append(" ".join(format_ru_fixed(v) for v in group))
    return "\n".join(lines)

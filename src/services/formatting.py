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


def format_fio_initials(full_name: str) -> str:
    """'Грищенко Сергей Вадимович' -> 'С. В. Грищенко' -- для подписей в
    актах/протоколах (Таблица 2 "Сведения о специалистах" вводит ФИО в
    порядке Фамилия Имя Отчество; подпись печатает инициалы имени и
    отчества впереди, фамилию полностью в конце).

    Raises:
        ValueError: если full_name не состоит ровно из трёх слов.
    """
    parts = full_name.split()
    if len(parts) != 3:
        raise ValueError(
            f"Ожидается ФИО из трёх слов (Фамилия Имя Отчество): {full_name!r}"
        )
    surname, first, patronymic = parts
    return f"{first[0]}. {patronymic[0]}. {surname}"


_ONES = [
    "ноль", "один", "два", "три", "четыре", "пять", "шесть", "семь", "восемь", "девять",
]
_TEENS = [
    "десять", "одиннадцать", "двенадцать", "тринадцать", "четырнадцать",
    "пятнадцать", "шестнадцать", "семнадцать", "восемнадцать", "девятнадцать",
]
_TENS = [
    "", "", "двадцать", "тридцать", "сорок", "пятьдесят",
    "шестьдесят", "семьдесят", "восемьдесят", "девяносто",
]
_HUNDREDS = [
    "", "сто", "двести", "триста", "четыреста", "пятьсот",
    "шестьсот", "семьсот", "восемьсот", "девятьсот",
]


def number_to_words_ru(n: int) -> str:
    """Целое число прописью (именительный падеж, мужской род) -- для
    пояснения срока в годах в скобках рядом с цифрой: "5 (пять) лет".

    Raises:
        ValueError: для отрицательных чисел или чисел от 1000 и выше --
        за пределами реалистичного диапазона срока эксплуатации.
    """
    if not (0 <= n < 1000):
        raise ValueError(f"Ожидается число от 0 до 999: {n!r}")
    if n < 10:
        return _ONES[n]
    if n < 20:
        return _TEENS[n - 10]

    words = []
    hundreds, remainder = divmod(n, 100)
    if hundreds:
        words.append(_HUNDREDS[hundreds])
    if remainder >= 20:
        tens, ones = divmod(remainder, 10)
        words.append(_TENS[tens])
        if ones:
            words.append(_ONES[ones])
    elif remainder >= 10:
        words.append(_TEENS[remainder - 10])
    elif remainder:
        words.append(_ONES[remainder])
    return " ".join(words)

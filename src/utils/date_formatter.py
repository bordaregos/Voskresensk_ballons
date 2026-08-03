"""Форматирование дат и времени."""

from typing import Optional
from datetime import datetime


# Словарь с правильными склонениями месяцев
MONTH_NAMES = {
    1: "января", 2: "февраля", 3: "марта",
    4: "апреля", 5: "мая", 6: "июня",
    7: "июля", 8: "августа", 9: "сентября",
    10: "октября", 11: "ноября", 12: "декабря"
}


def format_russian_date(date_str: str) -> Optional[str]:
    """
    Форматирование даты в русский формат: "ДД ММММ ГГГГг.".
    
    Args:
        date_str: Дата в формате ДД.ММ.ГГГГ
        
    Returns:
        Отформатированная дата или None при ошибке
    """
    try:
        day, month, year = map(int, date_str.split('.'))
        
        if month not in MONTH_NAMES:
            return None
        
        return f'"{day}" {MONTH_NAMES[month]} {year}г.'
    except (ValueError, KeyError):
        return None


def format_date_to_string(date_obj: datetime, format_type: str = "short") -> str:
    """
    Форматирование объекта datetime в строку.
    
    Args:
        date_obj: Объект datetime
        format_type: Тип формата:
            - "short": ДД.ММ.ГГГГ
            - "long": ДД ММММ ГГГГг.
            - "iso": ГГГГ-ММ-ДД
            
    Returns:
        Отформатированная дата
    """
    if format_type == "short":
        return date_obj.strftime("%d.%m.%Y")
    elif format_type == "long":
        day = date_obj.day
        month = date_obj.month
        year = date_obj.year
        
        if month not in MONTH_NAMES:
            return date_obj.strftime("%d.%m.%Y")
        
        return f'"{day}" {MONTH_NAMES[month]} {year}г.'
    elif format_type == "iso":
        return date_obj.strftime("%Y-%m-%d")
    else:
        return date_obj.strftime("%d.%m.%Y")


def parse_date_from_string(date_str: str) -> Optional[datetime]:
    """
    Парсинг даты из строки.
    
    Args:
        date_str: Дата в формате ДД.ММ.ГГГГ
        
    Returns:
        Объект datetime или None при ошибке
    """
    try:
        return datetime.strptime(date_str, "%d.%m.%Y")
    except ValueError:
        return None


def get_current_date_string() -> str:
    """
    Получение текущей даты в формате ДД.ММ.ГГГГ.
    
    Returns:
        Текущая дата как строка
    """
    return datetime.now().strftime("%d.%m.%Y")


def get_current_date_russian() -> str:
    """
    Получение текущей даты в русском формате.
    
    Returns:
        Текущая дата в формате "ДД ММММ ГГГГг."
    """
    now = datetime.now()
    day = now.day
    month = now.month
    year = now.year
    
    if month not in MONTH_NAMES:
        return f'"{day}" {month} {year}г.'
    
    return f'"{day}" {MONTH_NAMES[month]} {year}г.'

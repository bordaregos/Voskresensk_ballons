"""Валидация входных данных."""

import re
from typing import List, Union


class ValidationError(Exception):
    """Исключение для ошибок валидации."""
    pass


class InputValidator:
    """Валидатор входных данных для GUI."""
    
    @staticmethod
    def validate_non_empty(value: str, field_name: str) -> str:
        """
        Проверка, что значение не пустое.
        
        Args:
            value: Проверяемое значение
            field_name: Имя поля для сообщения об ошибке
            
        Returns:
            Значение, если валидно
            
        Raises:
            ValidationError: Если значение пустое
        """
        if value is None or value.strip() == "":
            raise ValidationError(f"Поле '{field_name}' не может быть пустым")
        return value.strip()
    
    @staticmethod
    def validate_positive_number(value: str, field_name: str) -> float:
        """
        Проверка, что значение является положительным числом.
        
        Args:
            value: Проверяемое значение
            field_name: Имя поля для сообщения об ошибке
            
        Returns:
            Число (float), если валидно
            
        Raises:
            ValidationError: Если значение не является положительным числом
        """
        value = InputValidator.validate_non_empty(value, field_name)
        
        try:
            num = float(value.replace(',', '.'))
            if num <= 0:
                raise ValidationError(f"Поле '{field_name}' должно быть положительным числом")
            return num
        except ValueError:
            raise ValidationError(f"Поле '{field_name}' должно содержать число")
    
    @staticmethod
    def validate_non_negative_number(value: str, field_name: str) -> float:
        """
        Проверка, что значение является неотрицательным числом.
        
        Args:
            value: Проверяемое значение
            field_name: Имя поля для сообщения об ошибке
            
        Returns:
            Число (float), если валидно
            
        Raises:
            ValidationError: Если значение не является неотрицательным числом
        """
        value = InputValidator.validate_non_empty(value, field_name)
        
        try:
            num = float(value.replace(',', '.'))
            if num < 0:
                raise ValidationError(f"Поле '{field_name}' должно быть неотрицательным числом")
            return num
        except ValueError:
            raise ValidationError(f"Поле '{field_name}' должно содержать число")
    
    @staticmethod
    def validate_integer(value: str, field_name: str) -> int:
        """
        Проверка, что значение является целым числом.
        
        Args:
            value: Проверяемое значение
            field_name: Имя поля для сообщения об ошибке
            
        Returns:
            Целое число (int), если валидно
            
        Raises:
            ValidationError: Если значение не является целым числом
        """
        value = InputValidator.validate_non_empty(value, field_name)
        
        try:
            return int(value)
        except ValueError:
            raise ValidationError(f"Поле '{field_name}' должно содержать целое число")
    
    @staticmethod
    def validate_thickness(value: str, field_name: str, min_allowed: float = 1.0, max_allowed: float = 100.0) -> float:
        """
        Проверка толщины стенки в допустимых пределах.
        
        Args:
            value: Проверяемое значение
            field_name: Имя поля для сообщения об ошибке
            min_allowed: Минимально допустимое значение
            max_allowed: Максимально допустимое значение
            
        Returns:
            Толщина (float), если валидна
            
        Raises:
            ValidationError: Если толщина вне допустимых пределов
        """
        num = InputValidator.validate_positive_number(value, field_name)
        
        if num < min_allowed or num > max_allowed:
            raise ValidationError(
                f"Поле '{field_name}' должно быть в диапазоне от {min_allowed} до {max_allowed}"
            )
        
        return num
    
    @staticmethod
    def validate_pressure(value: str, field_name: str, min_allowed: float = 0.1, max_allowed: float = 1000.0) -> float:
        """
        Проверка давления в допустимых пределах.
        
        Args:
            value: Проверяемое значение
            field_name: Имя поля для сообщения об ошибке
            min_allowed: Минимально допустимое значение
            max_allowed: Максимально допустимое значение
            
        Returns:
            Давление (float), если валидно
            
        Raises:
            ValidationError: Если давление вне допустимых пределов
        """
        num = InputValidator.validate_positive_number(value, field_name)
        
        if num < min_allowed or num > max_allowed:
            raise ValidationError(
                f"Поле '{field_name}' должно быть в диапазоне от {min_allowed} до {max_allowed}"
            )
        
        return num
    
    @staticmethod
    def validate_year(value: str, field_name: str, min_year: int = 1900, max_year: int = 2030) -> int:
        """
        Проверка года в допустимых пределах.
        
        Args:
            value: Проверяемое значение
            field_name: Имя поля для сообщения об ошибке
            min_year: Минимально допустимый год
            max_year: Максимально допустимый год
            
        Returns:
            Год (int), если валиден
            
        Raises:
            ValidationError: Если год вне допустимых пределов
        """
        year = InputValidator.validate_integer(value, field_name)
        
        if year < min_year or year > max_year:
            raise ValidationError(
                f"Поле '{field_name}' должно быть в диапазоне от {min_year} до {max_year}"
            )
        
        return year
    
    @staticmethod
    def validate_serial_number(value: str, field_name: str) -> str:
        """
        Проверка заводского номера (не пустой, не слишком длинный).
        
        Args:
            value: Проверяемое значение
            field_name: Имя поля для сообщения об ошибке
            
        Returns:
            Номер, если валиден
            
        Raises:
            ValidationError: Если номер не проходит валидацию
        """
        value = InputValidator.validate_non_empty(value, field_name)
        
        if len(value) > 50:
            raise ValidationError(f"Поле '{field_name}' слишком длинное ( максимум 50 символов)")
        
        return value
    
    @staticmethod
    def validate_date_format(value: str, field_name: str) -> str:
        """
        Проверка формата даты (ДД.ММ.ГГГГ).
        
        Args:
            value: Проверяемое значение
            field_name: Имя поля для сообщения об ошибке
            
        Returns:
            Дата, если валидна
            
        Raises:
            ValidationError: Если формат даты неверный
        """
        value = InputValidator.validate_non_empty(value, field_name)
        
        pattern = r'^\d{2}\.\d{2}\.\d{4}$'
        if not re.match(pattern, value):
            raise ValidationError(
                f"Поле '{field_name}' должно быть в формате ДД.ММ.ГГГГ (например, 31.12.2024)"
            )
        
        return value
    
    @staticmethod
    def validate_list_of_numbers(value: str, field_name: str) -> List[float]:
        """
        Проверка списка чисел (через запятую).
        
        Args:
            value: Проверяемое значение
            field_name: Имя поля для сообщения об ошибке
            
        Returns:
            Список чисел (float)
            
        Raises:
            ValidationError: Если список не проходит валидацию
        """
        value = InputValidator.validate_non_empty(value, field_name)
        
        numbers = []
        items = value.split(',')
        
        for i, item in enumerate(items):
            item = item.strip()
            try:
                num = float(item.replace(',', '.'))
                numbers.append(num)
            except ValueError:
                raise ValidationError(
                    f"В поле '{field_name}' обнаружено некорректное значение в позиции {i + 1}: '{item}'"
                )
        
        return numbers


def validate_report_required_fields(data: dict) -> List[str]:
    """
    Валидация обязательных полей заключения.
    
    Args:
        data: Словарь с данными формы
        
    Returns:
        Список ошибок (пустой если всё ок)
    """
    errors = []
    
    required_fields = {
        'zakl_number': 'Номер заключения',
        'reg_number': 'Регистрационный номер',
        'p_rab': 'Рабочее давление',
    }
    
    for field, name in required_fields.items():
        value = data.get(field, '')
        if value is None or str(value).strip() == '':
            errors.append(f"Не заполнено обязательное поле: {name}")
    
    return errors

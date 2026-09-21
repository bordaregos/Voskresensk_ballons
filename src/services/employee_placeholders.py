"""Готовые представления данных сотрудника для «Редактора сотрудника»
конструктора документов (ПКМ на чипе плейсхолдера -> «Создать сотрудника»,
см. src/ui/employee_placeholder_dialog.py и src/ui/main_window.py,
_show_chip_context_menu()/_render_slot_fields()).

Чистые функции, без Qt -- тот же принцип, что и у
src/services/calculations.py/formula_engine.py. EMPLOYEE_DATA_FIELDS --
общий источник и для диалога (какие чипы предложить выбрать), и для
рендера реквизитов (каждое отмеченное представление -- отдельное поле,
см. MainWindow._create_employee_from_chip_menu()/employee_data_value())."""

from typing import Callable, List, NamedTuple

from ..models.employee import Employee


def fio_short(full_name: str) -> str:
    """"Клименко Алексей Александрович" -> "Клименко А. А." -- фамилия
    полностью, имя и отчество сокращаются до инициала с точкой. Без
    отчества (два слова) даёт "Клименко А.". Пустая строка на пустом/
    состоящем из пробелов имени."""
    parts = full_name.split()
    if not parts:
        return ""
    surname, rest = parts[0], parts[1:]
    initials = [f"{part[0].upper()}." for part in rest]
    return surname if not initials else surname + " " + " ".join(initials)


def format_certificate(certificate) -> str:
    """Текст одного удостоверения для отображения/плейсхолдера -- сам текст
    записи плюс срок действия, если он указан ("Удостоверение № ... от ... —
    до 25.02.2029"). Без даты -- просто текст, как и раньше (до появления
    Certificate.expires)."""
    if not certificate.expires:
        return certificate.text
    return f"{certificate.text} — до {certificate.expires}"


class EmployeeDataField(NamedTuple):
    key: str
    label: str
    value: Callable[[Employee], str]


# Порядок -- тот же, что в докстрине модуля и в docs/design/
# редактор_сотрудника.html (CHIP_DEFS): полное ФИО, фамилия с инициалами,
# должность, квалификация, уровень квалификации, удостоверения.
EMPLOYEE_DATA_FIELDS: List[EmployeeDataField] = [
    EmployeeDataField("fio_full", "Полное ФИО", lambda e: e.full_name),
    EmployeeDataField("fio_short", "Фамилия И.О.", lambda e: fio_short(e.full_name)),
    EmployeeDataField("position", "Должность", lambda e: e.position),
    EmployeeDataField("qualification", "Квалификация", lambda e: e.qualification),
    EmployeeDataField("qualification_level", "Уровень квалификации", lambda e: e.qualification_level),
    EmployeeDataField(
        "certificates", "Удостоверения",
        lambda e: "; ".join(format_certificate(c) for c in e.certificates),
    ),
]

_FIELDS_BY_KEY = {field.key: field for field in EMPLOYEE_DATA_FIELDS}


def employee_data_value(employee: Employee, key: str) -> str:
    """Значение одного готового представления (key из EMPLOYEE_DATA_FIELDS)
    для конкретного сотрудника. Неизвестный key -- пустая строка, а не
    исключение: поле могло исчезнуть из EMPLOYEE_DATA_FIELDS уже после
    того, как привязка была сохранена (см. load_field_employee_bindings())."""
    field = _FIELDS_BY_KEY.get(key)
    return field.value(employee) if field is not None else ""

"""Реквизиты экспертной организации — уровень "организация" в трёхуровневой
модели конфигурации шаблонов (см. src/services/template_schema.py).

Одни и те же значения используются для всех отчётов независимо от типа
объекта и от конкретного отчёта — в отличие от полей формы (widget_names_*),
которые оператор заполняет каждый раз заново. Не персональные данные
заказчика и не секрет — файл не в .gitignore.

Значения по умолчанию взяты из примера реального отчёта
(TD_720291_otd_214_1.docx), приложенного при обсуждении задачи — правьте
под свою организацию.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class OrganizationConfig:
    """Реквизиты экспертной организации — Таблица 1 раздела 1.2 отчёта."""
    full_name: str
    short_name: str
    license_number: str
    license_date: str
    license_issuer: str
    address: str
    phone: str
    email: str = ""
    website: str = ""
    head_position: str = ""
    head_name: str = ""
    inn: str = ""


DEFAULT_ORGANIZATION = OrganizationConfig(
    full_name="Общество с ограниченной ответственностью "
               "«Экспертно-диагностический центр ИМПУЛЬС»",
    short_name="ООО «ЭДЦ ИМПУЛЬС»",
    license_number="ДЭ-00-007889",
    license_date="04.10.2007",
    license_issuer="Федеральная служба по экологическому, технологическому "
                    "и атомному надзору",
    address="141090, Московская обл., г.о. Королев, г. Королев, "
            "мкр. Болшево, ул. Пушкинская, дом 15, помещение LIX",
    phone="(495) 500-47-47",
    email="impuls2000@inbox.ru",
    website="edc-impuls.com",
    head_position="Генеральный директор",
    head_name="Сафронов Сергей Васильевич",
)

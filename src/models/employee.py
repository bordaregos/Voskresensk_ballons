"""Модель сотрудника — общий справочник компании, не привязан к отчёту."""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional


@dataclass
class Certificate:
    """Одна запись об удостоверении сотрудника -- текст (номер/дата выдачи,
    как раньше вводили одной строкой, например "Удостоверение № 0039-33921
    от 25.02.2024 г.") плюс отдельный срок действия (expires -- "" если не
    указан, иначе "дд.мм.гггг", тот же формат, что и QDateEdit.toString(
    "dd.MM.yyyy") в остальном приложении)."""

    text: str = ""
    expires: str = ""

    def to_dict(self) -> Dict[str, str]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Any) -> 'Certificate':
        # Совместимость со старым форматом -- до этого поля certificates
        # было List[str], каждый элемент -- голая строка без даты (см.
        # data/employees.json, записи, сохранённые предыдущей итерацией
        # фичи). Нормализация пробелов -- тем же приёмом, что и в
        # EmployeesTabController._add_certificate() для новых записей,
        # перенесена сюда, чтобы починить и уже сохранённые старые.
        if isinstance(data, str):
            return cls(text=" ".join(data.split()), expires="")
        return cls(text=" ".join(str(data.get('text', '')).split()), expires=data.get('expires', ''))


@dataclass
class Employee:
    """Запись справочника сотрудников.

    kleishe_filename — только имя файла в data/kleishe/ (см.
    src/config.py:KLEISHE_DIR), не абсолютный путь.
    """

    id: str
    position: str = ""
    full_name: str = ""
    # Квалификация -- отдельно от position (например, "II уровень" при
    # должности "Специалист НК II уровня"): нужна для готовых плейсхолдеров
    # сотрудника в редакторе сотрудника конструктора документов (см.
    # src/ui/employee_placeholder_dialog.py). Редактируется только в
    # constructor_window.ui -- см. EmployeesTabController.
    qualification: str = ""
    # Уровень квалификации -- отдельное поле от qualification (пользователь
    # явно попросил не переиспользовать существующее поле, а завести новое,
    # см. историю задачи): своё готовое представление
    # ("qualification_level" в EMPLOYEE_DATA_FIELDS), своя строка ввода в
    # редакторе. Как и qualification -- только в constructor_window.ui.
    qualification_level: str = ""
    certificates: List[Certificate] = field(default_factory=list)
    kleishe_filename: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        # asdict() рекурсивно раскладывает и вложенные dataclass'ы (каждый
        # Certificate в certificates) в обычные dict -- отдельная сборка
        # списка не нужна.
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Employee':
        return cls(
            id=data['id'],
            position=data.get('position', ''),
            full_name=data.get('full_name', ''),
            qualification=data.get('qualification', ''),
            qualification_level=data.get('qualification_level', ''),
            certificates=[Certificate.from_dict(item) for item in data.get('certificates', [])],
            kleishe_filename=data.get('kleishe_filename'),
        )

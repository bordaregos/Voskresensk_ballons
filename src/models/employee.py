"""Модель сотрудника — общий справочник компании, не привязан к отчёту."""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional


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
    certificates: List[str] = field(default_factory=list)
    kleishe_filename: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Employee':
        return cls(
            id=data['id'],
            position=data.get('position', ''),
            full_name=data.get('full_name', ''),
            qualification=data.get('qualification', ''),
            certificates=list(data.get('certificates', [])),
            kleishe_filename=data.get('kleishe_filename'),
        )

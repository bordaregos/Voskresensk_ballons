"""Пользовательский вариант титульного листа конструктора документов —
добавляется через UI (кнопка «Добавить» в списке «Титульные листы»), не
привязан к конкретному отчёту/проекту. Встроенные варианты (TITLE_VARIANTS,
src/services/template_schema.py) в этот справочник не входят и через UI не
удаляются."""

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List


@dataclass
class TitleVariant:
    id: str
    document_title: str = ""
    subtitle_fields: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TitleVariant':
        return cls(
            id=data['id'],
            document_title=data.get('document_title', ''),
            subtitle_fields=list(data.get('subtitle_fields', [])),
        )

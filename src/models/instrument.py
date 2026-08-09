"""Модель прибора — общий справочник компании, не привязан к отчёту."""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any


@dataclass
class Instrument:
    """Запись справочника приборов."""

    id: str
    name: str = ""
    serial_number: str = ""
    cert_number: str = ""
    documents: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Instrument':
        return cls(
            id=data['id'],
            name=data.get('name', ''),
            serial_number=data.get('serial_number', ''),
            cert_number=data.get('cert_number', ''),
            documents=list(data.get('documents', [])),
        )

"""Модель записи архива документов организации — общий справочник
компании (лицензии, приказы и т.п.), не привязан к отчёту. См.
src/services/org_docs_store.py."""

from dataclasses import dataclass, asdict
from typing import Dict, Any


@dataclass
class OrgDoc:
    """Запись архива: название/тип/дата — метаданные для таблицы,
    filename — имя файла на диске (в ORG_DOCS_FILES_DIR, не совпадает с
    исходным именем при загрузке, см. store_org_doc_file())."""

    id: str
    title: str = ""
    doc_type: str = ""
    date: str = ""
    filename: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'OrgDoc':
        return cls(
            id=data['id'],
            title=data.get('title', ''),
            doc_type=data.get('doc_type', ''),
            date=data.get('date', ''),
            filename=data.get('filename', ''),
        )

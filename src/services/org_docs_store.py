"""Архив документов организации (Фаза 10) — лицензии, приказы,
свидетельства и т.п., не привязанные к конкретному объекту/отчёту.

Отдельное общекомпанейское хранилище, тем же приёмом, что и
employees_store.py/instruments_store.py: JSON-манифест с метаданными +
папка с самими файлами (имя на диске — uuid4, исключает коллизии
независимо от исходного имени, как store_kleishe_image()). Название/
тип/дата хранятся в манифесте, а не в имени файла — то же соображение,
что и у остальных справочников компании.
"""

import json
from pathlib import Path
from typing import List
from uuid import uuid4

from ..config import DATA_DIR
from ..models.org_doc import OrgDoc

ORG_DOCS_FILE = DATA_DIR / "org_docs.json"
ORG_DOCS_FILES_DIR = DATA_DIR / "org_docs_files"


def load_org_docs(path: Path = ORG_DOCS_FILE) -> List[OrgDoc]:
    """Загружает архив из JSON. Файла ещё нет (первый запуск) —
    пустой список, не ошибка."""
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as file:
        data = json.load(file)
    return [OrgDoc.from_dict(item) for item in data.get("org_docs", [])]


def save_org_docs(org_docs: List[OrgDoc], path: Path = ORG_DOCS_FILE) -> None:
    """Сохраняет архив в JSON, создавая папку данных при необходимости."""
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {"org_docs": [doc.to_dict() for doc in org_docs]}
    with open(path, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


def store_org_doc_file(source_path: Path, dest_dir: Path = ORG_DOCS_FILES_DIR) -> str:
    """Копирует загружаемый файл в папку данных приложения, имя на
    диске — uuid4 + исходное расширение (тот же приём, что и
    employees_store.store_kleishe_image()). Возвращает имя сохранённого
    файла (без пути) — оно хранится в OrgDoc.filename."""
    import shutil

    dest_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid4().hex}{source_path.suffix.lower()}"
    shutil.copyfile(source_path, dest_dir / filename)
    return filename

"""Файловая модель "объект → документ" для дерева в сайдбаре формы.

Объект — подпапка OUTPUT_DIR, документ — .json-файл Project прямо внутри
неё (без вложенных папок дальше). Без отдельного индекса: дерево строится
сканированием диска (Path.iterdir()/glob()) каждый раз, когда нужно —
индекс-файл рисковал бы разойтись с реальными файлами при ручном
переименовании/удалении, а объектов и документов ожидаются десятки, не
тысячи, пересканировать дёшево. Не зависит от Qt — см. план редизайна
pipeline-формы, Фаза 2.
"""

import re
from pathlib import Path
from typing import List, Tuple

from ..config import OUTPUT_DIR
from ..models.project import Project


def list_objects(base_dir: Path = OUTPUT_DIR) -> List[str]:
    """Имена папок-объектов в base_dir, по алфавиту. Файлы верхнего
    уровня (старые плоские проекты вроде эталон_720291_проект.json) не
    считаются объектами и не мешают."""
    if not base_dir.exists():
        return []
    return sorted(p.name for p in base_dir.iterdir() if p.is_dir())


def list_documents(object_dir: Path, equipment_type_id: str) -> List[Tuple[Path, str]]:
    """Документы папки-объекта, отфильтрованные по equipment_type_id —
    окно одного типа не умеет открыть документ другого (другой набор
    виджетов целиком). Возвращает пары (путь, ярлык); ярлык — по
    reg_number из самого файла, а не имя файла на диске. Файлы, которые
    не парсятся как Project, тихо пропускаются — один битый/чужой .json
    в папке не должен ломать построение всего дерева."""
    if not object_dir.exists():
        return []
    documents = []
    for path in sorted(object_dir.glob("*.json")):
        try:
            project = Project.load_from_file(path)
        except (OSError, ValueError):
            continue
        if project.equipment_type != equipment_type_id:
            continue
        documents.append((path, _document_label(project)))
    return documents


def _document_label(project: Project) -> str:
    """Ярлык документа для дерева. reg_number ещё пуст сразу после
    create_document() (до первого реального сохранения оператором) —
    тогда возвращается плейсхолдер вместо пустой строки."""
    reg_number = str(project.report_data.get("reg_number", "")).strip()
    if reg_number:
        return f"рег.{reg_number}"
    return "Новый документ"


def sanitize_object_name(name: str) -> str:
    """Заменяет символы, недопустимые в имени папки (/ \\ : и т.п.), на
    "_" — имя объекта вводится оператором текстом, не гарантированно
    safe для файловой системы. Кириллица, пробелы, скобки — не трогаются,
    они допустимы в именах папок на macOS/Windows/Linux."""
    name = name.strip()
    cleaned = re.sub(r'[\\/:*?"<>|]', "_", name)
    return cleaned or "Новый объект"


def create_object(name: str, base_dir: Path = OUTPUT_DIR) -> Path:
    """Создаёт папку-объект (idempotent — если уже есть, просто
    возвращает её)."""
    object_dir = base_dir / sanitize_object_name(name)
    object_dir.mkdir(parents=True, exist_ok=True)
    return object_dir


def create_document(object_dir: Path, equipment_type_id: str) -> Path:
    """Создаёт пустой документ (Project) внутри папки-объекта и сразу
    сохраняет на диск — документ должен появиться в дереве сразу после
    создания, а не только после первого ручного "Сохранить". Имя файла —
    документ_<N>.json, N — по количеству уже существующих файлов такого
    вида в папке (не полагаемся на то, что файлы не переименовывали и не
    удаляли вручную — просто ищем первое свободное имя)."""
    object_dir.mkdir(parents=True, exist_ok=True)
    n = len(list(object_dir.glob("документ_*.json"))) + 1
    path = object_dir / f"документ_{n}.json"
    while path.exists():
        n += 1
        path = object_dir / f"документ_{n}.json"
    project = Project(equipment_type=equipment_type_id, output_dir=str(object_dir))
    project.save_to_file(path)
    return path

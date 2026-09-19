"""Файловая модель "папка → документ" для дерева в сайдбаре формы.

Папка (изначально называлась "объект" — имя list_objects()/create_object()/
rename_object() сохранено ради обратной совместимости с уже написанным
кодом-потребителем, хотя теперь это может быть подпапка на любой глубине,
а не только верхний уровень) — каталог внутри OUTPUT_DIR, документ —
.json-файл Project прямо внутри неё. Папки поддерживают произвольную
вложенность (docs/design/вводная_часть.html: "Папки -- произвольная
вложенность") — все функции ниже принимают путь к КОНКРЕТНОЙ папке
(base_dir/object_dir), а не завязаны на OUTPUT_DIR жёстко, поэтому
рекурсия (построение дерева всех уровней, создание подпапки внутри
подпапки и т.п.) — забота вызывающей стороны (см.
MainWindow._build_objects_tree_level()), не этого модуля. Без отдельного
индекса: дерево строится сканированием диска (Path.iterdir()/glob())
каждый раз, когда нужно — индекс-файл рисковал бы разойтись с реальными
файлами при ручном переименовании/удалении, а папок и документов
ожидаются десятки, не тысячи, пересканировать дёшево. Не зависит от Qt —
см. план редизайна pipeline-формы, Фаза 2.
"""

import re
import shutil
from pathlib import Path
from typing import List, Tuple

from ..config import OUTPUT_DIR
from ..models.project import Project


def list_all_folders(base_dir: Path = OUTPUT_DIR) -> List[Tuple[Path, int]]:
    """Плоский список ВСЕХ папок дерева (произвольная вложенность,
    родитель перед своими детьми, дети по алфавиту) вместе с глубиной
    вложенности -- под выпадающий список выбора папки в диалоге
    сохранения (см. src/ui/save_project_dialog.py), где иерархия
    показывается отступом в одном плоском QComboBox, а не собственным
    деревом внутри диалога."""
    result: List[Tuple[Path, int]] = []

    def walk(dir_path: Path, depth: int) -> None:
        for name in list_objects(dir_path):
            child = dir_path / name
            result.append((child, depth))
            walk(child, depth + 1)

    walk(base_dir, 0)
    return result


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
    виджетов целиком). Возвращает пары (путь, ярлык); ярлык — имя файла
    без расширения (path.stem), то самое имя, которое оператор вводит
    вручную в диалоге сохранения (см. FileHandler._prompt_document_path()).
    Файлы, которые не парсятся как Project, тихо пропускаются — один
    битый/чужой .json в папке не должен ломать построение всего дерева."""
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
        documents.append((path, path.stem))
    return documents


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


def duplicate_document(path: Path) -> Path:
    """Копирует документ в ту же папку-объект под новым свободным
    именем — «оригинал_копия.json», «оригинал_копия_2.json» и т.д.
    (Фаза 8, «Дублировать» в контекстном меню). Ярлык в дереве — это
    имя файла (см. list_documents()), так что копия сразу отличима от
    оригинала; report_data (включая reg_number) копируется как есть,
    оператор поправляет его вручную вслед за реальным рабочим
    процессом."""
    i = 1
    while True:
        suffix = "_копия" if i == 1 else f"_копия_{i}"
        candidate = path.parent / f"{path.stem}{suffix}.json"
        if not candidate.exists():
            break
        i += 1
    shutil.copy2(path, candidate)
    return candidate


def rename_object(object_dir: Path, new_name: str) -> Path:
    """Переименовывает папку-объект (Фаза 8, «Переименовать объект»).
    new_name прогоняется через тот же sanitize_object_name(), что и при
    создании — согласованность имён папок."""
    new_dir = object_dir.parent / sanitize_object_name(new_name)
    if new_dir != object_dir:
        object_dir.rename(new_dir)
    return new_dir


def delete_object(object_dir: Path) -> None:
    """Удаляет папку-объект целиком со всем содержимым (Фаза 8,
    «Удалить объект»). Подтверждение — забота вызывающей стороны
    (main_window.py), здесь — только само действие."""
    shutil.rmtree(object_dir)

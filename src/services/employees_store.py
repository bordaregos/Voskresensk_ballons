"""Хранение справочника сотрудников: JSON-файл + папка с клише.

Не зависит от Qt и от конкретного отчёта/проекта — см. src/models/employee.py
и CLAUDE.md/план по вкладке «Сотрудники».
"""

import json
import shutil
from pathlib import Path
from typing import List, Optional
from uuid import uuid4

from ..config import EMPLOYEES_FILE, KLEISHE_DIR
from ..models.employee import Employee


def load_employees(path: Path = EMPLOYEES_FILE) -> List[Employee]:
    """Загружает справочник сотрудников из JSON.

    Если файла ещё нет (первый запуск), возвращает пустой список.
    """
    if not path.exists():
        return []

    with open(path, 'r', encoding='utf-8') as file:
        data = json.load(file)

    return [Employee.from_dict(item) for item in data.get('employees', [])]


def save_employees(employees: List[Employee], path: Path = EMPLOYEES_FILE) -> None:
    """Сохраняет справочник сотрудников в JSON, создавая папку при необходимости."""
    path.parent.mkdir(parents=True, exist_ok=True)

    data = {'employees': [employee.to_dict() for employee in employees]}

    with open(path, 'w', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


def store_kleishe_image(source_path: Path, dest_dir: Path = KLEISHE_DIR) -> str:
    """Копирует картинку клише в папку данных приложения.

    Имя файла назначается по uuid4 — исключает коллизии между сотрудниками
    независимо от исходного имени файла. Возвращает имя сохранённого файла
    (без пути) — именно оно хранится в Employee.kleishe_filename.
    """
    dest_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{uuid4().hex}{source_path.suffix.lower()}"
    shutil.copyfile(source_path, dest_dir / filename)

    return filename


def resolve_kleishe_path(
    employees: List[Employee], employee_id: Optional[str], kleishe_dir: Path = KLEISHE_DIR
) -> Optional[Path]:
    """Путь к файлу клише сотрудника — для вставки InlineImage в отчёт
    (см. MainWindow._specialist_kleishe_image()).

    Возвращает None, если сотрудник не выбран, не найден в списке, клише не
    привязано или файл клише отсутствует на диске -- в отчёте на месте
    плейсхолдера клише тогда просто остаётся пусто, без ошибки рендера.
    """
    if not employee_id:
        return None

    employee = next((e for e in employees if e.id == employee_id), None)
    if employee is None or not employee.kleishe_filename:
        return None

    path = kleishe_dir / employee.kleishe_filename
    return path if path.exists() else None


def find_employee_id_by_name(employees: List[Employee], full_name: str) -> Optional[str]:
    """Ищет сотрудника по точному совпадению ФИО -- резервный путь для
    строк table_specialists, у которых нет employee_id (специалист вписан
    текстом вручную или строка сохранена в project.json ещё до того, как
    выбор специалиста стал привязываться к справочнику "Сотрудники", см.
    MainWindow._add_specialist_row()). Без этого клише не подставлялось бы
    в уже готовые документы, даже когда вписанное ФИО совпадает с
    сотрудником, у которого клише есть.

    Возвращает id первого сотрудника с таким ФИО или None, если ФИО пустое
    или совпадений нет.
    """
    full_name = full_name.strip()
    if not full_name:
        return None

    employee = next((e for e in employees if e.full_name.strip() == full_name), None)
    return employee.id if employee else None

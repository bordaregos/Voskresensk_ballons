"""Хранение справочника сотрудников: JSON-файл + папка с клише.

Не зависит от Qt и от конкретного отчёта/проекта — см. src/models/employee.py
и CLAUDE.md/план по вкладке «Сотрудники».
"""

import json
import shutil
from pathlib import Path
from typing import List
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

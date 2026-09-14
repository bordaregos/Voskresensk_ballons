"""Хранение пользовательских вариантов титульного листа конструктора
документов: JSON-файл, тот же приём, что employees_store.py/
instruments_store.py -- не зависит от Qt.

Встроенные варианты (TITLE_VARIANTS, src/services/template_schema.py)
живут в коде и через этот стор не редактируются -- get_all_title_variants()
только добавляет к ним пользовательские, id которых генерируется в UI-слое
(uuid4().hex[:8], тот же приём, что src/ui/employees_tab.py) и поэтому не
пересекается с "otchet"/"zaklyuchenie".
"""

import json
from pathlib import Path
from typing import Dict, List

from ..config import TITLE_VARIANTS_FILE
from ..models.title_variant import TitleVariant
from .template_schema import TITLE_VARIANTS, TitleConfig


def load_title_variants(path: Path = TITLE_VARIANTS_FILE) -> List[TitleVariant]:
    """Загружает пользовательские варианты титульного листа из JSON.

    Если файла ещё нет (первый запуск, или ни одного варианта ещё не
    добавили), возвращает пустой список.
    """
    if not path.exists():
        return []

    with open(path, 'r', encoding='utf-8') as file:
        data = json.load(file)

    return [TitleVariant.from_dict(item) for item in data.get('title_variants', [])]


def save_title_variants(variants: List[TitleVariant], path: Path = TITLE_VARIANTS_FILE) -> None:
    """Сохраняет пользовательские варианты титульного листа в JSON, создавая
    папку при необходимости."""
    path.parent.mkdir(parents=True, exist_ok=True)

    data = {'title_variants': [variant.to_dict() for variant in variants]}

    with open(path, 'w', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


def get_all_title_variants(path: Path = TITLE_VARIANTS_FILE) -> Dict[str, TitleConfig]:
    """Встроенные TITLE_VARIANTS + пользовательские из JSON, в виде единого
    словаря id -> TitleConfig -- то, чем сайдбар конструктора заполняет
    список «Титульные листы»."""
    variants = dict(TITLE_VARIANTS)
    for variant in load_title_variants(path):
        variants[variant.id] = TitleConfig(
            document_title=variant.document_title, subtitle_fields=variant.subtitle_fields,
        )
    return variants

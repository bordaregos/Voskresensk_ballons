"""Хранение справочника приборов: JSON-файл.

Не зависит от Qt и от конкретного отчёта/проекта — см.
src/models/instrument.py и вкладку «Приборы» (src/ui/instruments_tab.py).
"""

import json
from pathlib import Path
from typing import List

from ..config import INSTRUMENTS_FILE
from ..models.instrument import Instrument


def load_instruments(path: Path = INSTRUMENTS_FILE) -> List[Instrument]:
    """Загружает справочник приборов из JSON.

    Если файла ещё нет (первый запуск), возвращает пустой список.
    """
    if not path.exists():
        return []

    with open(path, 'r', encoding='utf-8') as file:
        data = json.load(file)

    return [Instrument.from_dict(item) for item in data.get('instruments', [])]


def save_instruments(instruments: List[Instrument], path: Path = INSTRUMENTS_FILE) -> None:
    """Сохраняет справочник приборов в JSON, создавая папку при необходимости."""
    path.parent.mkdir(parents=True, exist_ok=True)

    data = {'instruments': [instrument.to_dict() for instrument in instruments]}

    with open(path, 'w', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False, indent=2)

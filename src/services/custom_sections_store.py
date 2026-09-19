"""Список разделов конструктора документов, добавленных оператором сверх
встроенных title/intro/appendix1 (см. src/ui/main_window.py,
MainWindow._create_section()/_delete_section()) -- тот же приём, что и
остальные *_store.py (JSON-файл, не зависит от Qt).

Файл хранит ДВЕ секции -- "sections" (список {"id":.., "label":..} в
порядке добавления = порядке в сайдбаре/собранном документе) и
"next_section_id" (счётчик для генерации следующего id). Id -- не
производная от label (произвольный текст оператора), а простой счётчик
("section1", "section2", ...) -- он идёт в имена файлов
(FRAGMENTS_DIR/{id}_{variant_id}.docx, см. src/config.py) и в
setattr(self, ...) имена динамических Python-атрибутов виджетов
(MainWindow._build_section_widgets()), для которых произвольный
пользовательский текст небезопасен. save_sections() поэтому read-modify-
write, чтобы не столкнуть уже выданный next_section_id при параллельной
правке label."""

import json
from pathlib import Path
from typing import Dict, List

from ..config import CUSTOM_SECTIONS_FILE


def _load_raw(path: Path) -> Dict:
    if not path.exists():
        return {}
    with open(path, 'r', encoding='utf-8') as file:
        return json.load(file)


def _save_raw(data: Dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


def load_sections(path: Path = CUSTOM_SECTIONS_FILE) -> List[Dict[str, str]]:
    """Список {"id":.., "label":..} в порядке добавления. Пустой список,
    если файла ещё нет (ни одного раздела сверх встроенных трёх ещё не
    добавляли)."""
    data = _load_raw(path)
    return [{'id': item['id'], 'label': item['label']} for item in data.get('sections', [])]


def save_sections(sections: List[Dict[str, str]], path: Path = CUSTOM_SECTIONS_FILE) -> None:
    """Сохраняет список разделов, не трогая next_section_id."""
    data = _load_raw(path)
    data['sections'] = [{'id': s['id'], 'label': s['label']} for s in sections]
    _save_raw(data, path)


def next_section_id(path: Path = CUSTOM_SECTIONS_FILE) -> str:
    """Выдаёт очередной id ("section1", "section2", ...) и сразу сохраняет
    продвинутый счётчик -- повторный вызов (в т.ч. из другого запуска
    приложения) никогда не вернёт уже выданный id, даже если раздел с ним
    успели удалить."""
    data = _load_raw(path)
    n = int(data.get('next_section_id', 1))
    data['next_section_id'] = n + 1
    _save_raw(data, path)
    return f"section{n}"
